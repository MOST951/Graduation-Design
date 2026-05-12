package com.weibo.collector;

import com.weibo.collector.parser.ContentCleaner;

import org.apache.spark.api.java.JavaRDD;
import org.apache.spark.api.java.JavaSparkContext;
import org.apache.spark.sql.SparkSession;

import java.io.Serializable;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.SQLException;
import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Random;
import java.util.concurrent.atomic.AtomicLong;
import java.util.logging.Level;
import java.util.logging.Logger;

/**
 * 数据采集 Spark 作业入口 (CollectionController 通过 spark-submit --class 调用)
 *
 * <p>本类是数据采集模块的 <b>Spark 编排入口</b>:
 * <ol>
 *   <li>由 <code>spark-submit --master spark://spark-master:7077</code> 启动, 在 Spark 集群上注册一个 Application;</li>
 *   <li>解析采集关键词参数;</li>
 *   <li>用 {@link JavaSparkContext#parallelize} 把 "待采集索引" 列表分发到多个 Executor;</li>
 *   <li>每个分区独立: 生成合成微博 -> 用 {@link com.weibo.collector.parser.ContentCleaner} 清洗 -> 批量 JDBC 插入 MySQL <code>weibo_core_data</code>;</li>
 *   <li>Driver 汇总 success/failure 后, 在 <code>crawl_batch_log</code> 写一行批次统计.</li>
 * </ol>
 * Spark Master UI ({@code http://<host>:8080}) 可以在 "Running Applications" 里看到本作业, 以及它的 stages / tasks.
 */
public class DataCollectorJob {

    private static final Logger LOG = Logger.getLogger(DataCollectorJob.class.getName());

    private static final int DEFAULT_MAX_COUNT = 20;

    private static final String INSERT_WEIBO_SQL =
            "INSERT INTO weibo_core_data (weibo_id, content, created_at, user_id, user_name, " +
                    "verified, followers_count, reposts_count, comments_count, attitudes_count, " +
                    "has_image, has_video, source, keyword, batch_id, graduation_batch, student_id) " +
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)";

    private static final String INSERT_BATCH_LOG_SQL =
            "INSERT INTO crawl_batch_log (batch_id, task_name, task_type, keywords, status, " +
                    "total_weibos, success_count, failure_count, start_time, end_time) " +
                    "VALUES (?, ?, ?, JSON_ARRAY(?), ?, ?, ?, ?, ?, ?)";

    private static final String UPDATE_TASK_FINISHED_SQL =
            "UPDATE collection_task SET status=?, end_time=?, updated_at=? WHERE id=?";

    /** 模板池: 正/中/负三类基础模板, 每条模板中含 {kw} 占位符. */
    private static final String[] POSITIVE_TEMPLATES = {
            "今天的{kw}真的太赞了,体验非常棒,推荐大家也试试!",
            "{kw}的表现让人惊喜,完全超出我的预期,五星好评。",
            "刚入手{kw},品质和服务都很到位,点赞!",
            "用了一周{kw},越来越喜欢,值得拥有。",
            "强烈安利{kw},性价比超高,身边朋友都种草了。"
    };

    private static final String[] NEGATIVE_TEMPLATES = {
            "对{kw}非常失望,完全不是宣传的那样,差评。",
            "{kw}问题真不少,客服态度也很敷衍,不推荐。",
            "买了{kw}才发现质量堪忧,后悔死了。",
            "用了几天{kw}就出故障,售后还推卸责任,心累。",
            "{kw}虚假宣传太严重,大家千万别上当。"
    };

    private static final String[] NEUTRAL_TEMPLATES = {
            "关于{kw}的最新动态,详情见官方公告。",
            "今天看到{kw}的相关报道,具体内容大家自行判断。",
            "{kw}的市场表现需要更多数据验证,暂时观望。",
            "听同事讨论了一下{kw},褒贬不一,后续再了解。",
            "{kw}的更新日志已发布,功能调整较多。"
    };

    private static final String[] SOURCES = {
            "微博 weibo.com", "iPhone客户端", "Android客户端", "HUAWEI Mate 60 Pro", "iPad客户端"
    };

    private static final String[] USER_NAMES = {
            "数码爱好者", "美食探店家", "都市观察员", "学生小李", "职场打工人",
            "科技前线", "舆情观察", "市井见闻", "校园记者", "热点追踪者"
    };

    public static void main(String[] args) {
        long jobStart = System.currentTimeMillis();
        String batchId = "collect_" + jobStart;

        // 解析参数
        String keywordRaw = args.length > 0 ? String.join(" ", args).trim() : "";
        if (keywordRaw.isEmpty()) {
            LOG.severe("Missing required argument: keyword");
            System.exit(2);
        }
        // SparkJobLauncher 用 String.join(" ", args) 把所有调用方参数拼成 ONE 字符串传给 spark-submit,
        // 所以这里必须先把 keywordRaw 切成 token, 再从 token 列表里反向解析 taskId / maxCount.
        List<String> tokens = new ArrayList<>();
        for (String k : keywordRaw.split("[,\\s]+")) {
            if (!k.isEmpty()) tokens.add(k);
        }
        int maxCount = DEFAULT_MAX_COUNT;
        Long taskId = null;
        // 末尾是短整数 -> taskId
        if (!tokens.isEmpty()) {
            String last = tokens.get(tokens.size() - 1);
            if (last.matches("\\d+") && last.length() <= 8) {
                try {
                    taskId = Long.parseLong(last);
                    tokens.remove(tokens.size() - 1);
                } catch (NumberFormatException ignored) {}
            }
        }
        // 末尾还残留整数 -> maxCount
        if (!tokens.isEmpty()) {
            String last = tokens.get(tokens.size() - 1);
            if (last.matches("\\d+")) {
                try {
                    maxCount = Math.min(500, Integer.parseInt(last));
                    tokens.remove(tokens.size() - 1);
                } catch (NumberFormatException ignored) {}
            }
        }
        List<String> keywords = tokens;

        // 数据源连接 (driver + executor 都需要, 作为常量传给 lambda)
        final String url = env("SPRING_DATASOURCE_URL", "jdbc:mysql://db:3306/weibo_sentiment?useUnicode=true&characterEncoding=utf-8&serverTimezone=Asia/Shanghai");
        final String user = env("SPRING_DATASOURCE_USERNAME", "weibo_user");
        final String pass = env("SPRING_DATASOURCE_PASSWORD", "123456");

        // ---------- 1) 启动 SparkSession ----------
        // master 由 spark-submit --master 注入, 这里不再硬编码
        SparkSession spark = SparkSession.builder()
                .appName("WeiboDataCollector-" + batchId)
                // 让数据生成与 JDBC 写入有合理并行度 (限制不超过关键词数 * 4)
                .config("spark.sql.shuffle.partitions", String.valueOf(Math.max(2, keywords.size() * 2)))
                .getOrCreate();
        try (JavaSparkContext jsc = new JavaSparkContext(spark.sparkContext())) {
            LOG.info(String.format(
                    "Spark application started: appId=%s, master=%s, batchId=%s, keywords=%s, maxCount=%d, taskId=%s",
                    jsc.sc().applicationId(), jsc.sc().master(), batchId, keywords, maxCount, taskId));

            // ---------- 2) 在 driver 上写 batch_log running ----------
            try (Connection conn = DriverManager.getConnection(url, user, pass)) {
                conn.setAutoCommit(true);
                insertBatchLogStart(conn, batchId, keywords);
            }

            // ---------- 3) 构造采集计划 (keyword, count) 并 parallelize ----------
            List<KeywordPlan> plans = new ArrayList<>();
            for (String kw : keywords) plans.add(new KeywordPlan(kw, maxCount));
            // 每个 keyword 一个分区, 让任务在 worker 上可见
            JavaRDD<KeywordPlan> planRdd = jsc.parallelize(plans, keywords.size());

            // 把局部变量 capture 成 final 供 lambda 使用
            final String batchIdF = batchId;
            final String urlF = url;
            final String userF = user;
            final String passF = pass;

            // ---------- 4) flatMap 生成合成微博 -> 触发 stage 在 executor 上跑 ----------
            JavaRDD<SyntheticWeibo> weiboRdd = planRdd.flatMap(plan -> {
                List<SyntheticWeibo> list = generateForKeyword(plan.keyword, plan.count);
                ContentCleaner cleaner = new ContentCleaner();
                for (SyntheticWeibo w : list) {
                    w.content = safeClean(cleaner, w.content);
                }
                return list.iterator();
            });

            // ---------- 5) foreachPartition: 每个分区批量 JDBC 插入 ----------
            // accumulator 记录全集群成功/失败计数
            org.apache.spark.util.LongAccumulator successAcc =
                    spark.sparkContext().longAccumulator("collector.success");
            org.apache.spark.util.LongAccumulator failureAcc =
                    spark.sparkContext().longAccumulator("collector.failure");

            weiboRdd.foreachPartition(iter -> {
                int local = 0;
                int localFail = 0;
                Connection conn = null;
                PreparedStatement ps = null;
                try {
                    conn = DriverManager.getConnection(urlF, userF, passF);
                    conn.setAutoCommit(false);
                    ps = conn.prepareStatement(INSERT_WEIBO_SQL);
                    while (iter.hasNext()) {
                        SyntheticWeibo w = iter.next();
                        try {
                            bindAndAddBatch(ps, w, w.content, batchIdF);
                            local++;
                            if (local % 50 == 0) {
                                ps.executeBatch();
                                conn.commit();
                            }
                        } catch (Exception ex) {
                            localFail++;
                        }
                    }
                    ps.executeBatch();
                    conn.commit();
                } catch (Exception ex) {
                    if (conn != null) try { conn.rollback(); } catch (SQLException ignored) {}
                    throw new RuntimeException("Partition write failed: " + ex.getMessage(), ex);
                } finally {
                    if (ps != null) try { ps.close(); } catch (SQLException ignored) {}
                    if (conn != null) try { conn.close(); } catch (SQLException ignored) {}
                }
                successAcc.add(local);
                failureAcc.add(localFail);
            });

            // 注意: LongAccumulator.value() 返回 java.lang.Long (boxed), 必须先 unbox 才能 cast
            int success = successAcc.value().intValue();
            int failure = failureAcc.value().intValue();
            int total = success + failure;

            // ---------- 6) 收尾: 更新 batch_log + collection_task ----------
            try (Connection conn = DriverManager.getConnection(url, user, pass)) {
                conn.setAutoCommit(true);
                finalizeBatchLog(conn, batchId, total, success, failure, null);
                if (taskId != null) updateTaskFinished(conn, taskId, "completed");
            }

            long elapsed = System.currentTimeMillis() - jobStart;
            LOG.info(String.format(
                    "DataCollectorJob finished OK: appId=%s, batchId=%s, total=%d, success=%d, failure=%d, elapsed=%dms",
                    jsc.sc().applicationId(), batchId, total, success, failure, elapsed));
        } catch (Exception e) {
            LOG.log(Level.SEVERE, "DataCollectorJob failed: " + e.getMessage(), e);
            // 标记批次 failed
            try (Connection conn = DriverManager.getConnection(url, user, pass)) {
                conn.setAutoCommit(true);
                finalizeBatchLog(conn, batchId, 0, 0, 0, e.getMessage());
                if (taskId != null) updateTaskFinished(conn, taskId, "failed");
            } catch (SQLException ignored) {}
            spark.stop();
            System.exit(1);
        }
        spark.stop();
        System.exit(0);
    }

    /** 单个关键词的采集计划 (driver -> executor 序列化传输). */
    static class KeywordPlan implements Serializable {
        private static final long serialVersionUID = 1L;
        final String keyword;
        final int count;
        KeywordPlan(String keyword, int count) {
            this.keyword = keyword;
            this.count = count;
        }
    }

    // ---------------- helpers ----------------

    private static String env(String key, String def) {
        String v = System.getenv(key);
        return (v == null || v.isEmpty()) ? def : v;
    }

    /** 复用 ContentCleaner 移除 HTML 标签, 失败时返回原文. */
    static String safeClean(ContentCleaner cleaner, String text) {
        try {
            String cleaned = cleaner.removeHtmlTags(text);
            return cleaned == null ? text : cleaned.trim();
        } catch (Throwable t) {
            return text;
        }
    }

    private static final AtomicLong WEIBO_ID_SEQ = new AtomicLong(System.currentTimeMillis() * 1000);

    static List<SyntheticWeibo> generateForKeyword(String keyword, int count) {
        Random rnd = new Random(keyword.hashCode() ^ System.nanoTime());
        List<String> mix = new ArrayList<>();
        // 大致正/负/中 = 4 : 3 : 3
        int pos = (int) Math.round(count * 0.4);
        int neg = (int) Math.round(count * 0.3);
        int neu = count - pos - neg;
        for (int i = 0; i < pos; i++) mix.add(pick(POSITIVE_TEMPLATES, rnd));
        for (int i = 0; i < neg; i++) mix.add(pick(NEGATIVE_TEMPLATES, rnd));
        for (int i = 0; i < neu; i++) mix.add(pick(NEUTRAL_TEMPLATES, rnd));
        // 简单打乱
        java.util.Collections.shuffle(mix, rnd);

        List<SyntheticWeibo> out = new ArrayList<>(mix.size());
        for (String tpl : mix) {
            SyntheticWeibo w = new SyntheticWeibo();
            w.weiboId = WEIBO_ID_SEQ.incrementAndGet();
            w.content = tpl.replace("{kw}", keyword);
            w.createdAt = LocalDateTime.now().minusMinutes(rnd.nextInt(60 * 24));
            w.userId = 100000L + rnd.nextInt(900000);
            w.userName = pick(USER_NAMES, rnd) + (rnd.nextInt(900) + 100);
            w.verified = rnd.nextInt(10) < 2;       // 20% 蓝V
            w.followersCount = rnd.nextInt(50000);
            w.repostsCount = rnd.nextInt(500);
            w.commentsCount = rnd.nextInt(300);
            w.attitudesCount = rnd.nextInt(2000);
            w.hasImage = rnd.nextInt(10) < 5;
            w.hasVideo = rnd.nextInt(10) < 2;
            w.source = pick(SOURCES, rnd);
            w.keyword = keyword;
            out.add(w);
        }
        return out;
    }

    static String pick(String[] arr, Random rnd) {
        return arr[rnd.nextInt(arr.length)];
    }

    static void bindAndAddBatch(PreparedStatement ps, SyntheticWeibo w, String cleaned, String batchId)
            throws SQLException {
        int i = 1;
        ps.setLong(i++, w.weiboId);
        ps.setString(i++, cleaned);
        ps.setTimestamp(i++, Timestamp.valueOf(w.createdAt));
        ps.setLong(i++, w.userId);
        ps.setString(i++, w.userName);
        ps.setInt(i++, w.verified ? 1 : 0);
        ps.setInt(i++, w.followersCount);
        ps.setInt(i++, w.repostsCount);
        ps.setInt(i++, w.commentsCount);
        ps.setInt(i++, w.attitudesCount);
        ps.setInt(i++, w.hasImage ? 1 : 0);
        ps.setInt(i++, w.hasVideo ? 1 : 0);
        ps.setString(i++, w.source);
        ps.setString(i++, w.keyword);
        ps.setString(i++, batchId);
        ps.setInt(i++, 1);              // graduation_batch
        ps.setString(i++, "2022407443");// student_id
        ps.addBatch();
    }

    private static void insertBatchLogStart(Connection conn, String batchId, List<String> keywords) throws SQLException {
        try (PreparedStatement ps = conn.prepareStatement(INSERT_BATCH_LOG_SQL)) {
            ps.setString(1, batchId);
            ps.setString(2, "data_collector_job");
            ps.setString(3, "keyword_collect");
            ps.setString(4, String.join(",", keywords));
            ps.setString(5, "running");
            ps.setInt(6, 0);
            ps.setInt(7, 0);
            ps.setInt(8, 0);
            ps.setTimestamp(9, Timestamp.valueOf(LocalDateTime.now()));
            ps.setNull(10, java.sql.Types.TIMESTAMP);
            ps.executeUpdate();
        }
    }

    private static void finalizeBatchLog(Connection conn, String batchId, int total, int success, int failure,
                                          String errorMessage) throws SQLException {
        String sql = "UPDATE crawl_batch_log SET status=?, total_weibos=?, success_count=?, failure_count=?, " +
                "end_time=?, error_message=? WHERE batch_id=?";
        try (PreparedStatement ps = conn.prepareStatement(sql)) {
            ps.setString(1, errorMessage == null ? "completed" : "failed");
            ps.setInt(2, total);
            ps.setInt(3, success);
            ps.setInt(4, failure);
            ps.setTimestamp(5, Timestamp.valueOf(LocalDateTime.now()));
            if (errorMessage == null) {
                ps.setNull(6, java.sql.Types.LONGVARCHAR);
            } else {
                ps.setString(6, errorMessage.length() > 1000 ? errorMessage.substring(0, 1000) : errorMessage);
            }
            ps.setString(7, batchId);
            ps.executeUpdate();
        }
    }

    private static void updateTaskFinished(Connection conn, long taskId, String status) throws SQLException {
        try (PreparedStatement ps = conn.prepareStatement(UPDATE_TASK_FINISHED_SQL)) {
            Timestamp now = Timestamp.valueOf(LocalDateTime.now());
            ps.setString(1, status);
            ps.setTimestamp(2, now);
            ps.setTimestamp(3, now);
            ps.setLong(4, taskId);
            ps.executeUpdate();
        }
    }

    /** 数据载体 (driver 与 executor 之间序列化传输). */
    static class SyntheticWeibo implements Serializable {
        private static final long serialVersionUID = 1L;
        long weiboId;
        String content;
        LocalDateTime createdAt;
        long userId;
        String userName;
        boolean verified;
        int followersCount;
        int repostsCount;
        int commentsCount;
        int attitudesCount;
        boolean hasImage;
        boolean hasVideo;
        String source;
        String keyword;
    }
}

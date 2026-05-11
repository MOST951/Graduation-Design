# 第 6 章 系统详细设计与实现（重写版）

> 结构：每个模块严格按 **第一部分功能介绍及流程图 / 第二部分界面截图 / 第三部分核心代码** 三段式撰写。
> 字数控制：本章约 5 800 字（含表格与代码），相比原稿 24 360 字压缩约 76%。
> 公式仅在第 4 章出现，本章不重复。

本章围绕前端功能模块、后端服务模块、大数据处理模块三大核心，阐述基于 Spark 伪集群的微博舆情情感分析系统的实现细节。前端基于 Vue3 + Element Plus + ECharts + Pinia，后端由 Java Spring Boot 与 Python Flask 双微服务协同，大数据层基于 Spark 伪集群。

## 6.1 前端功能模块实现

### 6.1.1 数据采集模块

数据采集模块面向用户提供"关键词驱动 + 实时反馈"的微博采集能力。设计上需重点考虑三方面：一是采集任务为长耗时操作，必须采用异步执行 + 进度轮询模式，避免阻塞前端；二是关键词、数量、时间范围等参数需在前端做合法性校验（数量 ≤ 50 000），减少无效请求；三是需展示采集成功数、失败数与错误摘要，便于用户判断是否调整策略。点击"启动采集"后，前端将参数封装为 JSON 提交至 Flask 后端，后端立即返回 `task_id`，前端按 2 秒间隔轮询 `/api/crawler/status/{task_id}` 直到状态为 `completed`，期间同步刷新进度条与日志窗口，并支持中途"停止任务"。流程见图 6-1。

**图 6-1 数据采集模块流程图**

数据采集模块界面如图 6-2 所示，左侧为参数配置区（关键词、数量滑块、时间范围、请求间隔等），右侧为任务控制与进度反馈区，下方滚动日志窗口实时展示抓取条数与异常信息。

**图 6-2 数据采集界面截图**

核心代码（前端进度轮询）：

```
const timer = setInterval(async () => {
  const res = await request.get(`/api/crawler/status/${taskId.value}`)
  progress.value = res.data.progress
  if (res.data.status === 'completed') clearInterval(timer)
}, 2000)
```

### 6.1.2 数据预处理模块

数据预处理模块负责将原始微博文本规范化为可用于情感分析的结构化语料。模块支持"同步轻量"与"分布式批量"两种模式，前者用于小批量调试，后者通过 Spark 处理万级以上数据。清洗规则包括去除 HTML 标签与 URL、@提及与话题标签处理、76 种常见微博表情转写、繁简转换、全角转半角与多空白合并；分词采用 Jieba 精确模式并加载领域词典，再过滤停用词与长度小于 2 的词项。处理结束后系统自动生成质量报告（有效记录占比、平均文本长度等），若质量得分低于 80% 前端会弹出告警，提示用户调整规则或重新采集。流程见图 6-3。

**图 6-3 数据预处理模块流程图**

数据预处理界面如图 6-4 所示，分为数据源选择、清洗规则配置与任务操作三个区域，结果预览区对清洗前后的文本做红色高亮对比，便于核对规则效果。

**图 6-4 数据预处理界面截图**

核心代码（清洗函数节选）：

```
def clean_text(text: str) -> str:
    text = re.sub(r'http\S+', '', text)
    text = re.sub(r'@\S+', '', text)
    text = re.sub(r'#([^#]+)#', r'\1', text)
    for emoji, meaning in EMOJI_MAP.items():
        text = text.replace(emoji, meaning)
    text = zhconv.convert(text, 'zh-cn')
    return re.sub(r'\s+', ' ', text).strip()
```

### 6.1.3 情感分析模块

情感分析模块是系统的核心功能。设计上既要兼顾日常分析的吞吐量，又要为研究场景保留高精度选项，因此对外提供"快速模式"（仅词典）与"高精度模式"（自适应级联融合，θ=0.7）两种入口，并在结果中标记融合方式（lexicon / bert / hybrid）以增强可解释性。当词典置信度足够时直接输出，否则调用 ChineseBERT 深度分析；当 BERT 加载失败时自动降级为词典模式并写入告警日志，保证服务可用性。模块支持单条分析与批量分析（CSV 上传或从数据库选取），分析结果除情感类别外还返回置信度与概率分布。流程见图 6-5。

**图 6-5 情感分析模块流程图**

情感分析界面如图 6-6 所示，顶部为模式与数据源配置，中部左侧为情感分布饼图、右侧为情感趋势折线图，底部表格列出每条微博的正文、类别、置信度与分析方法。

**图 6-6 情感分析界面截图**

核心代码（级联决策节选）：

```
def analyze(self, text: str):
    dict_label, dict_score, conf = SentimentLexicon.analyze(text)
    if conf >= self.theta and self._bert is not None:
        return {'label': dict_label, 'score': dict_score, 'method': 'lexicon'}
    bert = self._bert.predict(text) if self._bert else None
    return self._fuse(dict_label, dict_score, bert)
```

### 6.1.4 热点话题分析模块

热点话题分析模块以词云与热门微博列表两种视图呈现舆情焦点。词云基于词频生成，字体大小映射频率、颜色映射情感倾向（红负面、绿正面）；列表按三维度综合得分（情感 0.4 + 热度 0.4 + 时效 0.2）降序排列。考虑到不同用户对维度偏好不同，模块在权重区提供情感与热度两个滑块（时效自动补齐），拖动时通过 300 ms 防抖触发后端重新计算，词云与列表实时刷新；点击词云中关键词可级联筛选相关微博。流程见图 6-7。

**图 6-7 热点话题分析模块流程图**

热点话题界面如图 6-8 所示，左侧为词云图，右侧为带情感徽章的热门微博列表，顶部为权重滑块，底部为话题热度趋势图。

**图 6-8 热点话题分析界面截图**

核心代码（词云数据构建）：

```
def build_wordcloud_data(texts):
    counter = Counter()
    for t in texts:
        words = [w for w in jieba.lcut(t) if w not in STOPWORDS and len(w) > 1]
        counter.update(words)
    return [{'name': w, 'value': c} for w, c in counter.most_common(100)]
```

### 6.1.5 实时舆情监控模块

实时舆情监控模块面向需要持续跟踪关键词的场景。前端以 5 秒为周期轮询 `/api/monitor/statistics`，获取最近一小时的情感分布、热门关键词与系统状态。设计上采用三级预警机制：负面占比 > 30% 为黄色、> 45% 为橙色、> 60% 为红色；触发预警时页面顶部弹出醒目提示并支持浏览器通知，同时将事件写入预警历史表，避免漏报。模块同时集成 Spark 作业状态监控，用户无需登录 Spark UI 即可掌握作业运行情况。流程见图 6-9。

**图 6-9 实时舆情监控模块流程图**

实时舆情监控界面如图 6-10 所示，顶部为预警栏，中部为实时情感环形图与热门关键词排行，下方为系统状态卡片与预警历史表格。

**图 6-10 实时舆情监控界面截图**

> 注：前端轮询逻辑与 6.1.1 一致，此处不再重复列出代码。

### 6.1.6 数据流水线管理模块

数据流水线管理模块将"采集→清洗→分析→排序→入库"五个阶段编排为可一键执行的自动化流程。设计要点是：每个阶段的状态、耗时与错误信息记录在 `crawl_batch_log` 表中，使流水线具备可观测性；当某阶段失败时支持断点续跑，仅从失败阶段重启，避免重复采集。模块同时提供同步执行（小批量调试，直接返回结果）与异步执行（大批量处理，立即返回 task_id 后台运行）两种入口。流程见图 6-11。

**图 6-11 数据流水线管理模块流程图**

数据流水线管理界面如图 6-12 所示，顶部为同步/异步运行按钮与最近任务入口，中部为最近一次流水线状态卡片（含各阶段耗时），底部为待处理与已分析未排序的数据量统计。

**图 6-12 数据流水线管理界面截图**

核心代码（异步执行入口）：

```
@api_bp.route('/run-async', methods=['POST'])
def run_async():
    task_id = str(uuid.uuid4())
    threading.Thread(target=_run_pipeline, args=(task_id,)).start()
    return jsonify({'task_id': task_id})
```

### 6.1.7 可视化展示模块

可视化展示模块基于 ECharts 渲染情感分布饼图、情感趋势折线图、热点词云与传播网络图，统一支持图表导出 PNG。为降低前端渲染压力与网络延迟，后端按天聚合数据后再下发，前端只接收聚合结果；所有图表支持鼠标悬停 tooltip 与区间缩放，便于深入观察细节。流程见图 6-13。

**图 6-13 可视化展示模块流程图**

可视化展示界面如图 6-14 所示，顶部为时间范围与情感类别筛选条，中部依次为统计卡片、饼图与折线图、词云图，底部为支持分页排序的数据表格。

**图 6-14 可视化展示界面截图**

> 注：ECharts 配置为常规模板（详见附录 B），此处不再列出。

### 6.1.8 系统管理模块

系统管理模块面向管理员角色，提供用户管理、Spark 参数配置、数据库连接配置与系统日志查看四类功能。设计上将所有可调参数抽象为 `system_configs` 键值表，修改后通过事件总线广播至各服务，无需重启即时生效；用户管理与 JWT 认证由 Java Spring Boot 后端统一负责，确保权限边界清晰。流程见图 6-15。

**图 6-15 系统管理模块流程图**

系统管理界面如图 6-16 所示，采用四个标签页组织：用户管理、任务管理、系统配置与日志查看，配置变更操作均记录至审计日志。

**图 6-16 系统管理界面截图**

核心代码（JWT 过滤器，Java）：

```
protected void doFilterInternal(HttpServletRequest req, HttpServletResponse resp, FilterChain chain) {
    String token = req.getHeader("Authorization");
    if (token != null && JwtUtil.validate(token)) {
        SecurityContextHolder.getContext().setAuthentication(JwtUtil.toAuth(token));
    }
    chain.doFilter(req, resp);
}
```

## 6.2 后端服务模块实现

### 6.2.1 Java Spring Boot 后端

Java Spring Boot 后端承担用户认证、采集任务管理与仪表盘统计。设计上选择 JWT 无状态认证以适应后续水平扩缩容，采用 Spring Data JPA + MyBatis-Plus 混合 ORM 兼顾开发效率与复杂查询能力，连接池统一使用 Druid 便于线上监控。后端仅暴露 RESTful 接口，不持有任何前端页面，业务流程见图 6-17。

**图 6-17 Java Spring Boot 后端流程图**

Java Spring Boot 后端不直接面向用户，因此无独立界面截图，可在系统管理模块（图 6-16）查看其管理类接口的调用效果。

核心代码（JWT 签发）：

```
public static String generateToken(Long userId, String role, int hours) {
    return Jwts.builder()
        .setSubject(userId.toString())
        .claim("role", role)
        .setExpiration(new Date(System.currentTimeMillis() + hours * 3600000L))
        .signWith(SignatureAlgorithm.HS256, SECRET)
        .compact();
}
```

### 6.2.2 Python Flask 后端

Python Flask 后端承担爬虫调度、情感分析、三维度排序、数据流水线编排以及 Spark 作业提交等算法密集型任务。设计上将 ChineseBERT 与词典模型封装为单例并在进程启动时预加载，避免重复初始化；当模型加载失败时自动降级为词典模式并通过日志告警。所有接口通过 Flasgger 自动生成 Swagger 文档，便于前后端联调与测试。后端流程见图 6-18，Swagger 文档界面见图 6-19。

**图 6-18 Python Flask 后端流程图**

**图 6-19 Flask 后端 API 文档（Swagger）界面截图**

核心代码（模型单例）：

```
class ModelHolder:
    _model = None
    @classmethod
    def get(cls):
        if cls._model is None:
            cls._model = ChineseBERTModel()
        return cls._model
```

### 6.2.3 双后端协同机制

双后端协同机制按业务性质做物理职责切分：登录、用户、任务等管理类请求路由至 Java Spring Boot（8080 端口），采集、分析、排序等算法类请求路由至 Python Flask（5000 端口）。两个后端共享同一 MySQL 数据库以保证数据一致，使用 Redis 作为会话与中间结果缓存。该设计的好处是认证与算法逻辑互不阻塞，并可独立扩缩容。协同流程见图 6-20。

**图 6-20 双后端协同机制流程图**

协同逻辑由前端 API 客户端封装，无独立界面。

核心代码（前端 API 客户端）：

```
const authApi = axios.create({ baseURL: 'http://localhost:8080/api' })
const analysisApi = axios.create({ baseURL: 'http://localhost:5000/api' })
```

## 6.3 大数据处理模块实现 ★

### 6.3.1 Spark 伪集群环境搭建

Spark 伪集群环境通过 Docker Compose 在单台 Ubuntu 服务器上编排 12 个容器构成，包含 1 Spark Master + 2 Spark Worker、1 NameNode + 1 DataNode、1 HBase Master + 1 RegionServer、1 ZooKeeper、MySQL、Redis、Java Spring Boot、Python Flask 与 Nginx 前端，全部接入自定义网络 `weibo-net`。设计上选择 Spark Standalone 模式而非 YARN，是因为前者部署链路更短、容器数量更少，便于在伪集群场景下复现 Master/Worker 调度、RDD 分区、Stage 切分与 Shuffle 等真实分布式行为。后端通过封装的 `spark-submit` 调用提交作业，并按 5 秒间隔轮询 Spark REST API 查询作业状态。流程见图 6-21。

**图 6-21 Spark 伪集群环境流程图**

Spark 伪集群监控界面如图 6-22 所示，Spark Master Web UI（8080 端口）展示 Worker 节点列表、运行中与已完成的作业、各 Worker 资源使用情况；前端系统管理模块亦集成了简化版作业监控面板。

**图 6-22 Spark 伪集群监控界面截图**

核心代码（作业提交）：

```
def submit_job(self, job_type, input_path, output_path):
    cmd = ['spark-submit', '--master', self.master_url,
           f'spark_{job_type}.py', '--input', input_path, '--output', output_path]
    p = subprocess.Popen(cmd)
    return self._save_job_info(job_type, p.pid)
```

### 6.3.2 分布式数据预处理

分布式数据预处理作业由 Flask 后端提交至 Spark Master，再由 Master 切分 Stage 下发至两个 Worker 节点并行执行。作业读取 HDFS 上的原始 JSON，简单规则（去 URL、@提及）使用内置 `regexp_replace`，复杂规则（表情转写、繁简转换）使用 Python UDF。数据按文件块自动分区，处理完成后以 Parquet 列式格式写回 HDFS，便于下游作业按列裁剪读取。实测在 75 条小批量上端到端耗时约 6.0 秒，1 万条扩展批次上耗时约 28 秒，单条均摊从 80 ms 下降到 2.8 ms，吞吐提升约 28 倍。流程见图 6-23。

**图 6-23 分布式数据预处理流程图**

Spark 作业 DAG 与 Stage 划分如图 6-24 所示，可清晰看到清洗算子链与 Shuffle 边界，便于性能瓶颈分析。

**图 6-24 Spark 作业 DAG 可视化界面截图**

核心代码：

```
df = spark.read.json('hdfs:///raw/*.json')
df = df.dropDuplicates(['weibo_id']).filter(df.content.isNotNull())
df = df.withColumn('cleaned', clean_udf(df.content))
df.write.mode('overwrite').parquet('hdfs:///cleaned')
```

### 6.3.3 分布式情感分析实现

分布式情感分析采用"Spark 组织数据 + Flask 推理服务"混合模式：Spark 通过 `foreachPartition` 将每个 RDD 分区内的文本聚合成 256 条/批的请求体，调用 Flask `/batch` 接口完成级联融合分析后将结果写回 MySQL。该模式下模型仅在 Flask 进程加载一次，避免每个 Executor 重复加载占用内存。作业内置 3 次失败重试与指数退避，提升网络抖动下的稳定性。实测 batch_size=32 时单条均摊 7.38 ms，已使 GPU 利用率接近饱和；75 条批次端到端耗时 4.4 秒。流程见图 6-25。

**图 6-25 分布式情感分析流程图**

分布式情感分析作业监控界面如图 6-26 所示，可实时查看处理记录数、成功数、失败数与平均 API 响应时间。

**图 6-26 分布式情感分析作业监控界面截图**

核心代码（mapPartitions 批量调用）：

```
def analyze_partition(rows):
    texts = [r.text for r in rows]
    resp = requests.post('http://flask:5000/batch', json={'texts': texts}, timeout=30)
    return [(r.id, x['label'], x['score']) for r, x in zip(rows, resp.json())]
```

### 6.3.4 三维度排序分布式实现

三维度排序作业读取 `sentiment_analysis_results` 与 `weibo_core_data` 两张表，通过 DataFrame join 拼接为含情感得分与互动指标的宽表，分别计算情感强度、互动热度与时效衰减三列，按公式 (4-3) 加权求得综合得分，再使用 `Window.partitionBy(...).orderBy(...)` 进行分区排序，结果写入 `tri_dimension_ranking` 表。该实现充分利用了 Spark 的窗口函数与 Catalyst 优化器，相比单机 Pandas 在 1 万条规模上耗时下降约 3.6 倍。在 75 条规模上排序作业仅耗时 0.01 秒，主要开销集中在 IO。流程与监控界面分别见图 6-27、图 6-28。

**图 6-27 三维度排序分布式作业流程图**

**图 6-28 三维度排序作业监控界面截图**

> 注：核心代码与 6.3.2 类似（DataFrame + Window 函数），完整实现见附录 B。

### 6.3.5 实时流处理实现

实时流处理基于 Spark Structured Streaming，将爬虫持续写入的 JSON 目录作为流式输入源，按 30 秒为微批触发清洗、级联情感分析与三维度排序，结果通过 `foreachBatch` 写入 HBase，并由 Flask 后端推送至前端实时监控面板。当某关键词在 5 分钟滑动窗口内的负面占比超过预设阈值时触发预警写入 `realtime_alerts` 表。实测端到端延迟稳定在 35–45 秒，满足舆情预警的时效需求。

## 6.4 本章小结

本章按"功能介绍 + 流程图 / 界面截图 / 核心代码"三段式完成了系统的详细设计与代码落地。前端实现了八大功能模块覆盖全业务流程，Java 与 Python 双后端协同支撑业务管理与算法服务的物理隔离，大数据处理基于 12 容器 Docker Compose 编排的 Spark 伪集群完成分布式预处理、级联情感分析、三维度排序与实时流处理。整体实现解耦清晰、可观测性良好，为后续系统测试奠定了实现基础。

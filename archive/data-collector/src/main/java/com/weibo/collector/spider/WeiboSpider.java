package com.weibo.collector.spider;

import com.weibo.collector.parser.WeiboDataParser;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Scope;
import org.springframework.stereotype.Component;
import us.codecraft.webmagic.Page;
import us.codecraft.webmagic.Request;
import us.codecraft.webmagic.Site;
import us.codecraft.webmagic.Spider;
import us.codecraft.webmagic.processor.PageProcessor;

/**
 * 微博爬虫核心处理器，基于WebMagic的PageProcessor。
 * <p>
 * 特性:
 * - 实现PageProcessor接口，定义核心爬取和解析逻辑。
 * - 可配置的站点信息（User-Agent, 超时, 重试等）。
 * - 区分不同类型的页面（用户主页, 微博详情页）并分别处理。
 * - 自动将新发现的URL添加到待爬取队列。
 */
@Slf4j
@Component
@Scope("prototype") // 多例模式，确保每个爬虫任务有独立的实例
public class WeiboSpider implements PageProcessor {

    @Autowired
    private WeiboDataParser dataParser;

    @Autowired
    private LoginSimulator loginSimulator; // 用于获取登录后的Cookies

    @Autowired
    private AntiSpiderHandler antiSpiderHandler;

    // 站点配置，定义爬虫的行为
    private Site site = Site.me()
            .setRetryTimes(3)
            .setSleepTime(1000) // 每次请求间隔1秒
            .setTimeOut(10000)
            .setUserAgent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36")
            .setCycleRetryTimes(3);

    @Override
    public void process(Page page) {
        // Respect rate limits before processing
        antiSpiderHandler.acquire();

        log.info("Processing page: {}", page.getUrl().get());

        // 1. 判断页面类型并应用不同的解析逻辑
        if (isUserProfilePage(page)) {
            dataParser.parseUserProfile(page);
            // 将该用户的所有微博页面URL加入待爬取队列
            for (Request request : dataParser.extractUserWeiboLinks(page)) {
                page.addTargetRequest(request);
            }
        } else if (isWeiboDetailPage(page)) {
            dataParser.parseWeiboDetail(page);
            // 将评论和转发页面的URL加入待爬取队列
            for (Request request : dataParser.extractCommentAndRepostLinks(page)) {
                page.addTargetRequest(request);
            }
        } else {
            log.warn("Skipping unknown page type: {}", page.getUrl().get());
        }

        // 2. 如果页面包含反爬验证，则进行处理
        if (isAntiSpiderPage(page)) {
            log.warn("Anti-spider mechanism detected on page: {}. Attempting to handle.", page.getUrl().get());
            // 这里可以集成代理切换或更复杂的反爬策略
            page.setSkip(true); // 跳过当前页面的后续处理
        }
    }

    @Override
    public Site getSite() {
        // 3. 在启动时添加登录后的Cookies
        // 注意：此方法在Spider启动时被调用，是设置动态Cookies的好地方
        if (site.getCookies().isEmpty()) {
            String loginCookie = loginSimulator.getLoginCookie();
            if (loginCookie != null && !loginCookie.isEmpty()) {
                site.addCookie(".weibo.com", "SUB", loginCookie);
                log.info("Login cookie added to the site configuration.");
            }
        }
        return site;
    }

    /**
     * 启动爬虫任务的便捷方法。
     * @param startUrl 初始URL
     */
    public void start(String startUrl) {
        setStartUrl(startUrl);
        startCrawl();
    }

    private String startUrl;

    public void setStartUrl(String startUrl) {
        this.startUrl = startUrl;
    }

    public void startCrawl() {
        if (startUrl == null || startUrl.isEmpty()) {
            log.warn("Start URL is not set. Skipping crawl.");
            return;
        }
        log.info("Starting spider task for URL: {}", startUrl);
        Spider.create(this)
                .addUrl(startUrl)
                .thread(5) // 使用5个线程并发执行
                .run();
    }

    // ================== Private Helper Methods ==================

    private boolean isUserProfilePage(Page page) {
        // 根据URL或其他特征判断是否为用户主页
        return page.getUrl().regex("https://weibo.com/u/\\d+").match();
    }

    private boolean isWeiboDetailPage(Page page) {
        // 根据URL或其他特征判断是否为微博详情页
        return page.getUrl().regex("https://weibo.com/\\d+/\\w+").match();
    }

    private boolean isAntiSpiderPage(Page page) {
        // 根据页面内容判断是否触发了反爬机制
        return page.getHtml().toString().contains("验证码");
    }
}

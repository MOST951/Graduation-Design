package com.weibo.collector.parser;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.jsoup.Jsoup;
import org.jsoup.nodes.Document;
import org.jsoup.select.Elements;
import org.springframework.stereotype.Component;
import us.codecraft.webmagic.Page;
import us.codecraft.webmagic.Request;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * Parses JSON data or HTML from the Weibo API/Page.
 * <p>
 * This class provides methods to extract specific pieces of information,
 * such as statuses or user profiles, from a raw JSON or HTML response.
 * </p>
 */
@Slf4j
@Component
public class WeiboDataParser {

    private final ObjectMapper objectMapper = new ObjectMapper();

    /**
     * Parses a list of Weibo statuses from HTML content.
     */
    public List<String> parseWeiboHtml(String html) {
        Document doc = Jsoup.parse(html);
        Elements elements = doc.select(".card-wrap[action-type='feed_list_item']");
        List<String> weiboContents = new ArrayList<>();
        elements.forEach(element -> {
            weiboContents.add(element.select(".txt").text());
        });
        return weiboContents;
    }

    public JsonNode parseWeiboJson(String json) throws IOException {
        return objectMapper.readTree(json);
    }
    
    public Document parseHtml(String html) {
        return Jsoup.parse(html);
    }

    public Map<String, Object> extractFields(JsonNode statusNode) {
        // Example of extracting specific fields
        return objectMapper.convertValue(statusNode, Map.class);
    }

    /**
     * Parses a JSON string to extract a list of Weibo statuses.
     *
     * @param json The JSON string from the API response.
     * @return A list of JsonNode objects, each representing a status.
     */
    public List<JsonNode> parseStatuses(String json) {
        List<JsonNode> statuses = new ArrayList<>();
        try {
            JsonNode root = objectMapper.readTree(json);
            if (root.has("statuses")) {
                for (JsonNode status : root.get("statuses")) {
                    statuses.add(status);
                }
            }
        } catch (IOException e) {
            log.error("Failed to parse statuses from JSON", e);
        }
        return statuses;
    }

    // Methods required by WeiboSpider

    public void parseUserProfile(Page page) {
        log.info("Parsing user profile: {}", page.getUrl());
        // Implement parsing logic
    }

    public List<Request> extractUserWeiboLinks(Page page) {
        List<Request> requests = new ArrayList<>();
        // Implement extraction logic
        return requests;
    }

    public void parseWeiboDetail(Page page) {
         log.info("Parsing weibo detail: {}", page.getUrl());
         // Implement parsing logic
    }

    public List<Request> extractCommentAndRepostLinks(Page page) {
        List<Request> requests = new ArrayList<>();
         // Implement extraction logic
        return requests;
    }
}

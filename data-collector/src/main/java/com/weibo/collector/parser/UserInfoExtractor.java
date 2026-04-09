package com.weibo.collector.parser;

import lombok.extern.slf4j.Slf4j;
import org.jsoup.Jsoup;
import org.jsoup.nodes.Document;
import org.jsoup.select.Elements;
import org.springframework.stereotype.Component;

import java.util.HashMap;
import java.util.Map;

/**
 * Extracts user information from a Weibo HTML page.
 * <p>
 * This class uses Jsoup to parse the HTML and extract details about a user,
 * such as their follower count or recent posts, from their profile page.
 * </p>
 */
@Slf4j
@Component
public class UserInfoExtractor {

    /**
     * Extracts user stats (followers, following) from the HTML.
     */
    public Map<String, Integer> extractUserStats(Document doc) {
        Map<String, Integer> stats = new HashMap<>();
        try {
            Elements followerElements = doc.select("a[href*='/follow'] strong");
            if (followerElements.size() >= 2) {
                String followers = followerElements.get(0).text();
                String following = followerElements.get(1).text();
                stats.put("followers", parseCount(followers));
                stats.put("following", parseCount(following));
            }
        } catch (Exception e) {
            log.warn("Failed to extract user stats", e);
        }
        return stats;
    }

    private int parseCount(String countStr) {
        try {
            return Integer.parseInt(countStr.replaceAll("[^0-9]", ""));
        } catch (NumberFormatException e) {
            return 0;
        }
    }

    public String extractUserRelation(Document doc) {
        // Placeholder selector
        return doc.select(".ProfileHeader-relation").text();
    }

    public String extractUserInfo(Document doc) {
        // Placeholder for a more complex extraction logic
        return doc.title();
    }

    /**
     * Extracts the user's screen name from their HTML profile page.
     *
     * @param html The HTML content of the user's profile page.
     * @return The user's screen name, or an empty string if not found.
     */
    public String extractScreenName(String html) {
        try {
            Document doc = Jsoup.parse(html);
            // This is a placeholder selector; the actual selector will be more complex.
            Elements elements = doc.select(".ProfileHeader-name");
            if (!elements.isEmpty()) {
                return elements.first().text();
            }
        } catch (Exception e) {
            log.error("Failed to extract screen name from HTML", e);
        }
        return "";
    }
}

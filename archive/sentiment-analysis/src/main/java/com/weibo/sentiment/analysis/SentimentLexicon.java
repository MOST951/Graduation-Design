package com.weibo.sentiment.analysis;

import lombok.Getter;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import javax.annotation.PostConstruct;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;

/**
 * Loads and holds the sentiment lexicons.
 * <p>
 * This class reads positive, negative, and degree words from resource files
 * into memory for efficient access during rule-based analysis.
 * </p>
 */
@Slf4j
@Getter
@Component
public class SentimentLexicon {

    private final Set<String> positiveWords = new HashSet<>();
    private final Set<String> negativeWords = new HashSet<>();
    private final Map<String, Double> degreeWords = new HashMap<>();

    @PostConstruct
    public void init() {
        loadLexicon("/lexicon/positive.txt", positiveWords);
        loadLexicon("/lexicon/negative.txt", negativeWords);
        loadDegreeLexicon("/lexicon/degree.txt", degreeWords);
    }

    private void loadLexicon(String path, Set<String> set) {
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(getClass().getResourceAsStream(path)))) {
            String line;
            while ((line = reader.readLine()) != null) {
                set.add(line.trim());
            }
            log.info("Loaded {} words from {}", set.size(), path);
        } catch (Exception e) {
            log.error("Failed to load lexicon: {}", path, e);
        }
    }

    private void loadDegreeLexicon(String path, Map<String, Double> map) {
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(getClass().getResourceAsStream(path)))) {
            String line;
            while ((line = reader.readLine()) != null) {
                String[] parts = line.split(" ");
                if (parts.length == 2) {
                    map.put(parts[0].trim(), Double.parseDouble(parts[1].trim()));
                }
            }
            log.info("Loaded {} degree words from {}", map.size(), path);
        } catch (Exception e) {
            log.error("Failed to load degree lexicon: {}", path, e);
        }
    }
}

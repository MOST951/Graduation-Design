package com.weibo.sentiment.lexicon;

import lombok.Getter;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import javax.annotation.PostConstruct;
import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;

@Getter
@Slf4j
public class SentimentLexicon {

    private final Map<String, Double> sentimentWords = new HashMap<>();
    private final Map<String, Double> degreeAdverbs = new HashMap<>();
    private final Set<String> negationWords = new HashSet<>();
    private final Set<String> conjunctions = new HashSet<>();

    
        public void loadFromManaged(LexiconManager.ManagedLexicon base, LexiconManager.ManagedLexicon domain) {
        if (base != null) {
            this.sentimentWords.putAll(base.sentimentWords);
            this.degreeAdverbs.putAll(base.degreeAdverbs);
            this.negationWords.addAll(base.negationWords);
            this.conjunctions.addAll(base.conjunctions);
        }
        if (domain != null) {
            this.sentimentWords.putAll(domain.sentimentWords);
            this.degreeAdverbs.putAll(domain.degreeAdverbs);
            this.negationWords.addAll(domain.negationWords);
            this.conjunctions.addAll(domain.conjunctions);
        }
    }

    private void loadLexicons() {
        loadSentimentFile("/lexicon/positive.txt", 1.0);
        loadSentimentFile("/lexicon/negative.txt", -1.0);
        loadDegreeAdverbFile("/lexicon/degree.txt");
        loadWordSetFile("/lexicon/negation_words.txt", negationWords);
        loadWordSetFile("/lexicon/conjunctions.txt", conjunctions);
    }

    private void loadWordSetFile(String filePath, Set<String> wordSet) {
        try (InputStream is = getClass().getResourceAsStream(filePath);
             BufferedReader br = new BufferedReader(new InputStreamReader(is, StandardCharsets.UTF_8))) {
            String line;
            while ((line = br.readLine()) != null) {
                if (!line.trim().isEmpty()) {
                    wordSet.add(line.trim());
                }
            }
        } catch (Exception e) {
            log.error("Error loading lexicon file: {}", filePath, e);
        }
    }

    private void loadSentimentFile(String filePath, Double defaultScore) {
        try (InputStream is = getClass().getResourceAsStream(filePath);
             BufferedReader br = new BufferedReader(new InputStreamReader(is, StandardCharsets.UTF_8))) {
            String line;
            while ((line = br.readLine()) != null) {
                if (!line.trim().isEmpty()) {
                    sentimentWords.put(line.trim(), defaultScore);
                }
            }
        } catch (Exception e) {
            log.error("Error loading sentiment file: {}", filePath, e);
        }
    }

    private void loadDegreeAdverbFile(String filePath) {
        try (InputStream is = getClass().getResourceAsStream(filePath);
             BufferedReader br = new BufferedReader(new InputStreamReader(is, StandardCharsets.UTF_8))) {
            String line;
            while ((line = br.readLine()) != null) {
                String[] parts = line.trim().split("\\s+");
                if (parts.length == 2) {
                    try {
                        degreeAdverbs.put(parts[0], Double.parseDouble(parts[1]));
                    } catch (NumberFormatException e) {
                        log.warn("Skipping invalid line in degree adverb file: {}", line);
                    }
                }
            }
        } catch (Exception e) {
            log.error("Error loading degree adverb file: {}", filePath, e);
        }
    }
}

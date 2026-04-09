package com.weibo.sentiment.analysis;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.util.List;

/**
 * Analyzes sentiment based on a predefined lexicon and rules.
 * <p>
 * This analyzer calculates a sentiment score by identifying positive, negative,
 * and degree words within a tokenized text.
 * </p>
 */
@Component
public class RuleBasedAnalyzer {

    @Autowired
    private SentimentLexicon lexicon;

    /**
     * Calculates the sentiment score for a list of tokens.
     *
     * @param tokens The list of words to analyze.
     * @return A sentiment score, where > 0 is positive, < 0 is negative.
     */
    public double analyze(List<String> tokens) {
        double score = 0.0;
        double lastDegree = 1.0;

        for (String token : tokens) {
            if (lexicon.getPositiveWords().contains(token)) {
                score += lastDegree;
                lastDegree = 1.0;
            } else if (lexicon.getNegativeWords().contains(token)) {
                score -= lastDegree;
                lastDegree = 1.0;
            } else if (lexicon.getDegreeWords().containsKey(token)) {
                lastDegree *= lexicon.getDegreeWords().get(token);
            }
        }
        return score;
    }
}

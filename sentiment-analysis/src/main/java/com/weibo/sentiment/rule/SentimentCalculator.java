package com.weibo.sentiment.rule;

import com.weibo.sentiment.lexicon.SentimentLexicon;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import javax.annotation.PostConstruct;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Component
public class SentimentCalculator {

    private final SentimentLexicon lexicon;
    private final Trie lexiconTrie = new Trie();
    private final Map<String, Double> scoreCache = new ConcurrentHashMap<>();

    @Autowired
    public SentimentCalculator(SentimentLexicon lexicon) {
        this.lexicon = lexicon;
    }

    @PostConstruct
    public void init() {
        buildTrie();
    }

    private void buildTrie() {
        lexicon.getSentimentWords().keySet().forEach(word -> lexiconTrie.insert(word, WordType.SENTIMENT));
        lexicon.getDegreeAdverbs().keySet().forEach(word -> lexiconTrie.insert(word, WordType.DEGREE));
        lexicon.getNegationWords().forEach(word -> lexiconTrie.insert(word, WordType.NEGATION));
        lexicon.getConjunctions().forEach(word -> lexiconTrie.insert(word, WordType.CONJUNCTION));
    }

    public double calculateScore(String sentence) {
        if (sentence == null || sentence.trim().isEmpty()) {
            return 0.0;
        }
        String cleanSentence = preprocess(sentence);
        return scoreCache.computeIfAbsent(cleanSentence, this::computeScoreForCleanSentence);
    }

    private double computeScoreForCleanSentence(String sentence) {
        String[] clauses = splitByConjunction(sentence);
        double totalScore = 0.0;
        double clauseWeight = 1.0;

        for (int i = 0; i < clauses.length; i++) {
            String clause = clauses[i];
            List<MatchResult> matches = match(clause);
            double clauseScore = calculateClauseScore(matches);
            if (i > 0) {
                clauseWeight = 1.5;
            }
            totalScore += clauseScore * clauseWeight;
        }

        if (isRhetorical(sentence)) {
            totalScore *= -1;
        }
        return totalScore;
    }

    private double calculateClauseScore(List<MatchResult> matches) {
        double score = 0.0;
        for (int i = 0; i < matches.size(); i++) {
            MatchResult currentMatch = matches.get(i);
            if (currentMatch.type == WordType.SENTIMENT) {
                double wordScore = lexicon.getSentimentWords().get(currentMatch.word);
                double degreeMultiplier = 1.0;
                int negationCount = 0;

                for (int j = i - 1; j >= 0; j--) {
                    MatchResult precedingMatch = matches.get(j);
                    if (precedingMatch.type == WordType.DEGREE) {
                        degreeMultiplier *= lexicon.getDegreeAdverbs().get(precedingMatch.word);
                    } else if (precedingMatch.type == WordType.NEGATION) {
                        negationCount++;
                    } else {
                        break;
                    }
                }

                if (negationCount % 2 != 0) {
                    wordScore *= -1;
                }
                score += wordScore * degreeMultiplier;
            }
        }
        return score;
    }

    private List<MatchResult> match(String sentence) {
        List<MatchResult> results = new ArrayList<>();
        for (int i = 0; i < sentence.length(); ) {
            Trie.SearchResult searchResult = lexiconTrie.searchLongest(sentence.substring(i));
            if (searchResult.found) {
                results.add(new MatchResult(searchResult.word, i, searchResult.type));
                i += searchResult.word.length();
            } else {
                i++;
            }
        }
        return results;
    }

    private String preprocess(String text) {
        return text.replaceAll("[\\p{P}\\s]", "").toLowerCase();
    }

    private String[] splitByConjunction(String sentence) {
        String regex = String.join("|", lexicon.getConjunctions());
        return regex.isEmpty() ? new String[]{sentence} : sentence.split(regex);
    }

    private boolean isRhetorical(String sentence) {
        return (sentence.startsWith("难道") && sentence.endsWith("吗")) || sentence.contains("不成");
    }

    public double calculateRuleConfidence(String sentence) {
        List<MatchResult> matches = match(preprocess(sentence));
        long sentimentWordCount = matches.stream().filter(m -> m.type == WordType.SENTIMENT).count();
        long modifierCount = matches.stream().filter(m -> m.type == WordType.DEGREE || m.type == WordType.NEGATION).count();

        // Simple heuristic: more sentiment words and modifiers increase confidence.
        double confidence = 0.5 + (sentimentWordCount * 0.1) + (modifierCount * 0.05);
        return Math.min(confidence, 1.0); // Cap at 1.0
    }


    private enum WordType { SENTIMENT, DEGREE, NEGATION, CONJUNCTION, UNKNOWN }

    private static class MatchResult {
        final String word; final int index; final WordType type;
        MatchResult(String word, int index, WordType type) { this.word = word; this.index = index; this.type = type; }
    }

    private static class Trie {
        private final TrieNode root = new TrieNode();
        private static class TrieNode { final Map<Character, TrieNode> children = new HashMap<>(); boolean isEndOfWord = false; WordType wordType = WordType.UNKNOWN; }
        public static class SearchResult { final boolean found; final String word; final WordType type; SearchResult(boolean found, String word, WordType type) { this.found = found; this.word = word; this.type = type; } }

        public void insert(String word, WordType type) {
            TrieNode current = root;
            for (char c : word.toCharArray()) { current = current.children.computeIfAbsent(c, k -> new TrieNode()); }
            current.isEndOfWord = true; current.wordType = type;
        }

        public SearchResult searchLongest(String text) {
            TrieNode current = root; int longestMatchLength = 0; WordType longestMatchType = WordType.UNKNOWN;
            for (int i = 0; i < text.length(); i++) {
                TrieNode node = current.children.get(text.charAt(i));
                if (node == null) break;
                current = node;
                if (current.isEndOfWord) { longestMatchLength = i + 1; longestMatchType = current.wordType; }
            }
            return longestMatchLength > 0 ? new SearchResult(true, text.substring(0, longestMatchLength), longestMatchType) : new SearchResult(false, null, WordType.UNKNOWN);
        }
    }
}

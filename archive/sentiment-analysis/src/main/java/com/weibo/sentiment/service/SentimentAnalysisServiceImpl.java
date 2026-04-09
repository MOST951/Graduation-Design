package com.weibo.sentiment.service;

import com.weibo.sentiment.dto.AnalysisConfig;
import com.weibo.sentiment.dto.AnalysisModelType;
import com.weibo.sentiment.dto.SentimentResult;
import com.weibo.sentiment.dto.ServiceStatus;
import com.weibo.sentiment.model.BertModelWrapper;
import com.weibo.sentiment.cache.SentimentCache;
import com.weibo.sentiment.config.AnalysisProperties;
import com.weibo.sentiment.rule.SentimentCalculator;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import javax.annotation.PostConstruct;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Service
@Slf4j
public class SentimentAnalysisServiceImpl implements SentimentAnalysisService {

    @Autowired
    private SentimentCalculator sentimentCalculator;

    // Use 'required = false' to allow the application to start even if the BERT model is not configured.
    @Autowired(required = false)
    private BertModelWrapper bertModelWrapper;

    @Autowired
    private AnalysisProperties analysisProperties;

    @Autowired
    private SentimentCache sentimentCache;

    @PostConstruct
    public void init() {
        log.info("Sentiment analysis service initialized with default strategy: {}", analysisProperties.getDefaultStrategy());
        if (bertModelWrapper != null) {
            log.info("BERT model is available: {}", bertModelWrapper.getModelInfo());
        } else {
            log.warn("BERT model wrapper not found. Only RULE_BASED analysis is available.");
        }
    }

    @Override
    public SentimentResult analyzeText(String text, AnalysisConfig config) {
        // Check cache first
        Optional<SentimentResult> cachedResult = sentimentCache.get(text);
        if (cachedResult.isPresent()) {
            return cachedResult.get();
        }

        if (text == null || text.trim().isEmpty()) {
            return SentimentResult.builder().originalText(text).score(0.0).label("Neutral").confidence(1.0).method("empty-input").build();
        }

        AnalysisModelType modelType = config.getModelType() != null ? config.getModelType() : AnalysisModelType.valueOf(analysisProperties.getDefaultStrategy().toUpperCase());

        SentimentResult result;
        switch (modelType) {
            case RULE_BASED:
                result = analyzeWithRules(text);
                break;
            case BERT_MODEL:
                if (bertModelWrapper == null || !bertModelWrapper.isModelLoaded()) {
                    log.warn("BERT model requested but not available. Falling back to rule-based analysis.");
                    result = analyzeWithRules(text);
                } else {
                    result = analyzeWithBert(text);
                }
                break;
            default:
                result = hybridAnalyzeInternal(text);
                break;
        }

        // Put the result into the cache before returning
        sentimentCache.put(text, result);
        return result;
    }

    @Override
    public List<SentimentResult> analyzeBatch(List<String> texts, AnalysisConfig config) {
        if (texts == null || texts.isEmpty()) {
            return Collections.emptyList();
        }
        return texts.parallelStream()
                .map(text -> analyzeText(text, config))
                .collect(Collectors.toList());
    }

    @Override
    public SentimentResult hybridAnalyze(String text) {
        return hybridAnalyzeInternal(text);
    }

    private SentimentResult hybridAnalyzeInternal(String text) {
        // Step 1: Use rule-based method for baseline sentiment
        double ruleScore = sentimentCalculator.calculateScore(text);
        double ruleConfidence = sentimentCalculator.calculateRuleConfidence(text);

        // Step 2: Decide if BERT model should be used
        boolean useBert = shouldUseBert(text, ruleConfidence);

        if (useBert && bertModelWrapper != null && bertModelWrapper.isModelLoaded()) {
            log.debug("Rule confidence is low or text is complex, engaging BERT model.");
            BertModelWrapper.BertPrediction bertPrediction = bertModelWrapper.predict(text);

            // Step 3: Weighted fusion of results
            return combineResults(text, ruleScore, ruleConfidence, bertPrediction.getScore(), bertPrediction.getConfidence());
        }

        // Step 4: Use only the rule-based result
        log.debug("Using rule-based result exclusively.");
        return SentimentResult.builder()
                .originalText(text)
                .score(ruleScore)
                .label(SentimentResult.scoreToLabel(ruleScore))
                .confidence(ruleConfidence)
                .method("rule-based")
                .build();
    }

    private boolean shouldUseBert(String text, double ruleConfidence) {
        // Use BERT if rule confidence is below a threshold or if the text is long/complex.
        return ruleConfidence < analysisProperties.getConfidenceThreshold() || text.length() > analysisProperties.getBertMinLength();
    }

    private SentimentResult combineResults(String text, double ruleScore, double ruleConfidence, double bertScore, double bertConfidence) {
        // Weighted average based on the confidence of each model
        double totalConfidence = ruleConfidence + bertConfidence;
        double combinedScore = ((ruleScore * ruleConfidence) + (bertScore * bertConfidence)) / totalConfidence;

        return SentimentResult.builder()
                .originalText(text)
                .score(combinedScore)
                .label(SentimentResult.scoreToLabel(combinedScore))
                .confidence((ruleConfidence + bertConfidence) / 2.0) // Average confidence
                .method("hybrid")
                .build();
    }

    @Override
    public ServiceStatus getServiceStatus() {
        boolean bertOk = bertModelWrapper != null && bertModelWrapper.isModelLoaded();
        boolean rulesOk = sentimentCalculator != null;
        boolean isHealthy = rulesOk; // Service is healthy if at least rules are OK

        String message = isHealthy ? "Service is operational" : "Service is fully degraded";
        if (isHealthy && !bertOk) {
            message = "Service is operational in degraded mode (BERT model unavailable)";
        }

        Map<String, Object> modelStatuses = Map.of(
                "ruleBasedEngine", rulesOk ? "OK" : "Error",
                "bertModelEngine", bertOk ? "OK" : "Unavailable"
        );
        return new ServiceStatus(isHealthy, message, modelStatuses);
    }

    // --- Private Helper Methods ---

    private SentimentResult analyzeWithRules(String text) {
        double score = sentimentCalculator.calculateScore(text);
        double confidence = sentimentCalculator.calculateRuleConfidence(text);
        return SentimentResult.builder()
                .originalText(text)
                .score(score)
                .label(SentimentResult.scoreToLabel(score))
                .confidence(confidence)
                .method("rule-based")
                .build();
    }

    private SentimentResult analyzeWithBert(String text) {
        BertModelWrapper.BertPrediction prediction = bertModelWrapper.predict(text);
        return SentimentResult.builder()
                .originalText(text)
                .score(prediction.getScore())
                .label(SentimentResult.scoreToLabel(prediction.getScore()))
                .confidence(prediction.getConfidence())
                .method("bert")
                .build();
    }
}

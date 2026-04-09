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
import java.util.Optional;
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
        // 级联策略（Cascade Strategy）：
        // 先用词典快速分析，置信度高则直接返回；否则调用BERT精确分析
        // 公式4-3: S_final = S_dict if |S_dict| > θ, else S_bert

        // Step 1: 词典快速分析
        double ruleScore = sentimentCalculator.calculateScore(text);
        double ruleConfidence = sentimentCalculator.calculateRuleConfidence(text);

        // Step 2: 级联决策 —— 词典置信度高于阈值θ，直接采用词典结果
        double confidenceThreshold = analysisProperties.getConfidenceThreshold();
        if (Math.abs(ruleScore) > confidenceThreshold || ruleConfidence > confidenceThreshold) {
            log.debug("Cascade: lexicon confidence sufficient (score={}, confidence={}), skipping BERT.", ruleScore, ruleConfidence);
            return SentimentResult.builder()
                    .originalText(text)
                    .score(ruleScore)
                    .label(SentimentResult.scoreToLabel(ruleScore))
                    .confidence(ruleConfidence)
                    .method("cascade-lexicon")
                    .build();
        }

        // Step 3: 词典置信度低，调用BERT精确分析
        if (bertModelWrapper != null && bertModelWrapper.isModelLoaded()) {
            log.debug("Cascade: lexicon confidence low (score={}, confidence={}), engaging BERT.", ruleScore, ruleConfidence);
            BertModelWrapper.BertPrediction bertPrediction = bertModelWrapper.predict(text);
            return SentimentResult.builder()
                    .originalText(text)
                    .score(bertPrediction.getScore())
                    .label(SentimentResult.scoreToLabel(bertPrediction.getScore()))
                    .confidence(bertPrediction.getConfidence())
                    .method("cascade-bert")
                    .build();
        }

        // Step 4: BERT不可用，回退使用词典结果
        log.debug("Cascade: BERT unavailable, using lexicon result as fallback.");
        return SentimentResult.builder()
                .originalText(text)
                .score(ruleScore)
                .label(SentimentResult.scoreToLabel(ruleScore))
                .confidence(ruleConfidence)
                .method("cascade-lexicon-fallback")
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

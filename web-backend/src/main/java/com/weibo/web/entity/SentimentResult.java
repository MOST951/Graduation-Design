package com.weibo.web.entity;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.CreationTimestamp;

import javax.persistence.*;
import java.time.LocalDateTime;

/**
 * Sentiment Analysis Result Entity
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
@Entity
@Table(name = "sentiment_result")
public class SentimentResult {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "task_id")
    private CollectionTask task;

    @Column(name = "weibo_id", nullable = false, unique = true, length = 50)
    private String weiboId;

    @Lob
    private String content;

    @Column(length = 20)
    private String sentiment; // e.g., POSITIVE, NEGATIVE, NEUTRAL

    private Double confidence;

    @Column(name = "publish_time")
    private LocalDateTime publishTime;

    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;
}

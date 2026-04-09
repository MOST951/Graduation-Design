package com.weibo.collector.storage;

import com.weibo.common.config.KafkaConfig;
import lombok.extern.slf4j.Slf4j;
import org.apache.kafka.clients.producer.KafkaProducer;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.common.Metric;
import org.apache.kafka.common.MetricName;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import javax.annotation.PostConstruct;
import java.util.List;
import java.util.Map;
import java.util.Properties;

/**
 * Produces and sends messages to a Kafka topic.
 * <p>
 * This class is a wrapper around the KafkaProducer, providing a simple method
 * to send data to a specified Kafka topic for real-time processing.
 * </p>
 */
@Slf4j
@Component
public class KafkaDataProducer {

    @Autowired
    private KafkaConfig kafkaConfig;

    private KafkaProducer<String, String> producer;

    /**
     * Initializes the Kafka producer.
     */
    @PostConstruct
    public void init() {
        Properties props = new Properties();
        props.put("bootstrap.servers", kafkaConfig.getBootstrapServers());
        props.put("key.serializer", "org.apache.kafka.common.serialization.StringSerializer");
        props.put("value.serializer", "org.apache.kafka.common.serialization.StringSerializer");
        producer = new KafkaProducer<>(props);
        log.info("KafkaProducer initialized successfully.");
    }

    /**
     * Sends a message to the specified Kafka topic.
     *
     * @param topic   The Kafka topic to send the message to.
     * @param message The message to send.
     */
    public void sendMessage(String topic, String message) {
        try {
            producer.send(new ProducerRecord<>(topic, message), (metadata, exception) -> {
                if (exception != null) {
                    log.error("Failed to send message to Kafka", exception);
                }
            });
        } catch (Exception e) {
            log.error("Failed to send message to Kafka topic: {}", topic, e);
        }
    }

    public void sendBatch(String topic, List<String> messages) {
        for (String message : messages) {
            sendMessage(topic, message);
        }
    }

    public Map<MetricName, ? extends Metric> getMetrics() {
        return producer.metrics();
    }
}

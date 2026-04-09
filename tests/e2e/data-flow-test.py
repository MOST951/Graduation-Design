import pytest
import requests
import time
from kafka import KafkaProducer, KafkaConsumer
import json

# --- Pytest Fixtures ---

@pytest.fixture(scope="module")
def kafka_producer():
    """Creates a Kafka producer for the test module."""
    try:
        producer = KafkaProducer(
            bootstrap_servers=['localhost:9092'],
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            retries=5, # Add retries for robustness
            request_timeout_ms=30000
        )
        yield producer
        producer.close()
    except Exception as e:
        pytest.fail(f"Failed to create Kafka producer: {e}")

@pytest.fixture(scope="module")
def kafka_consumer():
    """Creates a Kafka consumer for the sentiment results topic."""
    try:
        consumer = KafkaConsumer(
            'sentiment-results',
            bootstrap_servers=['localhost:9092'],
            value_deserializer=lambda v: json.loads(v.decode('utf-8')),
            auto_offset_reset='earliest',
            consumer_timeout_ms=15000 # Timeout to prevent test from hanging
        )
        yield consumer
        consumer.close()
    except Exception as e:
        pytest.fail(f"Failed to create Kafka consumer: {e}")

# --- Test Class ---

class TestDataFlow:
    """Tests the complete data flow from raw data ingestion to sentiment analysis results."""

    def test_complete_data_flow(self, kafka_producer, kafka_consumer):
        """
        Tests the full data pipeline:
        1. Sends a raw Weibo post to the 'raw-weibo-data' Kafka topic.
        2. Waits for the Spark Streaming job to process the data.
        3. Consumes the result from the 'sentiment-results' topic.
        4. Validates the sentiment score and metadata.
        """
        # 1. Prepare test data
        test_data = {
            "weibo_id": f"test_id_{int(time.time())}",
            "content": "这个新发布的手机真是太棒了，相机功能无与伦比，强烈推荐！",
            "user_id": "test_user_positive",
            "created_at": int(time.time())
        }

        # 2. Send to the raw data topic
        try:
            future = kafka_producer.send('raw-weibo-data', test_data)
            future.get(timeout=10) # Block until sent
            kafka_producer.flush()
            print(f"Sent test data to Kafka: {test_data}")
        except Exception as e:
            pytest.fail(f"Failed to send message to Kafka: {e}")

        # 3. Consume from the results topic and validate
        found_message = False
        for message in kafka_consumer:
            result = message.value
            print(f"Received result from Kafka: {result}")
            if result.get('weibo_id') == test_data['weibo_id']:
                # 4. Assertions
                assert 'sentiment_score' in result
                assert 'sentiment_label' in result
                assert result['sentiment_label'] == 'Positive' # Expecting a positive result
                assert result['sentiment_score'] > 0.5 # Expecting a high positive score
                found_message = True
                break
        
        assert found_message, f"Did not receive a result for weibo_id {test_data['weibo_id']} within the timeout period."

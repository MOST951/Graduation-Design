import pytest
import requests
from kafka import KafkaAdminClient
import redis

# --- Service Endpoints ---
SERVICES = {
    "web-backend": "http://localhost:8080/api/actuator/health",
    "spark-master-ui": "http://localhost:8081", # Default Spark Master UI port
    "model-service": "http://localhost:8000/health", # Assuming a health endpoint for the Python service
}

# --- Test Class ---

class TestDeploymentHealth:
    """Validates that all services in the deployment are up and running."""

    @pytest.mark.parametrize("service_name, url", SERVICES.items())
    def test_http_service_is_accessible(self, service_name, url):
        """Tests that a given HTTP service is accessible and returns a 200 OK status."""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            print(f"Successfully connected to {service_name} at {url}")
        except requests.exceptions.RequestException as e:
            pytest.fail(f"Failed to connect to {service_name} at {url}. Error: {e}")

    def test_kafka_broker_is_running(self):
        """Tests connectivity to the Kafka broker."""
        try:
            admin_client = KafkaAdminClient(
                bootstrap_servers='localhost:9092',
                client_id='test-deployment-checker',
                request_timeout_ms=5000
            )
            topics = admin_client.list_topics()
            assert 'raw-weibo-data' in topics
            assert 'sentiment-results' in topics
            print("Successfully connected to Kafka and found required topics.")
        except Exception as e:
            pytest.fail(f"Failed to connect to Kafka broker. Is it running? Error: {e}")

    def test_redis_is_running(self):
        """Tests connectivity to the Redis server."""
        try:
            r = redis.Redis(host='localhost', port=6379, db=0, socket_connect_timeout=5)
            assert r.ping()
            print("Successfully connected to Redis.")
        except redis.exceptions.ConnectionError as e:
            pytest.fail(f"Failed to connect to Redis. Is it running? Error: {e}")

    # You could also add a test for the database connection here
    # import mysql.connector
    # def test_mysql_is_running(self):
    #     try:
    #         conn = mysql.connector.connect(user='user', password='password', host='localhost', database='db')
    #         assert conn.is_connected()
    #         conn.close()
    #         print("Successfully connected to MySQL.")
    #     except mysql.connector.Error as e:
    #         pytest.fail(f"Failed to connect to MySQL. Is it running? Error: {e}")

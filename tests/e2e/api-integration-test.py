import pytest
import requests

# --- Test Configuration ---
BASE_URL = "http://localhost:8080/api"

# --- Test Fixtures ---

@pytest.fixture(scope="module")
def auth_token():
    """Authenticates and retrieves a JWT token for testing protected endpoints."""
    try:
        # In a real test suite, you'd fetch this from a login endpoint
        # response = requests.post(f"{BASE_URL}/auth/login", json={"username": "testuser", "password": "testpass"})
        # response.raise_for_status()
        # return response.json()['token']
        
        # For now, we use a placeholder token. The backend must be configured to accept it in a test environment.
        return "dummy-jwt-token-for-testing"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Authentication failed: {e}")

# --- Test Class ---

class TestApiIntegration:
    """Tests the integration of various API endpoints like tasks and system configs."""

    def test_health_check(self):
        """Tests the actuator health check endpoint."""
        try:
            response = requests.get(f"{BASE_URL}/actuator/health")
            response.raise_for_status()
            assert response.json()['status'] == 'UP'
        except requests.exceptions.RequestException as e:
            pytest.fail(f"Health check failed: {e}")

    def test_create_and_get_collection_task(self, auth_token):
        """
        Tests the full lifecycle of a data collection task: create, get, and list.
        """
        headers = {"Authorization": f"Bearer {auth_token}"}
        task_payload = {
            "name": "E2E Test Task",
            "type": "KEYWORD",
            "keywords": "#pytest,#integrationtest",
            "dataSource": "Weibo"
        }

        try:
            # 1. Create a new task
            create_response = requests.post(f"{BASE_URL}/tasks", json=task_payload, headers=headers)
            create_response.raise_for_status()
            created_task = create_response.json()
            task_id = created_task['id']

            assert task_id is not None
            assert created_task['name'] == "E2E Test Task"

            # 2. Get the specific task by ID
            get_response = requests.get(f"{BASE_URL}/tasks/{task_id}", headers=headers)
            get_response.raise_for_status()
            retrieved_task = get_response.json()
            assert retrieved_task['id'] == task_id

            # 3. List tasks and ensure the new task is present
            list_response = requests.get(f"{BASE_URL}/tasks", headers=headers)
            list_response.raise_for_status()
            all_tasks = list_response.json()
            assert any(task['id'] == task_id for task in all_tasks)

        except requests.exceptions.RequestException as e:
            pytest.fail(f"Task API integration test failed: {e}")

    def test_get_system_config(self, auth_token):
        """
        Tests retrieving system configuration.
        """
        headers = {"Authorization": f"Bearer {auth_token}"}
        try:
            response = requests.get(f"{BASE_URL}/config", headers=headers)
            response.raise_for_status()
            configs = response.json()
            # Check if a default key exists
            assert any(config['config_key'] == 'site.name' for config in configs)
        except requests.exceptions.RequestException as e:
            pytest.fail(f"System config API test failed: {e}")

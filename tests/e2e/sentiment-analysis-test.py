import pytest
import requests

# --- Test Configuration ---
BASE_URL = "http://localhost:8080/api/sentiment"

# --- Test Class ---

class TestSentimentAnalysis:
    """Tests the sentiment analysis endpoint with various inputs."""

    @pytest.mark.parametrize("text, expected_label, expected_score_range", [
        ("这款产品真是太棒了，我非常喜欢！", "Positive", (0.5, 1.0)),
        ("服务太差了，等了很久，非常失望。", "Negative", (-1.0, -0.5)),
        ("今天天气还行，不冷不热。", "Neutral", (-0.3, 0.3)),
        ("虽然外观有点普通，但功能确实强大。", "Positive", (0.1, 0.7)), # Complex sentence
    ])
    def test_single_text_analysis(self, text, expected_label, expected_score_range):
        """
        Tests the analysis of a single text string.
        """
        try:
            response = requests.post(f"{BASE_URL}/analyze", json={"text": text, "model": "hybrid"})
            response.raise_for_status() # Fail test if status code is not 2xx
            
            result = response.json()
            
            assert result['label'] == expected_label
            assert expected_score_range[0] <= result['score'] <= expected_score_range[1]
            assert result['originalText'] == text

        except requests.exceptions.RequestException as e:
            pytest.fail(f"API request failed: {e}")

    def test_batch_analysis(self):
        """
        Tests the batch analysis endpoint.
        """
        texts = [
            "阳光明媚，心情舒畅。",
            "这个更新导致了好多bug，没法用了。",
            "会议内容很常规。"
        ]
        
        try:
            response = requests.post(f"{BASE_URL}/analyze-batch", json={"texts": texts, "model": "hybrid"})
            response.raise_for_status()
            
            results = response.json()
            
            assert len(results) == 3
            assert results[0]['label'] == 'Positive'
            assert results[1]['label'] == 'Negative'
            assert results[2]['label'] == 'Neutral'

        except requests.exceptions.RequestException as e:
            pytest.fail(f"API request failed: {e}")

    def test_invalid_input(self):
        """
        Tests the API's behavior with invalid or empty input.
        """
        # Test with empty text
        response = requests.post(f"{BASE_URL}/analyze", json={"text": ""})
        assert response.status_code == 200 # Or 400, depending on implementation
        assert response.json()['label'] == 'Neutral'

        # Test with no text field
        response = requests.post(f"{BASE_URL}/analyze", json={})
        assert response.status_code == 400 # Expecting Bad Request

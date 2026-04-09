import pytest
import torch
from src.model.model_factory import ModelFactory

@pytest.fixture
def bert_config():
    return {
        'model_type': 'bert',
        'model_name': 'bert-base-uncased', # Use a smaller model for testing
        'num_labels': 2
    }

def test_bert_model_creation(bert_config):
    model = ModelFactory.create_model(bert_config)
    assert model is not None
    # Test forward pass
    dummy_input = {
        'input_ids': torch.randint(0, 1000, (2, 128)),
        'attention_mask': torch.ones(2, 128)
    }
    outputs = model(**dummy_input)
    assert outputs['logits'].shape == (2, 2)

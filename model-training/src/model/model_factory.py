from transformers import AutoConfig
from .bert_model import BertForSentiment
from .lstm_model import BiLSTMAttention
from typing import Any, Dict

class ModelFactory:
    """Factory to create models based on configuration."""

    @staticmethod
    def create_model(config: Dict[str, Any]) -> Any:
        model_type = config.get('model_type', 'bert')

        if model_type == 'bert':
            model_config = AutoConfig.from_pretrained(
                config['model_name'],
                num_labels=config['num_labels'],
            )
            return BertForSentiment.from_pretrained(config['model_name'], config=model_config)
        
        elif model_type == 'lstm':
            return BiLSTMAttention(
                vocab_size=config['vocab_size'],
                embedding_dim=config['embedding_dim'],
                hidden_dim=config['hidden_dim'],
                n_layers=config['n_layers'],
                dropout=config['dropout'],
                num_labels=config['num_labels'],
                pretrained_embeddings=config.get('pretrained_embeddings')
            )
            
        else:
            raise ValueError(f"Unsupported model type: {model_type}")

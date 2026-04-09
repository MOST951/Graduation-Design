import torch
import torch.nn as nn
from typing import List

class ModelEnsemble(nn.Module):
    """Ensemble of multiple models for improved performance."""

    def __init__(self, models: List[nn.Module], weights: List[float] = None):
        super().__init__()
        self.models = nn.ModuleList(models)
        self.weights = weights if weights else [1.0 / len(models)] * len(models)

    def forward(self, *args, **kwargs):
        """Average the predictions of the models."""
        outputs = [model(*args, **kwargs)['logits'] for model in self.models]
        weighted_outputs = [output * weight for output, weight in zip(outputs, self.weights)]
        return torch.stack(weighted_outputs).mean(dim=0)

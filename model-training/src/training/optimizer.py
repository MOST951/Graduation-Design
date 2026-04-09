from torch.optim import AdamW
from transformers import get_linear_schedule_with_warmup
from typing import Dict, Any, Tuple

class OptimizerBuilder:
    """Builds an optimizer and a learning rate scheduler."""

    @staticmethod
    def build(model, config: Dict[str, Any], num_training_steps: int) -> Tuple[Any, Any]:
        optimizer_type = config.get('optimizer', 'adamw')
        lr = config.get('learning_rate', 2e-5)
        warmup_steps = config.get('warmup_steps', 0)

        if optimizer_type == 'adamw':
            optimizer = AdamW(model.parameters(), lr=lr)
        else:
            raise ValueError(f"Unsupported optimizer: {optimizer_type}")

        scheduler = get_linear_schedule_with_warmup(
            optimizer,
            num_warmup_steps=warmup_steps,
            num_training_steps=num_training_steps
        )

        return optimizer, scheduler

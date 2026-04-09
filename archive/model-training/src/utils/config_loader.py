import yaml
import json
from typing import Dict, Any

def load_config(config_path: str) -> Dict[str, Any]:
    """Load configuration from a YAML or JSON file."""
    with open(config_path, 'r') as f:
        if config_path.endswith('.yaml') or config_path.endswith('.yml'):
            return yaml.safe_load(f)
        elif config_path.endswith('.json'):
            return json.load(f)
        else:
            raise ValueError(f"Unsupported config format for {config_path}")

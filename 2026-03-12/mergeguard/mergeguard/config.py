import yaml
from pathlib import Path
import os

DEFAULT_CONFIG = {
    "min_authenticity_score": 70,
    "fail_on_block": True,
    "llm_model": "gpt-4o",
    "ignore_paths": []
}

def load_config() -> dict:
    config_path = Path(".mergeguard.yml")
    if not config_path.exists():
        return DEFAULT_CONFIG
    
    with open(config_path, "r") as f:
        user_config = yaml.safe_load(f) or {}
    
    return {**DEFAULT_CONFIG, **user_config}

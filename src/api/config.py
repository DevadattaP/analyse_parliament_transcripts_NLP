import yaml
import os
from typing import Dict, Any
from pathlib import Path

class Config:
    """Configuration manager for the API"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        config_path = Path(self.config_path)
        
        if not config_path.exists():
            # Try to find config in parent directories
            config_path = Path(__file__).parent.parent.parent / "config.yaml"
            
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        else:
            # Return default configuration
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Return default configuration if config file not found"""
        return {
            "api": {
                "host": "0.0.0.0",
                "port": 8000,
                "debug": True,
                "reload": True,
                "workers": 1,
                "cors_origins": ["http://localhost:8000", "http://127.0.0.1:8000"]
            },
        }
    
    def get(self, key: str, default=None) -> Any:
        """Get configuration value using dot notation"""
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

# Global configuration instance
config = Config()
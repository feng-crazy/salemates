"""Configuration module for vikingbot."""

from salemates.config.loader import load_config, get_config_path
from salemates.config.schema import Config

__all__ = ["Config", "load_config", "get_config_path"]

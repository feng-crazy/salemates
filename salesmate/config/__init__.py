"""Configuration module for vikingbot."""

from salesmate.config.loader import load_config, get_config_path
from salesmate.config.schema import Config

__all__ = ["Config", "load_config", "get_config_path"]

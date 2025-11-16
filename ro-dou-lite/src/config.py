"""Configuration management for Ro-DOU Lite.

This module handles loading and validating YAML configuration files
with sensible defaults for Raspberry Pi deployment.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml


class ConfigError(Exception):
    """Raised when configuration is invalid."""
    pass


class Config:
    """Configuration manager for Ro-DOU Lite.

    Loads configuration from YAML file and provides validated access
    to settings with sensible defaults.

    Example:
        >>> config = Config.from_file("config.yaml")
        >>> config.get_inlabs_credentials()
        ('user@example.com', 'password')
    """

    def __init__(self, config_dict: Dict[str, Any]):
        """Initialize configuration from dictionary.

        Args:
            config_dict: Configuration dictionary loaded from YAML

        Raises:
            ConfigError: If required fields are missing
        """
        self._config = config_dict
        self._validate()

    @classmethod
    def from_file(cls, filepath: str) -> "Config":
        """Load configuration from YAML file.

        Args:
            filepath: Path to YAML configuration file

        Returns:
            Config instance

        Raises:
            ConfigError: If file doesn't exist or is invalid YAML
        """
        path = Path(filepath)
        if not path.exists():
            raise ConfigError(f"Configuration file not found: {filepath}")

        try:
            with open(path, 'r', encoding='utf-8') as f:
                config_dict = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ConfigError(f"Invalid YAML in configuration file: {e}")

        if not isinstance(config_dict, dict):
            raise ConfigError("Configuration file must contain a YAML dictionary")

        return cls(config_dict)

    def _validate(self) -> None:
        """Validate that required configuration sections exist.

        Raises:
            ConfigError: If required sections are missing
        """
        required_sections = ['inlabs', 'database', 'searches']
        for section in required_sections:
            if section not in self._config:
                raise ConfigError(f"Missing required configuration section: {section}")

        # Validate INLABS credentials
        inlabs = self._config['inlabs']
        if 'username' not in inlabs or 'password' not in inlabs:
            raise ConfigError("INLABS configuration must include username and password")

        # Validate database path
        if 'path' not in self._config['database']:
            raise ConfigError("Database configuration must include path")

        # Validate searches
        searches = self._config['searches']
        if not isinstance(searches, list) or len(searches) == 0:
            raise ConfigError("Searches must be a non-empty list")

        for i, search in enumerate(searches):
            if 'terms' not in search or not search['terms']:
                raise ConfigError(f"Search {i} must include non-empty terms list")

    def get_inlabs_credentials(self) -> tuple[str, str]:
        """Get INLABS portal credentials.

        Returns:
            Tuple of (username, password)
        """
        inlabs = self._config['inlabs']
        return inlabs['username'], inlabs['password']

    def get_inlabs_download_path(self) -> Path:
        """Get path for INLABS downloads.

        Returns:
            Path object for download directory
        """
        default_path = Path.home() / "ro-dou" / "data" / "downloads"
        path_str = self._config['inlabs'].get('download_path', str(default_path))
        return Path(path_str)

    def get_database_path(self) -> Path:
        """Get SQLite database file path.

        Returns:
            Path object for database file
        """
        return Path(self._config['database']['path'])

    def get_retention_days(self) -> int:
        """Get number of days to retain data in database.

        Returns:
            Number of days (default: 365)
        """
        return self._config['database'].get('retention_days', 365)

    def get_searches(self) -> List[Dict[str, Any]]:
        """Get list of search configurations.

        Returns:
            List of search configuration dictionaries
        """
        return self._config['searches']

    def get_notification_config(self) -> Optional[Dict[str, Any]]:
        """Get notification configuration (email).

        Returns:
            Notification config dict or None if not configured
        """
        return self._config.get('notifications')

    def get_email_config(self) -> Optional[Dict[str, Any]]:
        """Get email notification configuration.

        Returns:
            Email config dict or None if not configured
        """
        notifications = self.get_notification_config()
        if notifications:
            return notifications.get('email')
        return None

    def is_email_enabled(self) -> bool:
        """Check if email notifications are enabled.

        Returns:
            True if email is configured
        """
        email_config = self.get_email_config()
        if not email_config:
            return False

        required = ['smtp_host', 'smtp_port', 'from', 'to']
        return all(key in email_config for key in required)

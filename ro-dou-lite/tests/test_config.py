"""Tests for configuration management."""

import pytest
import tempfile
from pathlib import Path
import yaml

from src.config import Config, ConfigError


@pytest.fixture
def valid_config_dict():
    """Return a valid configuration dictionary."""
    return {
        'inlabs': {
            'username': 'test@example.com',
            'password': 'testpass123',
            'download_path': '/tmp/downloads'
        },
        'database': {
            'path': '/tmp/test.db',
            'retention_days': 180
        },
        'searches': [
            {
                'terms': ['LGPD', 'dados abertos'],
                'sections': ['DO1', 'DO2'],
                'departments': ['Ministério da Gestão']
            }
        ],
        'notifications': {
            'email': {
                'smtp_host': 'smtp.gmail.com',
                'smtp_port': 587,
                'from': 'alerts@example.com',
                'to': ['user@example.com'],
                'password': 'app_password'
            }
        }
    }


@pytest.fixture
def valid_config_file(valid_config_dict):
    """Create a temporary valid config file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(valid_config_dict, f)
        temp_path = f.name
    yield temp_path
    Path(temp_path).unlink()


class TestConfig:
    """Test Config class."""

    def test_from_file_success(self, valid_config_file):
        """Test loading configuration from valid file."""
        config = Config.from_file(valid_config_file)
        assert config is not None
        assert config.get_inlabs_credentials() == ('test@example.com', 'testpass123')

    def test_from_file_not_found(self):
        """Test loading from non-existent file raises error."""
        with pytest.raises(ConfigError, match="Configuration file not found"):
            Config.from_file('/nonexistent/config.yaml')

    def test_from_file_invalid_yaml(self):
        """Test loading invalid YAML raises error."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")
            temp_path = f.name

        try:
            with pytest.raises(ConfigError, match="Invalid YAML"):
                Config.from_file(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_from_file_non_dict(self):
        """Test loading non-dict YAML raises error."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(['list', 'not', 'dict'], f)
            temp_path = f.name

        try:
            with pytest.raises(ConfigError, match="must contain a YAML dictionary"):
                Config.from_file(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_validate_missing_inlabs(self, valid_config_dict):
        """Test validation fails when INLABS section is missing."""
        del valid_config_dict['inlabs']
        with pytest.raises(ConfigError, match="Missing required configuration section: inlabs"):
            Config(valid_config_dict)

    def test_validate_missing_database(self, valid_config_dict):
        """Test validation fails when database section is missing."""
        del valid_config_dict['database']
        with pytest.raises(ConfigError, match="Missing required configuration section: database"):
            Config(valid_config_dict)

    def test_validate_missing_searches(self, valid_config_dict):
        """Test validation fails when searches section is missing."""
        del valid_config_dict['searches']
        with pytest.raises(ConfigError, match="Missing required configuration section: searches"):
            Config(valid_config_dict)

    def test_validate_missing_inlabs_username(self, valid_config_dict):
        """Test validation fails when INLABS username is missing."""
        del valid_config_dict['inlabs']['username']
        with pytest.raises(ConfigError, match="INLABS configuration must include username and password"):
            Config(valid_config_dict)

    def test_validate_missing_database_path(self, valid_config_dict):
        """Test validation fails when database path is missing."""
        del valid_config_dict['database']['path']
        with pytest.raises(ConfigError, match="Database configuration must include path"):
            Config(valid_config_dict)

    def test_validate_empty_searches(self, valid_config_dict):
        """Test validation fails when searches list is empty."""
        valid_config_dict['searches'] = []
        with pytest.raises(ConfigError, match="Searches must be a non-empty list"):
            Config(valid_config_dict)

    def test_validate_search_without_terms(self, valid_config_dict):
        """Test validation fails when search has no terms."""
        valid_config_dict['searches'][0] = {'sections': ['DO1']}
        with pytest.raises(ConfigError, match="Search 0 must include non-empty terms list"):
            Config(valid_config_dict)

    def test_get_inlabs_credentials(self, valid_config_dict):
        """Test getting INLABS credentials."""
        config = Config(valid_config_dict)
        username, password = config.get_inlabs_credentials()
        assert username == 'test@example.com'
        assert password == 'testpass123'

    def test_get_inlabs_download_path(self, valid_config_dict):
        """Test getting INLABS download path."""
        config = Config(valid_config_dict)
        path = config.get_inlabs_download_path()
        assert path == Path('/tmp/downloads')

    def test_get_inlabs_download_path_default(self, valid_config_dict):
        """Test getting default INLABS download path."""
        del valid_config_dict['inlabs']['download_path']
        config = Config(valid_config_dict)
        path = config.get_inlabs_download_path()
        assert 'ro-dou' in str(path)
        assert 'downloads' in str(path)

    def test_get_database_path(self, valid_config_dict):
        """Test getting database path."""
        config = Config(valid_config_dict)
        path = config.get_database_path()
        assert path == Path('/tmp/test.db')

    def test_get_retention_days(self, valid_config_dict):
        """Test getting retention days."""
        config = Config(valid_config_dict)
        assert config.get_retention_days() == 180

    def test_get_retention_days_default(self, valid_config_dict):
        """Test getting default retention days."""
        del valid_config_dict['database']['retention_days']
        config = Config(valid_config_dict)
        assert config.get_retention_days() == 365

    def test_get_searches(self, valid_config_dict):
        """Test getting searches configuration."""
        config = Config(valid_config_dict)
        searches = config.get_searches()
        assert len(searches) == 1
        assert searches[0]['terms'] == ['LGPD', 'dados abertos']

    def test_get_notification_config(self, valid_config_dict):
        """Test getting notification configuration."""
        config = Config(valid_config_dict)
        notif_config = config.get_notification_config()
        assert notif_config is not None
        assert 'email' in notif_config

    def test_get_notification_config_missing(self, valid_config_dict):
        """Test getting notification config when not configured."""
        del valid_config_dict['notifications']
        config = Config(valid_config_dict)
        assert config.get_notification_config() is None

    def test_get_email_config(self, valid_config_dict):
        """Test getting email configuration."""
        config = Config(valid_config_dict)
        email_config = config.get_email_config()
        assert email_config is not None
        assert email_config['smtp_host'] == 'smtp.gmail.com'
        assert email_config['smtp_port'] == 587

    def test_get_email_config_missing(self, valid_config_dict):
        """Test getting email config when not configured."""
        del valid_config_dict['notifications']
        config = Config(valid_config_dict)
        assert config.get_email_config() is None

    def test_is_email_enabled_true(self, valid_config_dict):
        """Test email enabled check when properly configured."""
        config = Config(valid_config_dict)
        assert config.is_email_enabled() is True

    def test_is_email_enabled_false_missing_config(self, valid_config_dict):
        """Test email enabled check when not configured."""
        del valid_config_dict['notifications']
        config = Config(valid_config_dict)
        assert config.is_email_enabled() is False

    def test_is_email_enabled_false_incomplete(self, valid_config_dict):
        """Test email enabled check when config is incomplete."""
        del valid_config_dict['notifications']['email']['smtp_host']
        config = Config(valid_config_dict)
        assert config.is_email_enabled() is False

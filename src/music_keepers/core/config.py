"""Configuration management for Music Keepers."""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from dotenv import load_dotenv


class Config:
    """Configuration manager for Music Keepers."""

    DEFAULT_CONFIG_PATH = Path.home() / ".config" / "music-keepers" / "config.yml"
    DEFAULT_DATA_PATH = Path.home() / ".local" / "share" / "music-keepers"

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize configuration.

        Args:
            config_path: Path to configuration file. Uses default if not provided.
        """
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self.config_data: Dict[str, Any] = {}
        load_dotenv()
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from file or create default."""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                self.config_data = yaml.safe_load(f) or {}
        else:
            self._create_default_config()

    def _create_default_config(self) -> None:
        """Create default configuration file."""
        self.config_data = {
            'library': {
                'path': str(Path.home() / "Music"),
                'watch': False,
                'supported_formats': ['.mp3', '.flac', '.m4a', '.ogg', '.wav', '.aac']
            },
            'database': {
                'path': str(self.DEFAULT_DATA_PATH / "library.db")
            },
            'integrations': {
                'spotify': {
                    'client_id': os.getenv('SPOTIFY_CLIENT_ID', ''),
                    'client_secret': os.getenv('SPOTIFY_CLIENT_SECRET', '')
                },
                'lastfm': {
                    'api_key': os.getenv('LASTFM_API_KEY', ''),
                    'api_secret': os.getenv('LASTFM_API_SECRET', '')
                },
                'musicbrainz': {
                    'enabled': True,
                    'user_agent': 'MusicKeepers/0.1.0'
                }
            },
            'cleaning': {
                'duplicate_threshold': 0.95,
                'auto_delete': False,
                'backup_before_delete': True
            },
            'organization': {
                'default_pattern': '{artist}/{album}/{track:02d} - {title}',
                'handle_compilations': True,
                'compilation_pattern': 'Compilations/{album}/{track:02d} - {artist} - {title}'
            }
        }
        self.save()

    def save(self) -> None:
        """Save configuration to file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w') as f:
            yaml.dump(self.config_data, f, default_flow_style=False)

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot-separated key.

        Args:
            key: Dot-separated key (e.g., 'library.path')
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        value = self.config_data
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default

    def set(self, key: str, value: Any) -> None:
        """Set configuration value by dot-separated key.

        Args:
            key: Dot-separated key (e.g., 'library.path')
            value: Value to set
        """
        keys = key.split('.')
        config = self.config_data
        for k in keys[:-1]:
            config = config.setdefault(k, {})
        config[keys[-1]] = value
        self.save()

    @property
    def library_path(self) -> Path:
        """Get library path."""
        return Path(self.get('library.path', Path.home() / "Music"))

    @property
    def database_path(self) -> Path:
        """Get database path."""
        return Path(self.get('database.path', self.DEFAULT_DATA_PATH / "library.db"))

    @property
    def supported_formats(self) -> list:
        """Get supported audio formats."""
        return self.get('library.supported_formats', ['.mp3', '.flac', '.m4a', '.ogg'])

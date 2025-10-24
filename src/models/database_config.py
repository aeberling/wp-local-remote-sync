"""
Database configuration model
"""
from dataclasses import dataclass, field
from typing import List
import re


@dataclass
class DatabaseConfig:
    """Database configuration for a WordPress site"""

    # Local database
    local_db_name: str
    local_db_host: str = "localhost"
    local_db_port: int = 3306
    local_db_user: str = "root"
    local_table_prefix: str = "wp_"
    # local_db_password stored in keyring as "{site_id}_db_local"

    # Remote database
    remote_db_name: str = ""
    remote_db_host: str = "localhost"  # Usually localhost via SSH tunnel
    remote_db_port: int = 3306
    remote_db_user: str = ""
    remote_table_prefix: str = "wp_"
    # remote_db_password stored in keyring as "{site_id}_db_remote"

    # WordPress URLs (for search-replace)
    local_url: str = ""
    remote_url: str = ""

    # Table configuration
    exclude_tables: List[str] = field(default_factory=list)
    # Common exclusions: wp_users, wp_usermeta (for push to production)

    # Safety settings
    backup_before_import: bool = True
    require_confirmation_on_push: bool = True
    save_database_backups: bool = True  # Save database dumps to /db folder

    @staticmethod
    def normalize_url(url: str) -> str:
        """
        Normalize a URL for database search-replace operations

        - Strips leading/trailing whitespace
        - Removes trailing slashes
        - Validates URL format (must start with http:// or https://)
        - Fixes common malformations like https:/ (missing slash)

        Args:
            url: URL to normalize

        Returns:
            Normalized URL, or empty string if invalid/empty
        """
        if not url:
            return ""

        url = url.strip()

        # Remove trailing slashes
        url = url.rstrip('/')

        # Fix common malformation: https:/ -> https://
        if url.startswith('https:/') and not url.startswith('https://'):
            url = url.replace('https:/', 'https://', 1)
        elif url.startswith('http:/') and not url.startswith('http://'):
            url = url.replace('http:/', 'http://', 1)

        # Validate URL format
        if not re.match(r'^https?://.+', url):
            # If URL doesn't start with protocol, it's invalid
            return ""

        return url

    def to_dict(self) -> dict:
        """Convert to dictionary for YAML serialization"""
        return {
            'local_db_name': self.local_db_name,
            'local_db_host': self.local_db_host,
            'local_db_port': self.local_db_port,
            'local_db_user': self.local_db_user,
            'local_table_prefix': self.local_table_prefix,
            'remote_db_name': self.remote_db_name,
            'remote_db_host': self.remote_db_host,
            'remote_db_port': self.remote_db_port,
            'remote_db_user': self.remote_db_user,
            'remote_table_prefix': self.remote_table_prefix,
            'local_url': self.local_url,
            'remote_url': self.remote_url,
            'exclude_tables': self.exclude_tables,
            'backup_before_import': self.backup_before_import,
            'require_confirmation_on_push': self.require_confirmation_on_push,
            'save_database_backups': self.save_database_backups
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'DatabaseConfig':
        """Create from dictionary"""
        # Normalize URLs when loading from config
        local_url = cls.normalize_url(data.get('local_url', ''))
        remote_url = cls.normalize_url(data.get('remote_url', ''))

        return cls(
            local_db_name=data.get('local_db_name', ''),
            local_db_host=data.get('local_db_host', 'localhost'),
            local_db_port=data.get('local_db_port', 3306),
            local_db_user=data.get('local_db_user', 'root'),
            local_table_prefix=data.get('local_table_prefix', 'wp_'),
            remote_db_name=data.get('remote_db_name', ''),
            remote_db_host=data.get('remote_db_host', 'localhost'),
            remote_db_port=data.get('remote_db_port', 3306),
            remote_db_user=data.get('remote_db_user', ''),
            remote_table_prefix=data.get('remote_table_prefix', 'wp_'),
            local_url=local_url,
            remote_url=remote_url,
            exclude_tables=data.get('exclude_tables', []),
            backup_before_import=data.get('backup_before_import', True),
            require_confirmation_on_push=data.get('require_confirmation_on_push', True),
            save_database_backups=data.get('save_database_backups', True)
        )

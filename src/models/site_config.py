"""
Site configuration model
"""
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime
from .database_config import DatabaseConfig


@dataclass
class SiteConfig:
    """Configuration for a WordPress site"""
    id: str
    name: str
    local_path: str
    git_repo_path: str
    remote_host: str
    remote_port: int
    remote_path: str
    remote_username: str
    site_url: str = ""  # URL for previewing the live site
    last_pushed_commit: str = ""
    exclude_patterns: List[str] = field(default_factory=lambda: [
        "*.log",
        "wp-config.php",
        "wp-config-local.php",
        ".git/",
        "node_modules/",
        ".DS_Store",
        ".htaccess",
        "*.sql",
        "*.sql.gz",
        ".env",
        ".env.local"
    ])
    pull_include_paths: List[str] = field(default_factory=list)
    database_config: Optional[DatabaseConfig] = None
    last_db_pushed_at: str = ""
    last_db_pulled_at: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self):
        """Convert to dictionary for YAML serialization"""
        result = {
            'id': self.id,
            'name': self.name,
            'local_path': self.local_path,
            'git_repo_path': self.git_repo_path,
            'remote_host': self.remote_host,
            'remote_port': self.remote_port,
            'remote_path': self.remote_path,
            'remote_username': self.remote_username,
            'site_url': self.site_url,
            'last_pushed_commit': self.last_pushed_commit,
            'exclude_patterns': self.exclude_patterns,
            'pull_include_paths': self.pull_include_paths,
            'last_db_pushed_at': self.last_db_pushed_at,
            'last_db_pulled_at': self.last_db_pulled_at,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
        if self.database_config:
            result['database_config'] = self.database_config.to_dict()
        return result

    @classmethod
    def from_dict(cls, data):
        """Create from dictionary"""
        # Handle database_config separately
        database_config_data = data.pop('database_config', None)
        database_config = None
        if database_config_data:
            database_config = DatabaseConfig.from_dict(database_config_data)

        # Create site config with remaining data
        site_config = cls(**data)
        site_config.database_config = database_config
        return site_config

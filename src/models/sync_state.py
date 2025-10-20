"""
Sync state model
"""
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class OperationState:
    """State of a single operation (push or pull)"""
    timestamp: str = ""
    status: str = "pending"  # pending, success, failed, partial
    files_count: int = 0
    bytes_transferred: int = 0
    error_message: str = ""
    commit_hash: str = ""  # For push operations
    commit_message: str = ""  # For push operations
    date_range_start: str = ""  # For pull operations
    date_range_end: str = ""  # For pull operations

    def to_dict(self):
        return {
            'timestamp': self.timestamp,
            'status': self.status,
            'files_count': self.files_count,
            'bytes_transferred': self.bytes_transferred,
            'error_message': self.error_message,
            'commit_hash': self.commit_hash,
            'commit_message': self.commit_message,
            'date_range_start': self.date_range_start,
            'date_range_end': self.date_range_end
        }

    @classmethod
    def from_dict(cls, data):
        return cls(**data)


@dataclass
class DatabaseOperationState:
    """State of a database sync operation"""
    timestamp: str = ""
    status: str = "pending"  # pending, success, failed, partial
    tables_exported: int = 0
    tables_imported: int = 0
    bytes_transferred: int = 0
    urls_replaced: int = 0
    backup_created: str = ""  # Backup filename if created
    error_message: str = ""

    def to_dict(self):
        return {
            'timestamp': self.timestamp,
            'status': self.status,
            'tables_exported': self.tables_exported,
            'tables_imported': self.tables_imported,
            'bytes_transferred': self.bytes_transferred,
            'urls_replaced': self.urls_replaced,
            'backup_created': self.backup_created,
            'error_message': self.error_message
        }

    @classmethod
    def from_dict(cls, data):
        return cls(**data)


@dataclass
class SyncState:
    """Sync state for a site"""
    site_id: str
    last_push: Optional[OperationState] = None
    last_pull: Optional[OperationState] = None
    last_db_push: Optional[DatabaseOperationState] = None
    last_db_pull: Optional[DatabaseOperationState] = None

    def to_dict(self):
        return {
            'last_push': self.last_push.to_dict() if self.last_push else {},
            'last_pull': self.last_pull.to_dict() if self.last_pull else {},
            'last_db_push': self.last_db_push.to_dict() if self.last_db_push else {},
            'last_db_pull': self.last_db_pull.to_dict() if self.last_db_pull else {}
        }

    @classmethod
    def from_dict(cls, site_id, data):
        return cls(
            site_id=site_id,
            last_push=OperationState.from_dict(data.get('last_push', {})) if data.get('last_push') else None,
            last_pull=OperationState.from_dict(data.get('last_pull', {})) if data.get('last_pull') else None,
            last_db_push=DatabaseOperationState.from_dict(data.get('last_db_push', {})) if data.get('last_db_push') else None,
            last_db_pull=DatabaseOperationState.from_dict(data.get('last_db_pull', {})) if data.get('last_db_pull') else None
        )

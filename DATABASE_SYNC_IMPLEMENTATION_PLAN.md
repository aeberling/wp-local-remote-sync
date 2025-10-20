# Database Sync Implementation Plan

## Overview

This document outlines the implementation plan for adding MySQL database synchronization (push/pull) capabilities to the WordPress Site Deploy tool. The implementation will follow existing architectural patterns and integrate seamlessly with the current file-based sync functionality.

## Objectives

- Enable push (local → remote) and pull (remote → local) database operations
- Handle WordPress-specific challenges (serialized data, URL replacement)
- Maintain safety through backups, confirmations, and dry-run modes
- Follow existing codebase patterns for consistency
- Provide selective table sync capabilities
- Integrate with existing UI and configuration system

## Implementation Approach

### Chosen Method: WP-CLI Integration via SSH

**Rationale:**
- WP-CLI is the standard WordPress command-line tool, already installed in most WordPress hosting environments
- Handles WordPress-specific data (serialized PHP objects, URL replacements) automatically
- Works via SSH (which we already need for SFTP), minimal additional dependencies
- Safe, tested, and well-documented by WordPress community
- Supports dry-run operations and backups

**Alternative Considered:** Direct MySQL connection via SSH tunnel was considered but rejected due to complexity of handling serialized data and URL replacement manually.

---

## Architecture Changes

### New Components to Create

```
src/
├── services/
│   ├── ssh_service.py          # NEW: SSH command execution service
│   └── database_service.py     # NEW: Database sync orchestration
├── controllers/
│   ├── db_push_controller.py   # NEW: Database push operations
│   └── db_pull_controller.py   # NEW: Database pull operations
├── models/
│   └── database_config.py      # NEW: Database configuration dataclass
└── ui/
    └── database_dialog.py      # NEW: Database sync UI dialog
```

### Modified Components

```
src/
├── models/
│   ├── site_config.py          # MODIFY: Add database configuration fields
│   └── sync_state.py           # MODIFY: Add database operation tracking
├── services/
│   └── config_service.py       # MODIFY: Add database credential management
└── ui/
    └── main_window.py          # MODIFY: Add database sync buttons/menu items
```

---

## Detailed Component Specifications

### 1. New Model: `DatabaseConfig` (`src/models/database_config.py`)

```python
@dataclass
class DatabaseConfig:
    """Database configuration for a WordPress site"""

    # Local database
    local_db_name: str
    local_db_host: str = "localhost"
    local_db_port: int = 3306
    local_db_user: str = "root"
    # local_db_password stored in keyring as "{site_id}_db_local"

    # Remote database
    remote_db_name: str
    remote_db_host: str = "localhost"  # Usually localhost via SSH tunnel
    remote_db_port: int = 3306
    remote_db_user: str
    # remote_db_password stored in keyring as "{site_id}_db_remote"

    # WordPress URLs (for search-replace)
    local_url: str
    remote_url: str

    # Table configuration
    exclude_tables: List[str] = field(default_factory=list)
    # Common exclusions: wp_users, wp_usermeta (for push to production)

    # Safety settings
    backup_before_import: bool = True
    require_confirmation_on_push: bool = True

    def to_dict(self) -> dict:
        """Serialize to dictionary"""
        pass

    @classmethod
    def from_dict(cls, data: dict) -> 'DatabaseConfig':
        """Deserialize from dictionary"""
        pass
```

### 2. Modified Model: `SiteConfig` Updates

**Add to `SiteConfig` dataclass:**

```python
@dataclass
class SiteConfig:
    # ... existing fields ...

    # NEW: Database configuration (optional, None if not configured)
    database_config: DatabaseConfig = None

    # NEW: Track last database sync
    last_db_pushed_at: str = ""  # ISO timestamp
    last_db_pulled_at: str = ""  # ISO timestamp
```

### 3. New Service: `SSHService` (`src/services/ssh_service.py`)

**Purpose:** Execute commands on remote server via SSH

**Key Methods:**

```python
class SSHService:
    def __init__(self, host: str, port: int, username: str, password: str = None, key_path: str = None):
        """Initialize SSH connection (reuse SFTPService connection pattern)"""

    def connect(self) -> None:
        """Establish SSH connection"""

    def disconnect(self) -> None:
        """Close SSH connection"""

    def execute_command(self, command: str, timeout: int = 300) -> Tuple[bool, str, str]:
        """
        Execute a command on remote server

        Args:
            command: Shell command to execute
            timeout: Command timeout in seconds (default 5 minutes)

        Returns:
            Tuple of (success, stdout, stderr)
        """

    def test_wp_cli(self, wordpress_path: str) -> Tuple[bool, str]:
        """
        Test if WP-CLI is available on remote server

        Args:
            wordpress_path: Remote WordPress installation path

        Returns:
            Tuple of (available, version_string)
        """

    def __enter__(self):
        """Context manager support"""

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager cleanup"""
```

**Implementation Notes:**
- Use `paramiko.SSHClient` (already a dependency)
- Reuse connection patterns from `SFTPService`
- Support both password and key-based authentication
- Implement proper timeout handling for long-running database operations
- Log all commands executed (for debugging and audit trail)

### 4. New Service: `DatabaseService` (`src/services/database_service.py`)

**Purpose:** Core database operations orchestration

**Key Methods:**

```python
class DatabaseService:
    def __init__(self, site_config: SiteConfig, ssh_service: SSHService = None):
        """Initialize database service"""

    def export_local_database(self, output_path: str, exclude_tables: List[str] = None) -> Tuple[bool, str]:
        """
        Export local WordPress database using WP-CLI

        Args:
            output_path: Local path to save SQL dump
            exclude_tables: Tables to exclude from export

        Returns:
            Tuple of (success, message)

        Implementation:
            wp db export {output_path} --exclude_tables={tables} --path={local_wp_path}
        """

    def import_local_database(self, sql_file: str, backup_first: bool = True) -> Tuple[bool, str]:
        """
        Import database to local WordPress installation

        Args:
            sql_file: Path to SQL dump file
            backup_first: Create backup before import

        Returns:
            Tuple of (success, message)

        Implementation:
            1. If backup_first: wp db export backup.sql
            2. wp db import {sql_file}
        """

    def export_remote_database(self, output_filename: str, exclude_tables: List[str] = None) -> Tuple[bool, str]:
        """
        Export remote database using WP-CLI via SSH

        Args:
            output_filename: Filename for SQL dump on remote server
            exclude_tables: Tables to exclude from export

        Returns:
            Tuple of (success, message)

        Implementation:
            ssh: wp db export {output_filename} --exclude_tables={tables} --path={remote_wp_path}
        """

    def import_remote_database(self, sql_filename: str, backup_first: bool = True) -> Tuple[bool, str]:
        """
        Import database to remote WordPress installation

        Args:
            sql_filename: Filename of SQL dump on remote server
            backup_first: Create backup before import

        Returns:
            Tuple of (success, message)

        Implementation:
            1. If backup_first: ssh: wp db export backup-{timestamp}.sql
            2. ssh: wp db import {sql_filename}
        """

    def search_replace_local(self, search: str, replace: str, dry_run: bool = False) -> Tuple[bool, str, dict]:
        """
        Search and replace in local database (handles serialized data)

        Args:
            search: String to search for (e.g., old URL)
            replace: String to replace with (e.g., new URL)
            dry_run: If True, report changes without making them

        Returns:
            Tuple of (success, message, stats_dict)

        Implementation:
            wp search-replace '{search}' '{replace}' --report-changed-only --path={local_wp_path}
            Add --dry-run flag if dry_run=True
        """

    def search_replace_remote(self, search: str, replace: str, dry_run: bool = False) -> Tuple[bool, str, dict]:
        """Search and replace in remote database via SSH"""

    def get_local_table_list(self) -> List[str]:
        """Get list of tables in local database"""

    def get_remote_table_list(self) -> List[str]:
        """Get list of tables in remote database via SSH"""

    def verify_wp_cli_local(self) -> Tuple[bool, str]:
        """Verify WP-CLI is installed and accessible locally"""

    def verify_wp_cli_remote(self) -> Tuple[bool, str]:
        """Verify WP-CLI is installed and accessible on remote server"""
```

**Implementation Notes:**
- All WP-CLI commands should use `--path=` to specify WordPress installation directory
- Use `--quiet` or `--porcelain` flags for machine-readable output where applicable
- Parse WP-CLI JSON output for structured data (use `--format=json` where supported)
- Implement proper error handling and logging
- Handle temporary files securely (use tempfile module)
- Validate database credentials before operations

### 5. New Controller: `DBPushController` (`src/controllers/db_push_controller.py`)

**Purpose:** Orchestrate database push (local → remote) operations

**Key Method:**

```python
class DBPushController:
    def __init__(self, config_service: ConfigService):
        """Initialize controller"""

    def push(self, site_id: str, exclude_tables: List[str] = None,
             progress_callback: Callable = None) -> Tuple[bool, str, dict]:
        """
        Push local database to remote server

        Args:
            site_id: Site identifier
            exclude_tables: Additional tables to exclude (merged with config)
            progress_callback: Callback function(step, total_steps, message)

        Returns:
            Tuple of (success, message, stats_dict)

        Process:
            1. Verify configuration and credentials
            2. Verify WP-CLI available locally and remotely
            3. Show confirmation dialog (if required_confirmation_on_push=True)
            4. Export local database to temp file
            5. Search-replace local_url → remote_url in temp file
            6. SFTP upload temp file to remote
            7. SSH: Backup remote database (if backup_before_import=True)
            8. SSH: Import database on remote
            9. SSH: Verify import success (check table count)
            10. Clean up temp files
            11. Update sync state

        Stats returned:
            {
                'tables_exported': int,
                'tables_imported': int,
                'bytes_transferred': int,
                'urls_replaced': int,
                'backup_created': str  # filename if created
            }
        """

    def get_push_preview(self, site_id: str) -> Tuple[bool, str, dict]:
        """
        Dry-run: Show what would be pushed

        Returns preview dict:
            {
                'local_tables': List[str],
                'excluded_tables': List[str],
                'urls_to_replace': [(search, replace)],
                'remote_backup_will_be_created': bool,
                'estimated_size_mb': float
            }
        """
```

### 6. New Controller: `DBPullController` (`src/controllers/db_pull_controller.py`)

**Purpose:** Orchestrate database pull (remote → local) operations

**Key Method:**

```python
class DBPullController:
    def __init__(self, config_service: ConfigService):
        """Initialize controller"""

    def pull(self, site_id: str, exclude_tables: List[str] = None,
             progress_callback: Callable = None) -> Tuple[bool, str, dict]:
        """
        Pull remote database to local installation

        Args:
            site_id: Site identifier
            exclude_tables: Additional tables to exclude
            progress_callback: Callback function(step, total_steps, message)

        Returns:
            Tuple of (success, message, stats_dict)

        Process:
            1. Verify configuration and credentials
            2. Verify WP-CLI available locally and remotely
            3. SSH: Export remote database to temp file
            4. SSH: Search-replace remote_url → local_url in temp file
            5. SFTP download temp file to local
            6. Backup local database (if backup_before_import=True)
            7. Import database locally
            8. Verify import success
            9. Clean up temp files
            10. Update sync state

        Stats returned:
            {
                'tables_exported': int,
                'tables_imported': int,
                'bytes_transferred': int,
                'urls_replaced': int,
                'backup_created': str  # filename if created
            }
        """

    def get_pull_preview(self, site_id: str) -> Tuple[bool, str, dict]:
        """
        Dry-run: Show what would be pulled

        Returns preview dict:
            {
                'remote_tables': List[str],
                'excluded_tables': List[str],
                'urls_to_replace': [(search, replace)],
                'local_backup_will_be_created': bool,
                'estimated_size_mb': float
            }
        """
```

### 7. Modified Service: `ConfigService` Updates

**Add Methods:**

```python
# In src/services/config_service.py

def set_database_password(self, site_id: str, db_type: str, password: str) -> None:
    """
    Store database password in system keyring

    Args:
        site_id: Site identifier
        db_type: 'local' or 'remote'
        password: Database password
    """
    keyring.set_password(
        'wp-deploy-db',
        f"{site_id}_{db_type}",
        password
    )

def get_database_password(self, site_id: str, db_type: str) -> str:
    """
    Retrieve database password from system keyring

    Args:
        site_id: Site identifier
        db_type: 'local' or 'remote'

    Returns:
        Password string or None if not found
    """
    return keyring.get_password('wp-deploy-db', f"{site_id}_{db_type}")
```

### 8. Modified Model: `SyncState` Updates

**Add to `OperationState` dataclass:**

```python
# In src/models/sync_state.py

@dataclass
class DatabaseOperationState:
    """State of a database sync operation"""
    timestamp: str
    status: str  # 'success', 'failed', 'partial'
    tables_exported: int = 0
    tables_imported: int = 0
    bytes_transferred: int = 0
    urls_replaced: int = 0
    backup_created: str = ""  # Backup filename if created
    error_message: str = ""

@dataclass
class SyncState:
    # ... existing fields ...

    # NEW: Database operation tracking
    last_db_push: DatabaseOperationState = None
    last_db_pull: DatabaseOperationState = None
```

### 9. New UI: `DatabaseDialog` (`src/ui/database_dialog.py`)

**Purpose:** Configuration dialog for database settings

**UI Elements:**

```
Database Configuration Dialog
├── Local Database Section
│   ├── Database Name: [text input]
│   ├── Host: [text input] (default: localhost)
│   ├── Port: [number input] (default: 3306)
│   ├── Username: [text input] (default: root)
│   └── Password: [password input]
├── Remote Database Section
│   ├── Database Name: [text input]
│   ├── Host: [text input] (default: localhost - via SSH)
│   ├── Port: [number input] (default: 3306)
│   ├── Username: [text input]
│   └── Password: [password input]
├── WordPress URLs Section
│   ├── Local URL: [text input] (e.g., http://site.local)
│   └── Remote URL: [text input] (e.g., https://production.com)
├── Advanced Options
│   ├── Exclude Tables: [multi-line text] (one per line)
│   ├── [✓] Create backup before import
│   └── [✓] Require confirmation when pushing to production
└── Buttons
    ├── [Test Local Connection]
    ├── [Test Remote Connection]
    ├── [Save]
    └── [Cancel]
```

**Features:**
- Validate database connections before saving
- Verify WP-CLI availability on both local and remote
- Show helpful error messages if WP-CLI not found
- Pre-fill common values (localhost, 3306)
- Password fields use show/hide toggle

### 10. Modified UI: `MainWindow` Updates

**Add to main interface:**

```
Main Window
├── Site Selection (existing)
├── File Operations (existing)
│   ├── [Push Files]
│   └── [Pull Files]
├── Database Operations (NEW)
│   ├── [Configure Database] → Opens DatabaseDialog
│   ├── [Push Database] → Runs DBPushController
│   │   └── Shows confirmation dialog with preview
│   └── [Pull Database] → Runs DBPullController
│       └── Shows preview before execution
└── Status Display (existing)
    └── Add database operation status tracking
```

**Button States:**
- "Configure Database" always enabled
- "Push Database" / "Pull Database" enabled only if database configured
- Show warning icon if database not configured
- Disable during operations (prevent concurrent ops)

---

## Configuration File Updates

### Updated `sites.yaml` Structure

```yaml
sites:
  - id: "my-site"
    name: "My WordPress Site"

    # Existing file sync configuration
    local_path: "/Users/yourname/Local Sites/my-site/app/public"
    git_repo_path: "/Users/yourname/Local Sites/my-site/app/public"
    remote_host: "ssh.kinsta.com"
    remote_port: 22
    remote_path: "/www/my-site/public"
    remote_username: "mysite"
    last_pushed_commit: "abc123..."
    exclude_patterns: ["*.log", "wp-config.php", ...]
    pull_include_paths: ["wp-content/uploads"]

    # NEW: Database configuration (optional)
    database_config:
      # Local database
      local_db_name: "local_wp_db"
      local_db_host: "localhost"
      local_db_port: 3306
      local_db_user: "root"
      # local_db_password stored in keyring

      # Remote database
      remote_db_name: "production_wp_db"
      remote_db_host: "localhost"  # Accessed via SSH tunnel
      remote_db_port: 3306
      remote_db_user: "wp_user"
      # remote_db_password stored in keyring

      # WordPress URLs
      local_url: "http://my-site.local"
      remote_url: "https://my-site.com"

      # Tables to exclude from sync
      exclude_tables:
        # Common exclusions when pushing to production
        - "wp_users"         # Don't overwrite production users
        - "wp_usermeta"      # Don't overwrite production user metadata
        - "wp_sessions"      # Temporary data
        - "wp_woocommerce_sessions"  # If using WooCommerce

      # Safety settings
      backup_before_import: true
      require_confirmation_on_push: true

    # Timestamps
    last_db_pushed_at: "2025-10-20T15:30:00"
    last_db_pulled_at: "2025-10-19T10:15:00"
    created_at: "2025-01-15T12:00:00"
    updated_at: "2025-10-20T15:30:00"
```

### Updated `sync_state.json` Structure

```json
{
  "my-site": {
    "site_id": "my-site",
    "last_push": {
      "timestamp": "2025-10-20T15:30:00",
      "status": "success",
      "files_count": 42,
      "bytes_transferred": 1048576,
      "commit_hash": "abc123...",
      "commit_message": "Updated theme"
    },
    "last_pull": { ... },
    "last_db_push": {
      "timestamp": "2025-10-20T15:35:00",
      "status": "success",
      "tables_exported": 12,
      "tables_imported": 12,
      "bytes_transferred": 5242880,
      "urls_replaced": 847,
      "backup_created": "backup-20251020-153500.sql"
    },
    "last_db_pull": {
      "timestamp": "2025-10-19T10:15:00",
      "status": "success",
      "tables_exported": 12,
      "tables_imported": 12,
      "bytes_transferred": 8388608,
      "urls_replaced": 1203,
      "backup_created": "backup-20251019-101500.sql"
    }
  }
}
```

---

## Safety Mechanisms

### 1. Confirmation Dialogs

**Push to Production Warning:**
```
⚠️ WARNING: Push Database to Production

You are about to OVERWRITE the PRODUCTION database with your local database.

This will:
  • Replace all content, posts, and pages
  • Potentially affect live users and orders
  • Create a backup first (recommended)

Site: My WordPress Site
From: http://my-site.local (Local)
To:   https://my-site.com (Production)

Tables to sync: 10 tables
Tables excluded: wp_users, wp_usermeta
Estimated size: 5.2 MB

A backup will be created before import.

Are you absolutely sure you want to continue?

[Yes, Push to Production]  [Cancel]
```

**Pull from Production Info:**
```
ℹ️ Pull Database from Production

You are about to overwrite your LOCAL database with the production database.

Your local development work in the database will be lost.

Site: My WordPress Site
From: https://my-site.com (Production)
To:   http://my-site.local (Local)

Tables to sync: 12 tables
Estimated size: 8.4 MB

A backup of your local database will be created.

Continue?

[Yes, Pull Database]  [Cancel]
```

### 2. Automatic Backups

**Backup Naming Convention:**
```
{environment}-backup-{timestamp}.sql

Examples:
- local-backup-20251020-153000.sql
- remote-backup-20251020-153000.sql
```

**Backup Location:**
- Local backups: `~/.wp-deploy/backups/{site_id}/`
- Remote backups: `/tmp/wp-deploy-backups/` (cleaned after 7 days)

**Backup Retention:**
- Keep last 10 backups per site locally
- Older backups automatically pruned
- User can manually manage backups via UI

### 3. Dry-Run / Preview Mode

Before any database operation, show preview:

```
Database Push Preview
─────────────────────────────────────
Source: Local (http://my-site.local)
Destination: Production (https://my-site.com)

Tables to export: 10
  ✓ wp_posts (1,247 rows)
  ✓ wp_postmeta (8,932 rows)
  ✓ wp_options (342 rows)
  ✓ wp_comments (89 rows)
  ✓ wp_commentmeta (156 rows)
  ✓ wp_terms (45 rows)
  ✓ wp_term_taxonomy (45 rows)
  ✓ wp_term_relationships (1,023 rows)
  ✓ wp_termmeta (89 rows)
  ✓ wp_links (0 rows)

Tables excluded: 2
  ✗ wp_users (will not be modified)
  ✗ wp_usermeta (will not be modified)

URL Replacements:
  • 'http://my-site.local' → 'https://my-site.com'
  • '/Users/yourname/Local Sites/my-site' → '/www/my-site'

Estimated size: 5.2 MB
Transfer time: ~30 seconds

Safety:
  ✓ Production backup will be created
  ✓ Backup name: remote-backup-20251020-153000.sql

[Proceed with Push]  [Cancel]
```

### 4. Pre-Flight Checks

Before any operation, verify:

```python
def pre_flight_checks(self, site_config: SiteConfig) -> Tuple[bool, List[str]]:
    """
    Run pre-flight checks before database operation

    Returns:
        Tuple of (all_passed, list_of_issues)
    """
    issues = []

    # 1. Verify WP-CLI installed locally
    # 2. Verify WP-CLI installed remotely
    # 3. Test database connections (local and remote)
    # 4. Verify WordPress paths exist
    # 5. Check disk space (local and remote)
    # 6. Verify SSH connection
    # 7. Check if WordPress is in maintenance mode
    # 8. Validate URL formats

    return len(issues) == 0, issues
```

### 5. Operation Logging

Log all database operations to dedicated log file:

```
~/.wp-deploy/logs/database-operations.log

Format:
[2025-10-20 15:30:00] [my-site] DB_PUSH_START
[2025-10-20 15:30:05] [my-site] EXPORT_LOCAL: 10 tables, 5.2 MB
[2025-10-20 15:30:10] [my-site] SEARCH_REPLACE: 847 replacements
[2025-10-20 15:30:15] [my-site] UPLOAD: 5.2 MB transferred
[2025-10-20 15:30:20] [my-site] BACKUP_REMOTE: remote-backup-20251020-153000.sql
[2025-10-20 15:30:30] [my-site] IMPORT_REMOTE: SUCCESS
[2025-10-20 15:30:35] [my-site] DB_PUSH_COMPLETE: 35 seconds
```

---

## Dependencies

### Python Package Updates

**Add to `requirements.txt`:**

```
# Existing dependencies remain unchanged
paramiko==3.4.0
GitPython==3.1.40
pyyaml==6.0.1
keyring==24.3.0
python-dateutil==2.8.2

# No new Python packages required!
# WP-CLI is external dependency
```

### External Dependencies

**WP-CLI (WordPress Command Line Interface)**

**Installation:**

- **macOS:** `brew install wp-cli`
- **Linux:** `curl -O https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar`
- **Remote server:** Usually pre-installed by hosting provider (Kinsta, WP Engine, etc.)

**Version requirement:** WP-CLI 2.0 or higher

**Verification:**
```bash
wp --version
# Output: WP-CLI 2.10.0
```

### Documentation Updates Needed

**README.md additions:**
- New "Database Sync" section explaining features
- Installation instructions for WP-CLI
- Common database sync workflows
- Troubleshooting guide

**DEVELOPMENT_DOCUMENTATION.md additions:**
- Architecture overview of database sync
- Database service API reference
- Testing procedures for database operations

---

## Implementation Phases

### Phase 1: Core Infrastructure (Week 1)

**Tasks:**
1. Create `DatabaseConfig` model
2. Update `SiteConfig` to include database configuration
3. Update `ConfigService` with database password management
4. Create `SSHService` for remote command execution
5. Write unit tests for new models and SSH service

**Deliverables:**
- Database configuration can be stored and retrieved
- SSH commands can be executed on remote server
- All tests passing

### Phase 2: Database Service (Week 2)

**Tasks:**
1. Create `DatabaseService` class
2. Implement WP-CLI wrapper methods (export, import, search-replace)
3. Implement local database operations
4. Implement remote database operations via SSH
5. Add pre-flight checks
6. Write unit tests (mock WP-CLI calls)
7. Write integration tests (requires test WordPress installation)

**Deliverables:**
- Can export/import databases locally
- Can export/import databases remotely
- URL replacement works correctly
- All tests passing

### Phase 3: Controllers (Week 3)

**Tasks:**
1. Create `DBPushController`
2. Create `DBPullController`
3. Implement full push workflow with backups
4. Implement full pull workflow with backups
5. Implement preview/dry-run modes
6. Update `SyncState` tracking
7. Write controller tests

**Deliverables:**
- Complete push/pull workflows functional
- Backups created automatically
- Operation state tracked
- All tests passing

### Phase 4: User Interface (Week 4)

**Tasks:**
1. Create `DatabaseDialog` for configuration
2. Update `MainWindow` with database buttons
3. Add confirmation dialogs
4. Add preview displays
5. Integrate progress callbacks
6. Add error handling and user-friendly messages
7. UI/UX testing

**Deliverables:**
- Users can configure database settings via UI
- Users can push/pull databases via UI
- Clear feedback and progress indication
- Professional confirmation dialogs

### Phase 5: Safety & Polish (Week 5)

**Tasks:**
1. Implement backup management (view, restore, delete old backups)
2. Add backup retention policy
3. Enhance logging
4. Add telemetry for debugging
5. Update documentation (README, development docs)
6. Create user guide with screenshots
7. Comprehensive testing across different scenarios

**Deliverables:**
- Backup management UI
- Complete documentation
- User guide
- All edge cases handled

### Phase 6: Testing & Release (Week 6)

**Tasks:**
1. End-to-end testing with real WordPress sites
2. Test with different hosting providers (Kinsta, WP Engine, generic)
3. Test error scenarios (connection failures, WP-CLI not found, etc.)
4. Performance testing with large databases
5. Security audit (credential handling, SQL injection prevention)
6. Beta testing with real users
7. Bug fixes
8. Release v2.0.0

**Deliverables:**
- Stable, production-ready database sync feature
- No critical bugs
- Positive beta tester feedback

---

## Testing Strategy

### Unit Tests

**Test Coverage Required:**

1. **Model Tests** (`tests/models/test_database_config.py`)
   - Serialization/deserialization
   - Default values
   - Validation

2. **Service Tests** (`tests/services/test_ssh_service.py`)
   - Connection handling
   - Command execution
   - Error handling
   - Timeout behavior

3. **Service Tests** (`tests/services/test_database_service.py`)
   - Mock WP-CLI command generation
   - Export/import logic
   - Search-replace URL validation
   - Table exclusion logic

4. **Controller Tests** (`tests/controllers/test_db_push_controller.py`)
   - Push workflow orchestration
   - Backup creation
   - Error rollback
   - State updates

5. **Controller Tests** (`tests/controllers/test_db_pull_controller.py`)
   - Pull workflow orchestration
   - Similar to push tests

### Integration Tests

**Test Scenarios:**

1. **Local Database Operations**
   - Export local WordPress database
   - Import database to local WordPress
   - Search-replace URLs in local database
   - Verify data integrity after import

2. **Remote Database Operations**
   - Execute WP-CLI commands via SSH
   - Export remote database
   - Import database to remote WordPress
   - Handle SSH connection failures

3. **End-to-End Workflows**
   - Complete push: Local → Remote
   - Complete pull: Remote → Local
   - Verify URL replacements work correctly
   - Verify backups are created
   - Verify table exclusions work

### Test Environment Setup

**Requirements:**

1. **Local WordPress Installation**
   - Installed via Local by Flywheel or similar
   - WP-CLI installed and functional
   - Test database with sample data

2. **Remote Test Server**
   - Staging WordPress installation
   - SSH access configured
   - WP-CLI available
   - Separate from production

3. **Test Fixtures**
   - Sample database dumps
   - Mock SSH responses
   - Configuration files

### Performance Testing

**Metrics to Track:**

1. **Database Sizes:**
   - Small: < 10 MB (typical blog)
   - Medium: 10-100 MB (typical business site)
   - Large: 100-500 MB (e-commerce site)
   - Extra Large: > 500 MB (large e-commerce)

2. **Expected Performance:**
   - Export: < 30 seconds for medium database
   - Transfer: Depends on connection speed
   - Import: < 60 seconds for medium database
   - Search-replace: < 30 seconds for medium database
   - Total: < 3 minutes for complete push/pull

3. **Load Testing:**
   - Test with databases containing 1M+ rows
   - Test with slow connections
   - Test concurrent operations (should be prevented)

---

## Security Considerations

### 1. Credential Management

**Requirements:**
- All database passwords stored in system keyring (never in plain text)
- SSH passwords reused from existing SFTP configuration
- No credentials in logs
- No credentials in error messages shown to user

**Implementation:**
```python
# Good - credentials from keyring
password = config_service.get_database_password(site_id, 'local')

# Bad - NEVER do this
password = site_config.database_config.local_db_password  # Don't store here!
```

### 2. SQL Injection Prevention

**Note:** Since we're using WP-CLI (not raw SQL), injection risk is minimal. However:

- Validate all user inputs (database names, table names, URLs)
- Use WP-CLI's built-in escaping
- Never construct raw SQL queries
- Sanitize file paths and filenames

### 3. SSH Command Injection Prevention

**Requirements:**
- Escape all shell arguments using `shlex.quote()`
- Validate file paths
- Don't allow user-supplied commands

**Implementation:**
```python
import shlex

# Good
command = f"wp db export {shlex.quote(filename)}"

# Bad - vulnerable to injection
command = f"wp db export {filename}"  # If filename = "test.sql; rm -rf /"
```

### 4. Backup Security

**Requirements:**
- Store backups in user-specific directory with restricted permissions
- Include timestamp in filenames to prevent overwrites
- Implement backup retention (auto-delete old backups)
- Encrypt sensitive backups (optional, future enhancement)

### 5. Remote File Handling

**Requirements:**
- Use unique temporary filenames on remote server
- Clean up temporary files after operations
- Don't leave database dumps in web-accessible directories
- Verify file deletions after cleanup

---

## Error Handling

### Error Categories

**1. Configuration Errors**
- Database not configured
- Invalid credentials
- Invalid URLs

**User Action:** Show configuration dialog with error highlighted

**2. Connection Errors**
- Cannot connect to database
- Cannot connect via SSH
- SFTP transfer failure

**User Action:** Show troubleshooting guide, test connection button

**3. WP-CLI Errors**
- WP-CLI not found
- WP-CLI version too old
- WP-CLI command failed

**User Action:** Show installation instructions, link to WP-CLI docs

**4. Database Operation Errors**
- Export failed
- Import failed
- Search-replace failed

**User Action:** Show detailed error, offer to restore from backup

**5. Disk Space Errors**
- Not enough local disk space
- Not enough remote disk space

**User Action:** Show required vs available space, suggest cleanup

### Error Recovery

**Automatic Recovery:**
1. Retry failed operations (with exponential backoff)
2. Clean up temporary files on error
3. Restore from backup if import fails

**Manual Recovery:**
1. Provide "Restore from Backup" button in UI
2. Keep detailed logs for debugging
3. Offer to contact support with error details

### User-Friendly Error Messages

**Example:**

```
❌ Database Push Failed

Problem: WP-CLI is not installed on the remote server.

What this means:
The remote server needs the WP-CLI command-line tool to import
databases. Most WordPress hosting providers (like Kinsta, WP Engine)
have this installed by default.

How to fix:
1. Contact your hosting provider to confirm WP-CLI is installed
2. Try running this command via SSH: wp --version
3. If WP-CLI is not available, ask your host to install it

Need help? Check our troubleshooting guide:
https://github.com/yourusername/wp-deploy/wiki/Database-Sync-Troubleshooting

[View Detailed Logs]  [Close]
```

---

## Future Enhancements

### Phase 2 Features (Not in Initial Implementation)

**1. Selective Table Sync**
- UI to select specific tables to sync (checkbox list)
- Save table preferences per site
- Useful for syncing only content, not settings

**2. Scheduled Database Pulls**
- Automated nightly pulls from production
- Keep local development in sync with production content
- Configurable schedule

**3. Database Diff Viewer**
- Compare local vs remote database before sync
- Show which tables have changed
- Preview what data will be overwritten

**4. Multi-Environment Support**
- Support for dev → staging → production workflow
- Push database through environments sequentially
- Environment-specific URL configurations

**5. Database Sanitization**
- Anonymize user data when pulling to local (GDPR compliance)
- Remove sensitive data (credit cards, emails)
- Useful for sharing with contractors/developers

**6. Compression Support**
- Gzip database dumps before transfer
- Significantly faster for large databases
- Less bandwidth usage

**7. Incremental Database Sync**
- Only sync changed rows (using timestamps)
- Much faster for large databases
- More complex implementation

**8. Rollback Mechanism**
- One-click rollback to previous backup
- Keep backup history
- Verify backup integrity before deletion

**9. Database Health Checks**
- Optimize tables after import
- Check for corrupted tables
- Report database size and optimization suggestions

**10. Advanced Search-Replace**
- Multiple search-replace patterns in one operation
- Preview changes before applying
- Support for regular expressions

---

## Risk Assessment

### High Priority Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Data loss on production due to accidental push | Critical | Medium | Confirmation dialogs, automatic backups, preview mode |
| WP-CLI not available on remote server | High | Low | Pre-flight checks, clear error messages, documentation |
| Database too large to transfer | Medium | Medium | Progress indicators, timeout handling, compression (future) |
| URL replacement breaks serialized data | High | Low | Use WP-CLI search-replace (handles serialization), extensive testing |
| SSH connection drops mid-operation | Medium | Low | Transaction-like behavior, cleanup temporary files, retry logic |

### Medium Priority Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Different WordPress versions (local vs remote) | Medium | Medium | Version compatibility checks, warnings in UI |
| Different table prefixes (local vs remote) | Low | Low | Document that prefixes should match, or detect and handle |
| Plugins active on one environment but not the other | Medium | High | Document as known limitation, suggest plugin sync |
| User credentials stored insecurely | Critical | Very Low | Use system keyring, regular security audits |

### Low Priority Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Performance issues with very large databases | Low | Low | Document limitations, suggest direct MySQL approach for huge DBs |
| Backup retention fills disk | Low | Low | Automatic cleanup of old backups, configurable retention |

---

## Success Metrics

### Functional Success Criteria

- [ ] Database configuration can be added/edited via UI
- [ ] Push database from local to remote works reliably
- [ ] Pull database from remote to local works reliably
- [ ] URL replacement works correctly (including serialized data)
- [ ] Automatic backups are created before imports
- [ ] Table exclusions work as configured
- [ ] All operations properly logged
- [ ] Error messages are clear and actionable
- [ ] Works with major hosting providers (Kinsta, WP Engine, generic cPanel)

### Non-Functional Success Criteria

- [ ] 95%+ test coverage for database components
- [ ] No critical or high-severity bugs in beta testing
- [ ] Database operations complete in < 3 minutes for typical sites
- [ ] Zero data loss incidents in testing
- [ ] Documentation complete and comprehensive
- [ ] Beta testers rate usability 4/5 or higher

### User Acceptance Criteria

- [ ] Users can push/pull databases without reading documentation
- [ ] Users feel confident that their data is safe
- [ ] Users understand what will happen before operations execute
- [ ] Users can recover from errors without losing data
- [ ] Users report time savings vs manual database sync

---

## Documentation Requirements

### User-Facing Documentation

**README.md Updates:**
1. Add "Database Sync" section to features list
2. Installation instructions for WP-CLI
3. Quick start guide for database sync
4. Common workflows:
   - Pulling production content to local
   - Pushing local changes to staging
   - Creating backups manually
5. Troubleshooting section:
   - WP-CLI not found
   - Connection errors
   - Import failures

**User Guide (New File: `docs/DATABASE_SYNC_GUIDE.md`):**
1. Complete feature overview
2. Step-by-step tutorials with screenshots
3. Configuration best practices
4. Table exclusion recommendations
5. Safety tips for production databases
6. FAQ section

### Developer-Facing Documentation

**DEVELOPMENT_DOCUMENTATION.md Updates:**
1. Database sync architecture overview
2. Component relationships diagram
3. API reference for new services
4. Testing procedures
5. Adding new database operations
6. Debugging tips

**Code Documentation:**
- Comprehensive docstrings for all public methods
- Type hints for all function signatures
- Inline comments for complex logic
- Example usage in docstrings

---

## Migration Guide for Existing Users

### Backwards Compatibility

**Existing Installations:**
- All existing file sync functionality remains unchanged
- Database features are purely additive
- Sites without database configuration continue to work normally
- No breaking changes to configuration format

**Migration Steps:**

1. **Update Application:**
   - Install new version via `git pull` or download
   - Install WP-CLI if not already installed
   - Run `pip install -r requirements.txt` (no new packages, but safe to run)

2. **Configure Database (Optional):**
   - Open existing site in UI
   - Click "Configure Database" button
   - Fill in database details
   - Test connections
   - Save configuration

3. **First Database Sync:**
   - Start with PULL (safer) to test functionality
   - Review preview before proceeding
   - Verify backup was created
   - Check that local database updated correctly

**Rollback Plan:**
If issues occur:
- Database configuration is stored separately (won't break file sync)
- Can revert to previous version via git
- Existing functionality unaffected

---

## Appendix

### A. WP-CLI Command Reference

**Commands to be used:**

```bash
# Database export
wp db export [filename] --path=/path/to/wordpress --exclude_tables=table1,table2

# Database import
wp db import [filename] --path=/path/to/wordpress

# Search-replace (handles serialized data)
wp search-replace 'old-url' 'new-url' --path=/path/to/wordpress --report-changed-only

# Dry-run search-replace
wp search-replace 'old-url' 'new-url' --dry-run --path=/path/to/wordpress

# List tables
wp db tables --path=/path/to/wordpress --format=csv

# Check WP-CLI version
wp --version

# Database optimization (future)
wp db optimize --path=/path/to/wordpress
```

### B. Hosting Provider Compatibility

**Tested Providers:**

| Provider | WP-CLI Available | SSH Access | Database Access | Notes |
|----------|-----------------|------------|-----------------|-------|
| Kinsta | ✅ Yes | ✅ Yes | ✅ Yes | WP-CLI pre-installed |
| WP Engine | ✅ Yes | ✅ Yes | ✅ Yes | WP-CLI pre-installed |
| SiteGround | ✅ Yes | ✅ Yes | ✅ Yes | May need to enable SSH |
| Bluehost | ⚠️ Varies | ✅ Yes | ✅ Yes | WP-CLI might need manual installation |
| Generic cPanel | ⚠️ Varies | ✅ Yes | ✅ Yes | WP-CLI might need manual installation |
| Flywheel | ✅ Yes | ✅ Yes | ✅ Yes | WP-CLI pre-installed |

### C. Common Database Sizes

**Reference for testing:**

| Site Type | Typical Size | Tables | Example |
|-----------|--------------|--------|---------|
| Small blog | 5-10 MB | 12 | Personal WordPress blog |
| Business site | 20-50 MB | 15-20 | Corporate website with blog |
| Medium e-commerce | 100-300 MB | 30-40 | WooCommerce store with 1000 products |
| Large e-commerce | 500 MB - 2 GB | 50+ | WooCommerce store with 10,000+ products |
| Enterprise | 2-10 GB | 100+ | Multi-site network or large platform |

### D. Sample Exclude Tables List

**Common tables to exclude when pushing to production:**

```yaml
exclude_tables:
  # Users (don't overwrite production users)
  - "wp_users"
  - "wp_usermeta"

  # Sessions and transients (temporary data)
  - "wp_sessions"
  - "wp_options"  # Be careful - contains important settings

  # WooCommerce specific
  - "wp_woocommerce_sessions"
  - "wp_woocommerce_orders"  # Don't overwrite production orders!
  - "wp_woocommerce_order_items"
  - "wp_wc_orders"
  - "wp_wc_customer_lookup"

  # Form submissions
  - "wp_gf_entry"  # Gravity Forms entries
  - "wp_gf_entry_meta"

  # Analytics and logs
  - "wp_statistics_visitor"
  - "wp_statistics_pages"
  - "wp_actionscheduler_actions"
```

**Common tables to exclude when pulling to local:**

```yaml
exclude_tables:
  # Usually want ALL data when pulling
  # But might exclude:
  - "wp_actionscheduler_actions"  # Scheduled tasks
  - "wp_statistics_visitor"  # Large analytics tables
```

---

## Conclusion

This implementation plan provides a comprehensive roadmap for adding MySQL database synchronization to the WordPress Site Deploy tool. The approach:

✅ **Follows existing patterns** - Uses same architecture as file sync
✅ **Prioritizes safety** - Multiple confirmation and backup mechanisms
✅ **Handles WordPress specifics** - Uses WP-CLI for serialized data and URL replacement
✅ **Provides great UX** - Clear previews, progress indicators, helpful errors
✅ **Well-tested** - Comprehensive test strategy
✅ **Well-documented** - User and developer documentation
✅ **Phased approach** - Deliverables spread across 6 weeks

**Estimated Development Time:** 6 weeks (1 developer)
**Complexity:** Medium-High
**Risk:** Low (with proper testing and safety mechanisms)
**Value:** High (major feature requested by WordPress developers)

---

**Document Version:** 1.0
**Created:** October 20, 2025
**Author:** Implementation Planning Team
**Status:** Ready for Review

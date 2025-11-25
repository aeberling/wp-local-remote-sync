# SSH/SFTP Deployment - Quick Reference

## File Locations

| Item | Path |
|------|------|
| SFTP Service | `/Users/adam/Desktop/CODING/SANDBOX/Site-Deploy/src/services/sftp_service.py` |
| SSH Service | `/Users/adam/Desktop/CODING/SANDBOX/Site-Deploy/src/services/ssh_service.py` |
| Push Controller | `/Users/adam/Desktop/CODING/SANDBOX/Site-Deploy/src/controllers/push_controller.py` |
| Pull Controller | `/Users/adam/Desktop/CODING/SANDBOX/Site-Deploy/src/controllers/pull_controller.py` |
| Site Config Model | `/Users/adam/Desktop/CODING/SANDBOX/Site-Deploy/src/models/site_config.py` |
| Config Service | `/Users/adam/Desktop/CODING/SANDBOX/Site-Deploy/src/services/config_service.py` |
| Site Dialog UI | `/Users/adam/Desktop/CODING/SANDBOX/Site-Deploy/src/ui/site_dialog.py` |
| Main Window | `/Users/adam/Desktop/CODING/SANDBOX/Site-Deploy/src/ui/main_window.py` |
| File Patterns | `/Users/adam/Desktop/CODING/SANDBOX/Site-Deploy/src/utils/patterns.py` |

---

## Key Classes and Methods

### SFTPService

```python
from services.sftp_service import SFTPService

# Create instance
sftp = SFTPService(
    host="example.com",
    port=22,
    username="user",
    password="pass"  # or key_path="/path/to/key"
)

# Connect
sftp.connect()

# Upload
success, msg = sftp.upload_file(local_path, remote_path, progress_callback=None)

# Download
success, msg = sftp.download_file(remote_path, local_path, progress_callback=None)

# List files with date filter
files = sftp.list_files_recursive(
    remote_path,
    start_date=datetime(2024, 10, 1),
    end_date=datetime(2024, 10, 31)
)

# Disconnect
sftp.disconnect()

# Context manager
with SFTPService(host, port, user, pwd) as sftp:
    sftp.upload_file(local, remote)
```

### SSHService

```python
from services.ssh_service import SSHService

ssh = SSHService(host, port, username, password)
ssh.connect()

# Execute command
success, stdout, stderr = ssh.execute_command("ls -la", timeout=30)

# Test WP-CLI
available, version = ssh.test_wp_cli("/var/www/html")

# Test connection
success, msg = ssh.test_connection()

ssh.disconnect()
```

### PushController

```python
from controllers.push_controller import PushController

push = PushController(config_service)

# Incremental push (only changed files since last push)
success, msg, stats = push.push(
    site_id="abc12345",
    progress_callback=lambda c, t, m: print(f"{c}/{t}: {m}")
)

# Full push (all files)
success, msg, stats = push.push_all(site_id="abc12345")

# Dry run - see what would be pushed
success, msg, files = push.get_files_to_push(site_id="abc12345")
```

### PullController

```python
from controllers.pull_controller import PullController
from datetime import datetime, timedelta

pull = PullController(config_service)

# Pull files modified in date range
success, msg, stats = pull.pull(
    site_id="abc12345",
    start_date=datetime(2024, 10, 1),
    end_date=datetime(2024, 10, 31),
    include_paths=["wp-content/uploads", "wp-content/themes/custom"],
    progress_callback=lambda c, t, m: print(f"{c}/{t}: {m}")
)

# Dry run
success, msg, files = pull.get_files_to_pull(
    site_id="abc12345",
    start_date=datetime.now() - timedelta(days=1),
    end_date=datetime.now()
)
```

### ConfigService

```python
from services.config_service import ConfigService

config = ConfigService()

# Site operations
site = config.get_site("abc12345")
all_sites = config.get_all_sites()
config.add_site(site, password="ssh_pwd")
config.update_site(site)
config.delete_site("abc12345")

# Password storage
config.set_password("abc12345", "ssh_password")
pwd = config.get_password("abc12345")

# Database passwords
config.set_database_password("abc12345", "local", "db_pwd")
config.set_database_password("abc12345", "remote", "db_pwd")

# Sync state
state = config.get_sync_state("abc12345")
config.update_sync_state(state)
```

---

## Data Models

### SiteConfig

```python
@dataclass
class SiteConfig:
    id: str                              # 8-char UUID
    name: str                            # Display name
    local_path: str                      # Local WordPress root
    git_repo_path: str                   # Git repository path
    remote_host: str                     # SSH hostname
    remote_port: int                     # SSH port (22)
    remote_path: str                     # Remote WordPress root
    remote_username: str                 # SSH username
    site_url: str = ""                   # Site URL
    last_pushed_commit: str = ""         # Last successful push
    exclude_patterns: List[str] = [...]  # Files to skip
    pull_include_paths: List[str] = []   # Directories to pull
    database_config: Optional[DatabaseConfig] = None
    last_db_pushed_at: str = ""
    last_db_pulled_at: str = ""
    created_at: str                      # ISO timestamp
    updated_at: str                      # ISO timestamp
```

### DatabaseConfig

```python
@dataclass
class DatabaseConfig:
    local_db_name: str
    local_db_host: str = "localhost"
    local_db_port: int = 3306
    local_db_user: str = "root"
    local_table_prefix: str = "wp_"
    
    remote_db_name: str = ""
    remote_db_host: str = "localhost"
    remote_db_port: int = 3306
    remote_db_user: str = ""
    remote_table_prefix: str = "wp_"
    
    local_url: str = ""
    remote_url: str = ""
    exclude_tables: List[str] = ["wp_users", "wp_usermeta"]
    backup_before_import: bool = True
    require_confirmation_on_push: bool = True
```

### OperationState

```python
@dataclass
class OperationState:
    timestamp: str                    # ISO datetime
    status: str                       # "pending", "success", "failed", "partial"
    files_count: int                  # Number of files transferred
    bytes_transferred: int            # Total bytes
    error_message: str = ""           # If failed
    commit_hash: str = ""             # For push
    commit_message: str = ""          # For push
    date_range_start: str = ""        # For pull
    date_range_end: str = ""          # For pull
```

---

## Configuration Files

### ~/.wp-deploy/sites.yaml

```yaml
sites:
  - id: abc12345
    name: "My WordPress Site"
    local_path: "/Users/adam/sites/mysite"
    git_repo_path: "/Users/adam/sites/mysite"
    remote_host: "example.com"
    remote_port: 22
    remote_path: "/var/www/html"
    remote_username: "deploy"
    site_url: "https://example.com"
    exclude_patterns:
      - "*.log"
      - "wp-config.php"
      - ".git/"
      - "node_modules/"
    pull_include_paths:
      - "wp-content/uploads"
      - "wp-content/themes/custom-theme"
    last_pushed_commit: "abc123def456..."
    database_config:
      local_db_name: "mysite_local"
      local_db_host: "localhost"
      local_db_port: 3306
      local_db_user: "root"
      local_table_prefix: "wp_"
      remote_db_name: "mysite_prod"
      remote_db_host: "localhost"
      remote_db_port: 3306
      remote_db_user: "wordpress"
      remote_table_prefix: "wp_"
      local_url: "http://mysite.local"
      remote_url: "https://example.com"
      exclude_tables:
        - "wp_users"
        - "wp_usermeta"
      backup_before_import: true
      require_confirmation_on_push: true
    last_db_pushed_at: "2024-10-20T15:30:00"
    last_db_pulled_at: "2024-10-20T14:20:00"
    created_at: "2024-10-01T10:00:00"
    updated_at: "2024-10-20T15:30:00"
```

### ~/.wp-deploy/sync_state.json

```json
{
  "abc12345": {
    "last_push": {
      "timestamp": "2024-10-20T15:30:00",
      "status": "success",
      "files_count": 42,
      "bytes_transferred": 2097152,
      "error_message": "",
      "commit_hash": "abc123def456...",
      "commit_message": "Update theme files",
      "date_range_start": "",
      "date_range_end": ""
    },
    "last_pull": {
      "timestamp": "2024-10-20T14:20:00",
      "status": "success",
      "files_count": 128,
      "bytes_transferred": 5242880,
      "error_message": "",
      "commit_hash": "",
      "commit_message": "",
      "date_range_start": "2024-10-18T00:00:00",
      "date_range_end": "2024-10-20T00:00:00"
    },
    "last_db_push": {},
    "last_db_pull": {}
  }
}
```

---

## Error Handling

All service methods return tuples with status and message:

```python
# SFTP Methods
success, message = sftp.upload_file(local, remote)
success, message = sftp.download_file(remote, local)
success, message = sftp.test_connection()

# SSH Methods
success, stdout, stderr = ssh.execute_command(cmd)
available, version = ssh.test_wp_cli(path)
success, message = ssh.test_connection()

# Controllers
success, message, stats = push.push(site_id)
success, message, stats = pull.pull(site_id, start, end)

# Check results
if not success:
    print(f"Error: {message}")
    # Handle error
```

---

## Progress Callback Pattern

Used for UI updates during operations:

```python
def progress_callback(current, total, message):
    """
    Args:
        current: Current item number (for controllers)
                or bytes transferred (for SFTP)
        total: Total items (for controllers)
              or total bytes (for SFTP)
        message: Status message string
    """
    print(f"[{current}/{total}] {message}")

# Usage in controllers
success, msg, stats = push.push(
    site_id="abc12345",
    progress_callback=progress_callback
)
```

---

## Default Exclude Patterns

These files/directories are NOT transferred during push:

```
*.log                  # Log files
wp-config.php          # WordPress configuration
wp-config-local.php    # Local configuration
.git/                  # Git directory
node_modules/          # Node packages
.DS_Store              # macOS metadata
.htaccess              # Apache configuration
*.sql                  # SQL backup files
*.sql.gz               # Compressed SQL
.env                   # Environment variables
.env.local             # Local environment
```

---

## Push vs Pull

### Push (Local → Remote)

- Reads Git commit history
- Finds **changed files** since `last_pushed_commit`
- Uploads to remote via SFTP
- Updates `last_pushed_commit`
- **Incremental by nature**

### Pull (Remote → Local)

- Lists files in `pull_include_paths`
- Filters by modification date range (user-specified)
- Downloads from remote via SFTP
- Does **not** track state between pulls
- **Each pull is independent**

---

## Security Features

1. **Credentials Storage**:
   - SSH passwords: OS Keyring
   - Database passwords: OS Keyring
   - NOT stored in config files

2. **File Filtering**:
   - Prevents pushing sensitive files (wp-config, .env)
   - Can be customized per site

3. **Date-Based Filtering**:
   - Pull only recent files
   - Prevents accidental large downloads

4. **Confirmation Dialogs**:
   - Database sync has safety options
   - Requires confirmation on production push (optional)

---

## Common Use Cases

### First-Time Deployment

```python
# 1. Create site config in UI
# 2. Run full push
success, msg, stats = push.push_all(site_id)
# 3. All files uploaded, last_pushed_commit recorded
```

### Incremental Updates

```python
# 1. Make local changes
# 2. Commit to Git
# 3. Click Push button
success, msg, stats = push.push(site_id)
# 4. Only changed files uploaded
```

### Sync Remote Changes

```python
# 1. Click Pull button
# 2. Select date range (e.g., last 24 hours)
# 3. Specify include paths (e.g., uploads)
success, msg, stats = pull.pull(
    site_id,
    start_date=datetime.now() - timedelta(days=1),
    end_date=datetime.now(),
    include_paths=["wp-content/uploads"]
)
# 4. Only recent uploads downloaded
```

### Backup Database

```python
# 1. Pull database from production
# 2. Auto-detects database config from remote wp-config.php
# 3. Exports database
# 4. Creates backup
# 5. URL search-replace (prod → local)
```

---

## Logging

All operations logged to `~/.wp-deploy/logs/`:

```
sftp.log    - SFTP transfer operations
ssh.log     - SSH connections and commands
git.log     - Git operations
push.log    - Push operation details
pull.log    - Pull operation details
config.log  - Configuration changes
db.log      - Database operations
```

Enable debug mode to see detailed logs:

```python
from utils.logger import setup_logger
logger = setup_logger('push', level='DEBUG')
```


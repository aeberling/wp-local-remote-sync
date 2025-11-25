# SSH/SFTP Deployment Implementation Analysis

## Overview
This codebase is a **WordPress Deployment Tool** that manages file and database synchronization between local and remote WordPress installations using SSH/SFTP protocols. It's a Python-based GUI application built with Tkinter.

## Directory Structure

```
src/
├── services/           # Core business logic
│   ├── ssh_service.py       # SSH connection and command execution
│   ├── sftp_service.py      # SFTP file transfer operations
│   ├── git_service.py       # Git repository operations
│   ├── config_service.py    # Configuration management
│   └── database_service.py  # Database sync operations
├── controllers/        # Operation orchestrators
│   ├── push_controller.py    # File upload from local to remote
│   ├── pull_controller.py    # File download from remote to local
│   ├── db_push_controller.py # Database export/upload
│   └── db_pull_controller.py # Database download/import
├── models/            # Data models
│   ├── site_config.py       # Site configuration
│   ├── database_config.py   # Database credentials
│   └── sync_state.py        # Operation state tracking
├── ui/               # User interface
│   ├── main_window.py       # Main application window
│   ├── site_dialog.py       # Site configuration dialog
│   ├── database_dialog.py   # Database sync dialog
│   └── log_viewer.py        # Log viewer
└── utils/            # Utilities
    ├── patterns.py         # File pattern matching
    ├── wp_config_parser.py # WordPress config parsing
    └── logger.py           # Logging setup
```

---

## 1. SSH/SFTP Push and Pull Methods Implementation

### A. SFTP Service (`/Users/adam/Desktop/CODING/SANDBOX/Site-Deploy/src/services/sftp_service.py`)

**Purpose**: Low-level SFTP file transfer operations using Paramiko library.

#### Key Methods:

1. **`connect()`** (lines 37-67)
   - Establishes SSH/SFTP connection
   - Supports both password and private key authentication
   - Uses Paramiko's `SSHClient` and `open_sftp()`
   - Auto-adds host key policy

2. **`disconnect()`** (lines 69-78)
   - Closes SFTP and SSH connections safely

3. **`upload_file()`** (lines 117-157)
   - **Single file upload** from local to remote
   - Creates remote directories recursively
   - Preserves local file permissions on remote
   - Supports progress callback for UI updates
   - Returns: `(success: bool, message: str)`

4. **`download_file()`** (lines 159-191)
   - **Single file download** from remote to local
   - Creates local directories as needed
   - Supports progress callback
   - Returns: `(success: bool, message: str)`

5. **`list_files_recursive()`** (lines 193-232)
   - **Recursive file listing** from remote path
   - Filters by date range (start_date, end_date)
   - Returns list of `(filepath, modification_datetime)` tuples
   - Used for selective pulling

6. **`mkdir_recursive()`** (lines 94-115)
   - Creates nested remote directories
   - Safely handles existing directories

7. **`test_connection()`** (lines 80-92)
   - Validates SSH/SFTP connectivity
   - Returns: `(success: bool, message: str)`

#### Authentication Methods:
- **Password**: Direct SSH password authentication
- **SSH Key**: Via `key_filename` parameter (supports passphrase-protected keys)

#### Context Manager Support:
```python
with SFTPService(host, port, username, password) as sftp:
    sftp.upload_file(local, remote)
```

---

### B. SSH Service (`/Users/adam/Desktop/CODING/SANDBOX/Site-Deploy/src/services/ssh_service.py`)

**Purpose**: Remote command execution via SSH.

#### Key Methods:

1. **`connect()`** (lines 32-61)
   - Similar authentication to SFTP
   - Uses Paramiko's `SSHClient`

2. **`execute_command()`** (lines 72-111)
   - Executes shell commands on remote server
   - Configurable timeout (default 300 seconds)
   - Returns: `(success: bool, stdout: str, stderr: str)`
   - Waits for command completion

3. **`test_wp_cli()`** (lines 113-138)
   - Verifies WP-CLI availability on remote
   - Used for remote database operations

4. **`test_connection()`** (lines 140-159)
   - Tests SSH connectivity with echo command

---

### C. Push Controller (`/Users/adam/Desktop/CODING/SANDBOX/Site-Deploy/src/controllers/push_controller.py`)

**Purpose**: Orchestrates incremental and full file uploads to remote.

#### Key Methods:

1. **`push()`** (lines 23-135) - **Incremental push**
   - **Flow**:
     1. Gets site configuration by ID
     2. Retrieves SSH password from keyring
     3. Gets list of changed files since `last_pushed_commit`
     4. Filters files by `exclude_patterns`
     5. Connects to SFTP
     6. Uploads each file with progress callback
     7. Updates `last_pushed_commit` in config
     8. Records operation in sync state
   - Returns: `(success: bool, message: str, stats_dict)`
   - Stats include: files_pushed, files_failed, bytes_transferred, file_list

2. **`push_all()`** (lines 137-245) - **Full push**
   - Same as `push()` but ignores `last_pushed_commit`
   - Uploads ALL tracked files regardless of history
   - Useful for initial deployment

3. **`get_files_to_push()`** (lines 247-275) - **Dry run**
   - Returns list of files that would be pushed
   - Doesn't perform actual transfer

#### File Filtering:
- Uses Git to determine changed files between commits
- Applies exclusion patterns (see patterns.py)
- Default exclusions: `*.log`, `wp-config.php`, `.git/`, `node_modules/`, `.htaccess`, `*.sql`, `.env`

---

### D. Pull Controller (`/Users/adam/Desktop/CODING/SANDBOX/Site-Deploy/src/controllers/pull_controller.py`)

**Purpose**: Orchestrates selective file downloads from remote.

#### Key Methods:

1. **`pull()`** (lines 22-152) - **Date-based selective pull**
   - **Flow**:
     1. Gets site configuration
     2. Retrieves SSH password from keyring
     3. Uses `pull_include_paths` (e.g., "wp-content/uploads")
     4. Lists all files from remote paths within date range
     5. Filters by `exclude_patterns`
     6. Downloads filtered files
     7. Records in sync state
   - Returns: `(success: bool, message: str, stats_dict)`
   - **Date-based filtering**: Downloads only files modified between `start_date` and `end_date`

2. **`get_files_to_pull()`** (lines 154-212) - **Dry run**
   - Returns list of files matching pull criteria
   - No download performed

#### Pull Include Paths:
- Configured per site (e.g., `wp-content/uploads`, `wp-content/themes/my-theme`)
- Allows selective pulling of specific directories
- Prevents pulling entire remote server

---

## 2. Deployment Settings Storage/Configuration

### A. Configuration Service (`/Users/adam/Desktop/CODING/SANDBOX/Site-Deploy/src/services/config_service.py`)

**Purpose**: Manages all configuration and credential storage.

#### Configuration Storage:
- **Location**: `~/.wp-deploy/`
- **Sites File**: `sites.yaml` - Site configurations (non-sensitive)
- **Sync State File**: `sync_state.json` - Last operation states
- **Credentials**: System keyring (OS-specific)

#### Key Methods:

1. **Site Management**:
   - `add_site()` - Create new site config
   - `update_site()` - Modify existing config
   - `delete_site()` - Remove site
   - `get_site()` - Retrieve by ID
   - `get_all_sites()` - List all sites

2. **Password Storage** (System Keyring):
   ```python
   set_password(site_id, password)        # SSH password for {site_id}
   get_password(site_id)                  # Retrieve SSH password
   set_database_password(site_id, 'local', pwd)   # Database passwords
   get_database_password(site_id, 'remote', pwd)
   ```

3. **Sync State Management**:
   - `get_sync_state()` - Get operation history
   - `update_sync_state()` - Record operation results

---

### B. Site Configuration Model (`/Users/adam/Desktop/CODING/SANDBOX/Site-Deploy/src/models/site_config.py`)

**Data Structure** (stored in YAML):

```yaml
sites:
  - id: abc12345                          # Generated UUID (8 chars)
    name: "My Site"                       # Display name
    local_path: "/Users/adam/sites/mysite"
    git_repo_path: "/Users/adam/sites/mysite"
    remote_host: "example.com"            # SSH host
    remote_port: 22                       # SSH port
    remote_path: "/var/www/html"          # Remote WordPress root
    remote_username: "siteuser"           # SSH username
    site_url: "https://example.com"
    exclude_patterns:                     # Files to skip in push
      - "*.log"
      - "wp-config.php"
      - ".git/"
      - "node_modules/"
    pull_include_paths:                   # Directories to pull from remote
      - "wp-content/uploads"
      - "wp-content/themes/my-theme"
    last_pushed_commit: "abc123def456..."
    database_config: {}                   # See DatabaseConfig model
    last_db_pushed_at: "2024-10-20T15:30:00"
    last_db_pulled_at: "2024-10-20T14:20:00"
```

#### Fields:
- **Local/Git Paths**: Where source files are
- **Remote Host**: SFTP/SSH server hostname
- **Remote Path**: WordPress installation directory on server
- **Exclude Patterns**: Glob patterns for files to skip (push)
- **Pull Include Paths**: Specific directories to sync from remote
- **last_pushed_commit**: Git commit hash of last successful push (for incremental syncs)

---

### C. Database Configuration Model (`/Users/adam/Desktop/CODING/SANDBOX/Site-Deploy/src/models/database_config.py`)

**Stored in Site Config**:

```python
@dataclass
class DatabaseConfig:
    # Local database
    local_db_name: str
    local_db_host: str = "localhost"
    local_db_port: int = 3306
    local_db_user: str = "root"
    local_table_prefix: str = "wp_"
    
    # Remote database (accessed via SSH tunnel)
    remote_db_name: str = ""
    remote_db_host: str = "localhost"     # Usually localhost via SSH
    remote_db_port: int = 3306
    remote_db_user: str = ""
    remote_table_prefix: str = "wp_"
    
    # WordPress URLs (for search-replace after sync)
    local_url: str = ""
    remote_url: str = ""
    
    # Tables to exclude from sync
    exclude_tables: List[str] = ["wp_users", "wp_usermeta"]
    
    # Safety settings
    backup_before_import: bool = True
    require_confirmation_on_push: bool = True
```

**Password Storage**: Database passwords stored separately in keyring (not in YAML).

---

### D. Sync State Model (`/Users/adam/Desktop/CODING/SANDBOX/Site-Deploy/src/models/sync_state.py`)

**Tracks Operation History** (stored in `sync_state.json`):

```python
@dataclass
class OperationState:
    timestamp: str                     # ISO timestamp of operation
    status: str                        # "pending", "success", "failed", "partial"
    files_count: int                   # Number of files transferred
    bytes_transferred: int             # Total bytes
    error_message: str                 # If failed
    commit_hash: str                   # For push: git commit hash
    commit_message: str                # For push: commit message
    date_range_start: str              # For pull: start date
    date_range_end: str                # For pull: end date

@dataclass
class SyncState:
    site_id: str
    last_push: Optional[OperationState]
    last_pull: Optional[OperationState]
    last_db_push: Optional[DatabaseOperationState]
    last_db_pull: Optional[DatabaseOperationState]
```

---

## 3. File Transfer Logic

### A. Push Flow (Local → Remote)

```
push_controller.push(site_id)
    ↓
get_site_config(site_id)
    ↓
get_password(site_id) from keyring
    ↓
GitService.get_changed_files(last_commit, HEAD)
    [OR get_all_tracked_files() if first push]
    ↓
filter_files(exclude_patterns)
    ↓
SFTPService.connect(host, port, username, password)
    ↓
for each file:
    SFTPService.mkdir_recursive(remote_dir)
    SFTPService.upload_file(local_path, remote_path)
    [with progress callback for UI]
    ↓
SFTPService.disconnect()
    ↓
update_last_pushed_commit(site_id, new_commit_hash)
    ↓
update_sync_state(site_id, OperationState)
```

**Key Features**:
- **Incremental**: Only uploads changed files (Git-based)
- **Excludes**: Respects exclude_patterns
- **Preserves**: File permissions on remote
- **Atomic**: Either completes fully or fails cleanly
- **Tracked**: Records success/failure in sync_state.json

---

### B. Pull Flow (Remote → Local)

```
pull_controller.pull(site_id, start_date, end_date, include_paths)
    ↓
get_site_config(site_id)
    ↓
get_password(site_id) from keyring
    ↓
SFTPService.connect(host, port, username, password)
    ↓
for each include_path:
    if path_exists(remote_path):
        list_files_recursive(remote_path, start_date, end_date)
            [Returns files modified within date range]
    ↓
filter_files(exclude_patterns)
    ↓
for each file:
    os.makedirs(local_dir, exist_ok=True)
    SFTPService.download_file(remote_path, local_path)
    [with progress callback for UI]
    ↓
SFTPService.disconnect()
    ↓
update_sync_state(site_id, OperationState)
```

**Key Features**:
- **Selective**: Only pulls specified directories (include_paths)
- **Date-filtered**: Downloads only recently modified files
- **Excludes**: Respects exclude_patterns
- **Creates directories**: Makes local folders as needed
- **Tracked**: Records operation in sync_state.json

---

### C. File Filtering (`/Users/adam/Desktop/CODING/SANDBOX/Site-Deploy/src/utils/patterns.py`)

```python
def should_exclude(file_path, exclude_patterns):
    """
    Checks file against patterns using:
    1. Full path glob matching: fnmatch(file_path, pattern)
    2. Directory matching: /{pattern}/ in /{file_path}/
    3. Filename matching: fnmatch(filename, pattern)
    """
    
def filter_files(files, exclude_patterns):
    """Returns list of files NOT matching any exclude pattern"""
```

**Example Exclusions**:
```
*.log                  # All log files
wp-config.php          # WordPress config
wp-config-local.php    # Local config
.git/                  # Git directory
node_modules/          # npm packages
.DS_Store              # macOS metadata
.htaccess              # Apache config
*.sql                  # SQL backups
*.sql.gz               # Compressed SQL
.env                   # Environment files
.env.local             # Local env
```

---

## 4. UI Structure for Deployment Settings

### A. Main Window (`/Users/adam/Desktop/CODING/SANDBOX/Site-Deploy/src/ui/main_window.py`)

**Tabs**:
1. **Sites** - List of configured sites with push/pull buttons
2. **Database Sync** - Database operations UI
3. **Logs** - Operation logs viewer
4. **Settings** - Application preferences

**Operations**:
- Push button → executes push in thread, shows progress
- Pull button → date picker dialog → executes pull
- Database Sync button → opens database dialog

---

### B. Site Configuration Dialog (`/Users/adam/Desktop/CODING/SANDBOX/Site-Deploy/src/ui/site_dialog.py`)

**Main Window**: 950x750 px

#### Tab 1: SSH/SFTP Configuration

**Section 1: Basic Information**
```
Site Name:        [Text Input]
Local Path:       [Text Input] [Browse...]
Git Repo Path:    [Text Input] [Browse...] [Same as Local]
  Status: ✓ Git repository (commit: abc123d)
```

**Section 2: Remote Server (SSH/SFTP)**
```
Host:             [Text Input]           # e.g., example.com
Port:             [Text Input] (default: 22)
Username:         [Text Input]
Password:         [Password Input]
Remote Path:      [Text Input]           # e.g., /var/www/html
Site URL:         [Text Input]           # e.g., https://example.com
```

**Section 3: Pull Include Paths**
```
[ScrolledText Widget] (6 rows)
wp-content/uploads
wp-content/themes/my-theme
wp-content/plugins/my-plugin
```
*One path per line*

---

#### Tab 2: Database Configuration

**Sub-Tab 2a: Local Database**
```
Database Name:    [Text Input]
Host:             [localhost]
Port:             [3306]
Username:         [root]
Password:         [Password Input]
Table Prefix:     [wp_]
[Auto-detect from wp-config.php]

Site URL:         [Text Input]
```

**Sub-Tab 2b: Remote Database**
```
Database Name:    [Text Input]
Host:             [localhost]  (Usually localhost via SSH)
Port:             [3306]
Username:         [Text Input]
Password:         [Password Input]
Table Prefix:     [wp_]
[Auto-detect from wp-config.php]

Site URL:         [Text Input]
```

**Sub-Tab 2c: Advanced Options**
```
Exclude Tables (one per line):
[ScrolledText Widget] (6 rows)
wp_users
wp_usermeta

Safety Options:
☑ Create backup before import
☑ Require confirmation when pushing to production
```

**Buttons**:
- [Test Local Connection] - Validates WP-CLI and database access locally
- [Test Remote Connection] - SSH → tests WP-CLI and database on remote

---

#### Features:

1. **Auto-detection**:
   - "Auto-detect from wp-config.php" button reads local file and populates fields
   - "Auto-detect from wp-config.php" button (remote) uses SSH to read remote file
   - Extracts: DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, table prefix

2. **Validation**:
   - Connection tests verify SSH/database access before saving
   - Port must be numeric
   - Required fields enforced (name, local path, host)

3. **Context Help**:
   - Grayed-out hints (e.g., "e.g., https://yoursite.com")
   - Remote DB host note: "(Usually 'localhost' via SSH)"

4. **Focus Management**:
   - Tab order: Name → Local Path → Git Path → SSH/SFTP fields
   - Escape key closes dialog
   - macOS focus handling for proper window management

---

### C. Connection Test Dialog

**Local Database Test**:
```
1. Verifies WP-CLI is installed (wp --version)
2. Gets local table list
3. Shows: WP-CLI version and table count
```

**Remote Database Test**:
```
1. SSH connects to remote server
2. Reads remote wp-config.php via SSH
3. Verifies WP-CLI on remote
4. Gets remote table list
5. Shows: SSH/WP-CLI status and table count
```

---

### D. Password Storage and Retrieval

**Implementation** (lines 127-173 in config_service.py):

```python
# SFTP/SSH Password
keyring.set_password("wp-deploy", f"site-{site_id}", password)
keyring.get_password("wp-deploy", f"site-{site_id}")

# Database Passwords
keyring.set_password("wp-deploy-db", f"{site_id}_local", pwd)
keyring.get_password("wp-deploy-db", f"{site_id}_local")

keyring.set_password("wp-deploy-db", f"{site_id}_remote", pwd)
keyring.get_password("wp-deploy-db", f"{site_id}_remote")
```

**Security**:
- Uses OS-specific secure storage (Keychain on macOS, Credential Manager on Windows)
- Passwords NOT stored in YAML config files
- Automatically retrieved when needed for connections

---

## 5. Authentication Methods

### SSH Connection Authentication

**Two Methods** (in both `SSHService` and `SFTPService`):

1. **Password Authentication**:
   ```python
   ssh_client.connect(
       hostname=host,
       port=port,
       username=username,
       password=password
   )
   ```

2. **SSH Key Authentication**:
   ```python
   ssh_client.connect(
       hostname=host,
       port=port,
       username=username,
       key_filename=key_path
   )
   ```

**Configuration Dialog**: Currently only supports password (no UI for key path).

---

## 6. Error Handling and Logging

### Logging
- **Location**: `~/.wp-deploy/logs/`
- **Components**: Separate loggers for: sftp, ssh, git, push, pull, config, db
- **Level**: INFO/ERROR with detailed messages

### Error Handling Patterns

**SFTP Methods** (lines 154-157 in sftp_service.py):
```python
except Exception as e:
    error_msg = f"Failed to upload {local_path}: {e}"
    self.logger.error(error_msg)
    return False, error_msg  # Returns tuple (success, message)
```

**Controllers** (lines 132-135 in push_controller.py):
```python
except Exception as e:
    error_msg = f"Push failed: {str(e)}"
    self.logger.error(error_msg)
    return False, error_msg, stats
```

### Connection Failures
- Paramiko exceptions caught and logged
- Returns error messages to UI for display
- Clean connection teardown even on error

---

## 7. Progress Tracking and UI Updates

### Progress Callback Pattern

**Controllers** (lines 83-84 in push_controller.py):
```python
if progress_callback:
    progress_callback(i + 1, total_files, f"Uploading {file_path}")
```

**SFTP** (lines 138-142 in sftp_service.py):
```python
def progress_wrapper(bytes_transferred, total_bytes):
    if progress_callback:
        progress_callback(bytes_transferred, total_bytes)

self.sftp_client.put(local_path, remote_path, callback=progress_wrapper)
```

**UI Thread Handling**:
- Operations run in background threads
- Progress callbacks update UI from threads
- Prevents GUI freezing during transfers

---

## 8. Summary Table

| Aspect | Implementation | Location |
|--------|---|---|
| **SSH Connection** | Paramiko SSHClient | ssh_service.py, sftp_service.py |
| **SFTP File Transfer** | Paramiko SFTPClient | sftp_service.py |
| **File Upload** | `sftp.put()` with progress | push_controller.py |
| **File Download** | `sftp.get()` with progress | pull_controller.py |
| **Changed Files Detection** | GitPython diff | git_service.py, push_controller.py |
| **Selective Download** | Date-based filtering | pull_controller.py, sftp_service.py |
| **Configuration Storage** | YAML + Keyring | config_service.py, ~/.wp-deploy/ |
| **Passwords** | System Keyring | config_service.py |
| **UI Framework** | Tkinter with sv_ttk theme | ui/ |
| **Site Configuration UI** | Tabbed dialog | site_dialog.py |
| **Progress Display** | Callback pattern + threading | main_window.py |
| **State Tracking** | JSON file | config_service.py, sync_state.json |
| **Logging** | Python logging | utils/logger.py |

---

## 9. Key Data Flows

### Initial Setup:
1. User creates site config via Site Dialog
2. SSH credentials stored in keyring
3. Database credentials (if any) also stored in keyring
4. YAML config saved to `~/.wp-deploy/sites.yaml`

### First Push:
1. Gets all tracked Git files
2. Filters by exclude_patterns
3. Uploads to remote via SFTP
4. Records commit hash as `last_pushed_commit`
5. Saves operation in sync_state.json

### Incremental Push:
1. Gets changed files since `last_pushed_commit`
2. Filters and uploads only changes
3. Updates `last_pushed_commit` to current HEAD

### Pull Operation:
1. User specifies date range
2. Lists remote files from include_paths within date range
3. Filters by exclude_patterns
4. Downloads changed files
5. Records operation in sync_state.json

---

## 10. Important Notes

- **No Native SSH Key Support in UI**: Currently only password auth in config dialog, but code supports key-based auth
- **Safe Defaults**: Excludes sensitive files (wp-config, .env, .git)
- **Database Sync**: Separate controllers handle WP-CLI-based database operations
- **macOS Optimized**: Special handling for focus management on macOS
- **Thread-Safe**: Uses threading to prevent UI freeze during operations
- **State Persistence**: All operations recorded for history and recovery


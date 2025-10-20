# WordPress Site Deployment Tool - Development Documentation

## Executive Summary

This document outlines the requirements, architecture, and implementation plan for a desktop tool that synchronizes WordPress sites between Local by Flywheel development environments and remote hosting platforms (Kinsta, etc.) using Git-based version tracking and SFTP file transfer.

---

## Table of Contents

1. [Requirements Analysis](#requirements-analysis)
2. [Technology Stack Recommendations](#technology-stack-recommendations)
3. [System Architecture](#system-architecture)
4. [Data Structures & Storage](#data-structures--storage)
5. [Core Features Specification](#core-features-specification)
6. [Implementation Plan](#implementation-plan)
7. [Security Considerations](#security-considerations)
8. [Testing Strategy](#testing-strategy)
9. [Future Enhancements](#future-enhancements)

---

## Requirements Analysis

### Functional Requirements

#### Push to Remote
- **FR-1**: Detect files changed since the last pushed commit in the Git repository
- **FR-2**: Transfer changed files to remote server via SFTP
- **FR-3**: Track and store the last successfully pushed commit hash
- **FR-4**: Maintain directory structure during transfer
- **FR-5**: Provide progress feedback during push operations
- **FR-6**: Handle failed transfers with rollback capability

#### Pull from Remote
- **FR-7**: Allow user to specify date range for file selection
- **FR-8**: Download files modified within the specified date range
- **FR-9**: Allow user to specify include paths (whitelist approach)
- **FR-10**: Ignore files/folders outside specified paths
- **FR-11**: Overwrite local files with remote versions
- **FR-12**: Provide progress feedback during pull operations

#### General
- **FR-13**: Support multiple site configurations (profiles)
- **FR-14**: Validate SFTP connections before operations
- **FR-15**: Provide detailed operation logs
- **FR-16**: Exclude database files from sync operations

### Non-Functional Requirements

- **NFR-1**: Cross-platform compatibility (macOS, Windows, Linux)
- **NFR-2**: Secure credential storage
- **NFR-3**: Resume interrupted transfers
- **NFR-4**: Handle large files (WordPress uploads, etc.)
- **NFR-5**: Intuitive GUI for non-technical users
- **NFR-6**: Performance: Handle sites with 10,000+ files

### Out of Scope (Phase 1)

- Database synchronization
- WordPress-specific migrations (URLs, serialized data)
- Conflict resolution (will overwrite)
- Real-time sync or file watching
- Version control integration beyond Git

---

## Technology Stack Recommendations

### Recommended: Python

**Rationale:**
- Excellent cross-platform support
- Rich ecosystem for required functionality
- Easy deployment with PyInstaller
- Strong SFTP and Git libraries
- Rapid development cycle

### Core Dependencies

```
# File Transfer
paramiko==3.4.0           # SFTP client
fabric==3.2.2             # High-level SSH/SFTP operations

# Git Operations
GitPython==3.1.40         # Git repository interaction

# GUI Framework (Choose One)
tkinter                   # Built-in, lightweight (RECOMMENDED for simplicity)
PyQt6==6.6.1             # Professional, feature-rich (alternative)
wxPython==4.2.1          # Native look, good cross-platform (alternative)

# Configuration & Storage
pyyaml==6.0.1            # Configuration files
keyring==24.3.0          # Secure credential storage

# Utilities
python-dateutil==2.8.2   # Date parsing
pathlib                  # Path manipulation (built-in)
logging                  # Logging (built-in)

# Packaging
pyinstaller==6.3.0       # Create standalone executables
```

### Alternative Technology Stacks (If Python Not Suitable)

#### Option 2: Node.js/Electron
- **Pros**: Modern web UI, familiar to web developers, great npm ecosystem
- **Cons**: Larger bundle size, more complexity
- **Key Libraries**: `ssh2-sftp-client`, `simple-git`, `electron`

#### Option 3: Go
- **Pros**: Single binary, fast, no runtime dependencies
- **Cons**: GUI less mature, steeper learning curve
- **Key Libraries**: `pkg/sftp`, `go-git`, `fyne` (GUI)

**Recommendation**: Stick with Python + tkinter for rapid development and ease of maintenance.

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      GUI Layer                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Push Panel   │  │ Pull Panel   │  │ Config Panel │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                   Controller Layer                      │
│  ┌──────────────────────────────────────────────────┐   │
│  │         DeploymentController                     │   │
│  │  - Orchestrate operations                        │   │
│  │  - Validate inputs                               │   │
│  │  - Handle errors                                 │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
┌──────────────┐  ┌─────────────┐  ┌──────────────┐
│  GitService  │  │ SFTPService │  │ ConfigService│
│              │  │             │  │              │
│ - Get diff   │  │ - Connect   │  │ - Load/Save  │
│ - Get commits│  │ - Upload    │  │ - Validate   │
│ - Get hash   │  │ - Download  │  │ - Encrypt    │
└──────────────┘  └─────────────┘  └──────────────┘
                         │
                         ▼
                  ┌─────────────┐
                  │ FileSystem  │
                  │  & Remote   │
                  └─────────────┘
```

### Component Descriptions

#### 1. GUI Layer (`ui/`)
Handles user interaction and displays feedback.

**Components:**
- `main_window.py`: Main application window
- `push_panel.py`: Push operation interface
- `pull_panel.py`: Pull operation interface
- `config_panel.py`: Site configuration management
- `progress_dialog.py`: Transfer progress display
- `log_viewer.py`: Operation log display

#### 2. Controller Layer (`controllers/`)
Business logic and operation orchestration.

**Components:**
- `deployment_controller.py`: Main controller
- `push_controller.py`: Push operation logic
- `pull_controller.py`: Pull operation logic

#### 3. Service Layer (`services/`)
Core functionality implementation.

**Components:**
- `git_service.py`: Git operations
- `sftp_service.py`: SFTP operations
- `config_service.py`: Configuration management
- `sync_state_service.py`: Track sync state

#### 4. Data Layer (`models/`)
Data structures and persistence.

**Components:**
- `site_config.py`: Site configuration model
- `sync_state.py`: Sync state model
- `transfer_log.py`: Operation log model

---

## Data Structures & Storage

### Site Configuration

**Storage**: `~/.wp-deploy/sites.yaml` (or `%APPDATA%\wp-deploy\sites.yaml` on Windows)

```yaml
sites:
  - id: "site-001"
    name: "My WordPress Site"
    local_path: "/Users/yourname/Local Sites/mysite/app/public"
    git_repo_path: "/Users/yourname/Local Sites/mysite/app/public"
    remote_host: "sftp.kinsta.com"
    remote_port: 22
    remote_path: "/www/mysite_123/public"
    remote_username: "mysite_123"
    # Password stored in system keyring
    last_pushed_commit: "a3f2b1c9e8d7f6a5b4c3d2e1"
    exclude_patterns:
      - "*.log"
      - "wp-config.php"
      - ".git/"
      - "node_modules/"
      - ".DS_Store"
    pull_include_paths:
      - "wp-content/uploads"
      - "wp-content/themes/my-theme"
      - "wp-content/plugins/my-plugin"
    created_at: "2025-01-15T10:30:00Z"
    updated_at: "2025-01-20T14:22:00Z"
```

### Sync State

**Storage**: `~/.wp-deploy/sync_state.json`

```json
{
  "site-001": {
    "last_push": {
      "timestamp": "2025-01-20T14:22:00Z",
      "commit_hash": "a3f2b1c9e8d7f6a5b4c3d2e1",
      "commit_message": "Update header styles",
      "files_pushed": 12,
      "bytes_transferred": 45678,
      "status": "success"
    },
    "last_pull": {
      "timestamp": "2025-01-18T09:15:00Z",
      "date_range_start": "2025-01-10T00:00:00Z",
      "date_range_end": "2025-01-17T23:59:59Z",
      "files_pulled": 8,
      "bytes_transferred": 1234567,
      "status": "success"
    }
  }
}
```

### Operation Log

**Storage**: `~/.wp-deploy/logs/operations.log`

```
2025-01-20 14:22:15 [INFO] [site-001] Starting push operation
2025-01-20 14:22:16 [INFO] [site-001] Git: Found 12 changed files since a3f2b1c
2025-01-20 14:22:16 [INFO] [site-001] SFTP: Connecting to sftp.kinsta.com:22
2025-01-20 14:22:17 [INFO] [site-001] SFTP: Connected successfully
2025-01-20 14:22:18 [INFO] [site-001] Uploading: wp-content/themes/my-theme/style.css
2025-01-20 14:22:19 [INFO] [site-001] Uploaded: wp-content/themes/my-theme/style.css (4.2 KB)
...
2025-01-20 14:22:45 [INFO] [site-001] Push completed successfully (12 files, 45.6 KB)
```

---

## Core Features Specification

### Feature 1: Push to Remote

#### Workflow

1. **User initiates push**
   - Select site from dropdown
   - Click "Push to Remote" button

2. **Pre-flight checks**
   - Verify Git repository exists
   - Verify local path exists
   - Test SFTP connection
   - Retrieve last pushed commit hash

3. **Determine files to push**
   ```python
   # Pseudo-code
   last_commit = get_last_pushed_commit(site_id)
   current_commit = get_current_head_commit(repo)

   if last_commit is None:
       # First push - get all tracked files
       files_to_push = get_all_tracked_files(repo)
   else:
       # Get diff between commits
       files_to_push = get_changed_files(repo, last_commit, current_commit)

   # Apply exclusion patterns
   files_to_push = filter_excluded_files(files_to_push, exclude_patterns)
   ```

4. **Upload files**
   - Create remote directories as needed
   - Upload each file via SFTP
   - Maintain local directory structure
   - Track progress (files/bytes)
   - Handle errors (retry logic)

5. **Update sync state**
   - Save current commit hash as last_pushed_commit
   - Update sync state JSON
   - Log operation details

6. **Display results**
   - Show success message
   - Display files pushed
   - Option to view detailed log

#### Error Handling

- **SFTP connection failure**: Show error, allow retry
- **File upload failure**: Log error, continue with remaining files, mark operation as partial success
- **Git repository not found**: Show error, require configuration fix
- **No changes to push**: Inform user, no operation performed

### Feature 2: Pull from Remote

#### Workflow

1. **User configures pull**
   - Select site from dropdown
   - Set date range (start date, end date)
   - Review/edit include paths in text area
   - Click "Pull from Remote" button

2. **Pre-flight checks**
   - Verify local path exists
   - Test SFTP connection
   - Validate date range
   - Validate include paths

3. **Determine files to pull**
   ```python
   # Pseudo-code
   all_remote_files = []

   # Recursively list files in each include path
   for include_path in site.pull_include_paths:
       remote_path = os.path.join(site.remote_path, include_path)
       files = sftp.listdir_recursive(remote_path)

       # Filter by modification date
       for file in files:
           file_stat = sftp.stat(file)
           file_mtime = datetime.fromtimestamp(file_stat.st_mtime)

           if date_range_start <= file_mtime <= date_range_end:
               all_remote_files.append(file)

   # Apply exclusion patterns
   files_to_pull = filter_excluded_files(all_remote_files, exclude_patterns)
   ```

4. **Download files**
   - Create local directories as needed
   - Download each file via SFTP
   - Overwrite local files
   - Track progress (files/bytes)
   - Handle errors

5. **Update sync state**
   - Save pull operation details
   - Update sync state JSON
   - Log operation details

6. **Display results**
   - Show success message
   - Display files pulled
   - Option to view detailed log

#### Date Range Behavior

- **Date range**: Inclusive of start and end dates
- **Timezone**: Use server timezone (or make configurable)
- **Date picker**: Provide GUI calendar widget
- **Quick options**: "Last 7 days", "Last 30 days", "Custom range"

#### Include Paths Configuration

```
User interface: Multi-line text area

Example input:
wp-content/uploads
wp-content/themes/my-theme
wp-content/plugins/my-plugin

Behavior:
- One path per line
- Paths relative to remote_path
- Empty lines ignored
- Paths are validated before pull
- Non-existent paths show warning but don't block operation
```

---

## Implementation Plan

### Phase 1: Core Infrastructure (Week 1-2)

#### Tasks
1. Set up project structure
2. Implement configuration management
   - YAML parser for site configs
   - Keyring integration for password storage
   - Config validation
3. Implement Git service
   - Connect to repository
   - Get current commit
   - Get commit diff
   - List tracked files
4. Implement SFTP service
   - Connection management
   - Upload file
   - Download file
   - Recursive directory listing
   - Get file stats

#### Deliverable
Working CLI tool that can:
- Connect to Git repo
- Connect to SFTP server
- Upload/download single files

### Phase 2: Push Feature (Week 3)

#### Tasks
1. Implement push controller
   - File change detection
   - Exclusion pattern matching
   - Upload orchestration
2. Add sync state tracking
3. Add error handling and retry logic
4. Add progress tracking
5. Write unit tests

#### Deliverable
Working CLI push command:
```bash
python deploy.py push --site my-site
```

### Phase 3: Pull Feature (Week 4)

#### Tasks
1. Implement pull controller
   - Remote file listing
   - Date range filtering
   - Include path filtering
2. Add download orchestration
3. Add progress tracking
4. Write unit tests

#### Deliverable
Working CLI pull command:
```bash
python deploy.py pull --site my-site --start-date 2025-01-01 --end-date 2025-01-15
```

### Phase 4: GUI Development (Week 5-6)

#### Tasks
1. Design GUI layout
2. Implement main window
3. Implement push panel
4. Implement pull panel
5. Implement config panel
6. Add progress dialogs
7. Add log viewer
8. Connect GUI to controllers

#### Deliverable
Functional desktop application with GUI

### Phase 5: Testing & Refinement (Week 7)

#### Tasks
1. Integration testing
2. User acceptance testing
3. Bug fixes
4. Performance optimization
5. Documentation
6. Packaging for distribution

#### Deliverable
Standalone executable (.app for macOS, .exe for Windows)

---

## Security Considerations

### Credential Storage

**Problem**: Storing SFTP passwords securely

**Solution**: Use system keyring
```python
import keyring

# Store password
keyring.set_password("wp-deploy", f"site-{site_id}", password)

# Retrieve password
password = keyring.get_password("wp-deploy", f"site-{site_id}")
```

**Fallback**: If keyring unavailable, use encrypted file with master password

### SSH Key Support

**Alternative to passwords**: Support SSH private keys
```python
# In site config
ssh_key_path: "/Users/yourname/.ssh/kinsta_rsa"

# In SFTP service
import paramiko
key = paramiko.RSAKey.from_private_key_file(ssh_key_path)
transport = paramiko.Transport((host, port))
transport.connect(username=username, pkey=key)
```

### File Permission Preservation

**Consideration**: WordPress files often require specific permissions

**Implementation**:
```python
# During upload, preserve local permissions
local_stat = os.stat(local_file)
sftp.put(local_file, remote_file)
sftp.chmod(remote_file, local_stat.st_mode)
```

### Secure Connection

**Requirements**:
- Use SFTP (not FTP)
- Verify host keys
- Support key-based authentication
- Encrypt config files

### WordPress-Specific Security

**Files to exclude by default**:
```
wp-config.php          # Database credentials
.htaccess              # Server config (could differ)
.env                   # Environment variables
*.sql                  # Database dumps
debug.log              # May contain sensitive info
error_log              # May contain sensitive info
```

---

## Testing Strategy

### Unit Tests

Test individual components in isolation.

```python
# tests/test_git_service.py
def test_get_changed_files():
    git_service = GitService("/path/to/repo")
    files = git_service.get_changed_files("abc123", "def456")
    assert len(files) > 0
    assert "wp-content/themes/style.css" in files

# tests/test_sftp_service.py
def test_upload_file(mock_sftp):
    sftp_service = SFTPService(mock_sftp)
    result = sftp_service.upload_file("/local/file.txt", "/remote/file.txt")
    assert result.success == True

# tests/test_config_service.py
def test_load_site_config():
    config_service = ConfigService()
    site = config_service.get_site("site-001")
    assert site.name == "My WordPress Site"
```

### Integration Tests

Test component interactions.

```python
# tests/integration/test_push_operation.py
def test_complete_push_workflow():
    # Setup: Create test repo, mock SFTP
    # Execute: Run push operation
    # Assert: Verify files uploaded, state updated
    pass
```

### Manual Testing Checklist

- [ ] Push with no previous push (first time)
- [ ] Push with changes since last push
- [ ] Push with no changes
- [ ] Push with SFTP connection failure
- [ ] Pull with valid date range
- [ ] Pull with no matching files
- [ ] Pull with include paths
- [ ] Multiple site configurations
- [ ] Password change/update
- [ ] Large file transfers (100MB+)
- [ ] Interrupted transfer resume

### Test Environment Setup

**Local Git Repository**:
```bash
mkdir -p test-site/wp-content/themes/test-theme
cd test-site
git init
echo "v1" > wp-content/themes/test-theme/style.css
git add .
git commit -m "Initial commit"
```

**Mock SFTP Server**:
Use `pytest-sftpserver` or Docker container with OpenSSH

```bash
docker run -d -p 2222:22 \
  -e USERNAME=testuser \
  -e PASSWORD=testpass \
  atmoz/sftp:latest \
  testuser:testpass:::wp-site
```

---

## Future Enhancements

### Phase 2 Features

1. **Database Synchronization**
   - Export/import database via WP-CLI
   - Search and replace for URLs
   - Handle serialized data

2. **Conflict Resolution**
   - Detect conflicts (local and remote both modified)
   - Three-way merge options
   - Backup before overwrite

3. **Real-time Sync**
   - File system watching
   - Auto-push on save
   - Configurable debounce

4. **Advanced Git Integration**
   - Automatic commit before push
   - Branch-specific configurations
   - Tag releases on successful push

5. **Backup & Rollback**
   - Create backup before push/pull
   - Rollback to previous state
   - Retention policy

6. **Multi-Environment Support**
   - Staging, production environments
   - Environment-specific configs
   - Promote staging to production

7. **Team Collaboration**
   - Shared site configurations
   - Lock mechanism (prevent simultaneous pushes)
   - Activity notifications

8. **WordPress-Specific Features**
   - Plugin/theme install via push
   - Activate/deactivate remotely
   - Clear caches after push
   - Integration with Kinsta API

9. **Advanced Filtering**
   - File size limits
   - File type filters
   - Gitignore-style patterns
   - Content-based filtering

10. **Reporting & Analytics**
    - Transfer history
    - Bandwidth usage
    - Most frequently changed files
    - Export reports

---

## Project Structure

```
wp-deploy/
├── main.py                      # Application entry point
├── requirements.txt             # Python dependencies
├── setup.py                     # Package configuration
├── README.md                    # User documentation
├── DEVELOPMENT_DOCUMENTATION.md # This file
│
├── src/
│   ├── __init__.py
│   │
│   ├── ui/                      # GUI components
│   │   ├── __init__.py
│   │   ├── main_window.py       # Main application window
│   │   ├── push_panel.py        # Push operation UI
│   │   ├── pull_panel.py        # Pull operation UI
│   │   ├── config_panel.py      # Configuration management UI
│   │   ├── progress_dialog.py   # Transfer progress display
│   │   └── log_viewer.py        # Operation log viewer
│   │
│   ├── controllers/             # Business logic
│   │   ├── __init__.py
│   │   ├── deployment_controller.py  # Main controller
│   │   ├── push_controller.py        # Push operations
│   │   └── pull_controller.py        # Pull operations
│   │
│   ├── services/                # Core services
│   │   ├── __init__.py
│   │   ├── git_service.py       # Git operations
│   │   ├── sftp_service.py      # SFTP operations
│   │   ├── config_service.py    # Configuration management
│   │   └── sync_state_service.py # Sync state tracking
│   │
│   ├── models/                  # Data models
│   │   ├── __init__.py
│   │   ├── site_config.py       # Site configuration
│   │   ├── sync_state.py        # Sync state
│   │   └── transfer_log.py      # Transfer log entry
│   │
│   └── utils/                   # Utility functions
│       ├── __init__.py
│       ├── logger.py            # Logging configuration
│       ├── validators.py        # Input validation
│       └── patterns.py          # Pattern matching (exclusions)
│
├── tests/                       # Test suite
│   ├── __init__.py
│   ├── test_git_service.py
│   ├── test_sftp_service.py
│   ├── test_config_service.py
│   ├── test_push_controller.py
│   ├── test_pull_controller.py
│   └── integration/
│       ├── __init__.py
│       └── test_push_pull_workflow.py
│
├── config/                      # Configuration templates
│   ├── sites.example.yaml       # Example site configuration
│   └── settings.yaml            # Application settings
│
├── docs/                        # Additional documentation
│   ├── USER_GUIDE.md
│   ├── INSTALLATION.md
│   └── TROUBLESHOOTING.md
│
└── build/                       # Build artifacts (created during packaging)
    ├── macos/
    ├── windows/
    └── linux/
```

---

## Getting Started with Development

### 1. Set Up Development Environment

```bash
# Create project directory
mkdir wp-deploy
cd wp-deploy

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Create requirements.txt
cat > requirements.txt << EOF
paramiko==3.4.0
GitPython==3.1.40
pyyaml==6.0.1
keyring==24.3.0
python-dateutil==2.8.2
pyinstaller==6.3.0
pytest==7.4.3
pytest-mock==3.12.0
EOF

# Install dependencies
pip install -r requirements.txt

# Create project structure
mkdir -p src/{ui,controllers,services,models,utils}
mkdir -p tests/integration
mkdir -p config docs
```

### 2. Create Initial Files

```bash
# Create __init__.py files
touch src/__init__.py
touch src/{ui,controllers,services,models,utils}/__init__.py
touch tests/__init__.py

# Create main entry point
touch main.py
```

### 3. Start with Core Service

Begin by implementing `git_service.py` - the foundation for push operations.

---

## CLI Interface (for testing before GUI)

```bash
# Configure a site
python main.py config add \
  --name "My Site" \
  --local "/Users/yourname/Local Sites/mysite/app/public" \
  --remote-host "sftp.kinsta.com" \
  --remote-path "/www/mysite_123/public" \
  --remote-user "mysite_123"

# List configured sites
python main.py config list

# Push to remote
python main.py push --site mysite

# Pull from remote
python main.py pull --site mysite \
  --start-date "2025-01-01" \
  --end-date "2025-01-15" \
  --include-paths "wp-content/uploads,wp-content/themes/my-theme"

# View logs
python main.py logs --site mysite --operation push
```

---

## Common WordPress Exclude Patterns

```yaml
exclude_patterns:
  # Version control
  - ".git/"
  - ".gitignore"
  - ".svn/"

  # Dependencies
  - "node_modules/"
  - "vendor/"
  - "bower_components/"

  # Build artifacts
  - "dist/"
  - "build/"
  - "*.map"

  # WordPress specific
  - "wp-config.php"
  - "wp-config-local.php"
  - ".htaccess"
  - "php.ini"

  # Caches and logs
  - "*.log"
  - "wp-content/cache/"
  - "wp-content/w3tc-config/"
  - "wp-content/et-cache/"

  # Backups
  - "*.sql"
  - "*.sql.gz"
  - "backups/"

  # OS files
  - ".DS_Store"
  - "Thumbs.db"
  - "desktop.ini"

  # IDE files
  - ".idea/"
  - ".vscode/"
  - "*.sublime-*"

  # Local development
  - "local-config.php"
  - ".env"
  - ".env.local"
```

---

## Kinsta-Specific Considerations

### SFTP Details

Kinsta provides SFTP access with these characteristics:
- **Host**: Typically `sftp.kinsta.com` or site-specific
- **Port**: 22 (standard)
- **Username**: Site-specific (e.g., `yoursite_123`)
- **Password**: Set in MyKinsta dashboard
- **Path**: Usually `/www/yoursite_123/public`

### Kinsta Directory Structure

```
/www/yoursite_123/
├── public/                  # Web root (DocumentRoot)
│   ├── wp-admin/
│   ├── wp-content/
│   ├── wp-includes/
│   └── index.php
├── logs/                    # Log files (if accessible)
└── private/                 # Non-public files
```

### Important Notes

1. **wp-config.php**: Kinsta manages this file, do NOT overwrite
2. **Object Cache**: Kinsta uses Redis, may need cache clearing
3. **CDN**: Consider CDN cache invalidation after push
4. **Staging**: Kinsta offers staging environments (future enhancement)

---

## Risk Assessment & Mitigation

### Risk 1: Data Loss

**Scenario**: Accidental overwrite of important files

**Mitigation**:
- Implement dry-run mode (show what would be changed)
- Create backups before operations
- Confirmation dialog for destructive operations
- Exclude critical files by default

### Risk 2: Partial Transfer

**Scenario**: Network interruption during transfer

**Mitigation**:
- Implement transfer resume capability
- Track transferred files
- Verify file integrity (checksums)
- Allow retry of failed files

### Risk 3: Credential Exposure

**Scenario**: Passwords leaked in logs or config files

**Mitigation**:
- Use system keyring for passwords
- Prefer SSH keys over passwords
- Never log credentials
- Encrypt config files

### Risk 4: Site Downtime

**Scenario**: Push breaks live site

**Mitigation**:
- Test push on staging first (future feature)
- Implement rollback capability
- Atomic operations where possible
- Health check after push (future feature)

### Risk 5: Performance Impact

**Scenario**: Large sync causes timeout or memory issues

**Mitigation**:
- Streaming file transfers (don't load entire files in memory)
- Batch operations with pause between
- Configurable timeout settings
- Progress indication for long operations

---

## Success Metrics

### Phase 1 Success Criteria

- [ ] Successfully push files from local to remote
- [ ] Successfully pull files from remote to local
- [ ] No data loss in test scenarios
- [ ] Configuration persists between sessions
- [ ] Operations complete in reasonable time (< 5 min for 1000 files)

### User Satisfaction Metrics

- Time saved vs manual SFTP (target: 80% reduction)
- Error rate (target: < 1% failed transfers)
- Learning curve (target: < 15 min to first successful push)
- User feedback score (target: 4.5/5)

---

## Appendix A: Example Workflows

### Workflow 1: Daily Development Push

1. Developer makes changes to theme files locally
2. Commits changes to Git: `git commit -m "Update header styles"`
3. Opens wp-deploy tool
4. Selects site "Production"
5. Clicks "Push to Remote"
6. Tool identifies 5 changed files
7. Shows preview: "5 files will be uploaded (12.3 KB)"
8. Developer confirms
9. Files uploaded via SFTP
10. Success notification: "Push complete (5 files, 12.3 KB, 8s)"

### Workflow 2: Pull Recent Uploads

1. Client uploads images via WordPress admin on live site
2. Developer needs to download for local testing
3. Opens wp-deploy tool
4. Selects site "Production"
5. Goes to Pull tab
6. Sets date range: Last 7 days
7. Include paths: `wp-content/uploads`
8. Clicks "Pull from Remote"
9. Tool finds 23 new images
10. Shows preview: "23 files will be downloaded (4.5 MB)"
11. Developer confirms
12. Files downloaded via SFTP
13. Success notification: "Pull complete (23 files, 4.5 MB, 45s)"

### Workflow 3: First-Time Site Setup

1. Developer wants to add existing site to tool
2. Opens wp-deploy tool
3. Goes to Configuration tab
4. Clicks "Add Site"
5. Fills in form:
   - Name: My Client Site
   - Local Path: [Browse] /Users/yourname/Local Sites/clientsite/app/public
   - Git Repo: [Same as Local Path]
   - Remote Host: sftp.kinsta.com
   - Remote Port: 22
   - Remote Path: /www/clientsite_456/public
   - Remote Username: clientsite_456
   - Remote Password: [Secure input]
6. Clicks "Test Connection"
7. Success: "SFTP connection successful"
8. Sets exclude patterns (uses defaults)
9. Sets pull include paths:
   ```
   wp-content/uploads
   wp-content/themes/client-theme
   ```
10. Clicks "Save Site"
11. Site now available for push/pull operations

---

## Appendix B: Troubleshooting Guide

### Issue: "Git repository not found"

**Cause**: Local path is not a Git repository

**Solution**:
1. Verify Git repo exists: `cd /path/to/site && git status`
2. If not, initialize: `git init`
3. Or, update site configuration with correct Git repo path

### Issue: "SFTP connection failed"

**Causes & Solutions**:

1. **Wrong credentials**: Verify username/password in Kinsta dashboard
2. **Wrong host**: Check SFTP host in Kinsta (may be site-specific)
3. **Firewall**: Allow port 22 outbound
4. **IP whitelist**: Add your IP to Kinsta's IP allowlist if enabled

### Issue: "No files to push"

**Cause**: No changes detected since last push

**Solutions**:
1. Make changes and commit: `git add . && git commit -m "Changes"`
2. Or, reset last pushed commit to force re-push (advanced)

### Issue: "Permission denied uploading file"

**Cause**: SFTP user lacks write permissions on remote path

**Solution**:
1. Verify remote path is correct
2. Contact hosting support to verify SFTP permissions
3. Check file/directory ownership on server

### Issue: "Transfer very slow"

**Causes & Solutions**:

1. **Large files**: Exclude large files from sync, handle separately
2. **Network**: Check internet connection speed
3. **Server**: Check hosting server status
4. **Many small files**: Consider compression (future feature)

---

## Appendix C: Resources

### Documentation

- **Paramiko**: https://docs.paramiko.org/
- **GitPython**: https://gitpython.readthedocs.io/
- **Tkinter**: https://docs.python.org/3/library/tkinter.html
- **Keyring**: https://keyring.readthedocs.io/
- **PyYAML**: https://pyyaml.org/wiki/PyYAMLDocumentation

### Kinsta Resources

- **SFTP Access**: https://kinsta.com/knowledgebase/how-to-use-sftp/
- **File Structure**: https://kinsta.com/knowledgebase/wordpress-files/
- **Best Practices**: https://kinsta.com/blog/wordpress-deployment/

### Local by Flywheel

- **Directory Structure**: `~/Local Sites/[site-name]/app/public`
- **Local Config**: `wp-config-local.php` used for local settings
- **Git Integration**: Manual setup required

---

## Conclusion

This document provides a comprehensive blueprint for developing the WordPress deployment tool. The recommended approach is:

1. **Start Simple**: Build CLI version with push functionality first
2. **Iterate**: Add pull functionality, then GUI
3. **Test Thoroughly**: Use test WordPress site before production
4. **Deploy**: Package as standalone executable for easy distribution

The Python-based approach with Tkinter GUI offers the best balance of:
- Development speed
- Cross-platform compatibility
- Maintainability
- Feature completeness

Estimated development time for Phase 1 (functional CLI tool): **2-3 weeks**
Estimated development time for complete GUI application: **6-7 weeks**

---

**Document Version**: 1.0
**Last Updated**: January 2025
**Author**: Development Documentation for WordPress Deployment Tool

# SSH/SFTP Deployment Architecture Diagrams

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          WordPress Deployment Tool                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌─────────────────────┐                    ┌──────────────────────────┐   │
│  │   Tkinter GUI       │                    │   Configuration Layer    │   │
│  │ ───────────────────  │                    │ ──────────────────────── │   │
│  │ • main_window       │ ◄──────────────────► │ • config_service       │   │
│  │ • site_dialog       │                    │ • site_config          │   │
│  │ • db_dialog         │                    │ • database_config      │   │
│  │ • log_viewer        │                    └──────────────────────────┘   │
│  └─────────────────────┘                                                   │
│           ▲                                                                 │
│           │                                                                 │
│           ▼                                                                 │
│  ┌─────────────────────┐                                                   │
│  │  Controllers        │                                                   │
│  │ ──────────────────  │                                                   │
│  │ • push_controller   │                                                   │
│  │ • pull_controller   │                                                   │
│  │ • db_push_ctrl      │                                                   │
│  │ • db_pull_ctrl      │                                                   │
│  └─────────────────────┘                                                   │
│           ▲                                                                 │
│           │                                                                 │
│           ▼                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │              Service Layer (Business Logic)                         │   │
│  │  ───────────────────────────────────────────────────────────────   │   │
│  │  ┌──────────────┐  ┌─────────────┐  ┌──────────────┐             │   │
│  │  │ SFTP Service │  │ SSH Service │  │ Git Service  │             │   │
│  │  └──────────────┘  └─────────────┘  └──────────────┘             │   │
│  │  (Paramiko)        (Paramiko)       (GitPython)                   │   │
│  │                                                                    │   │
│  │  ┌──────────────────────────────────────────────────────────┐   │   │
│  │  │ Database Service (WP-CLI based)                          │   │   │
│  │  │ • Local DB operations                                    │   │   │
│  │  │ • Remote DB operations (via SSH)                         │   │   │
│  │  └──────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│           ▲                                                                 │
│           │                                                                 │
│           ▼                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    Storage Layer                                    │   │
│  │  ───────────────────────────────────────────────────────────────   │   │
│  │  ~/.wp-deploy/                                                      │   │
│  │  ├── sites.yaml              (Site configurations)                  │   │
│  │  ├── sync_state.json         (Operation history)                   │   │
│  │  └── logs/                   (Log files)                           │   │
│  │                                                                     │   │
│  │  OS Keyring (System Credentials)                                   │   │
│  │  ├── SSH Passwords                                                 │   │
│  │  ├── Database Passwords                                            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                               │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ (SSH/SFTP over Port 22)
                                    │
                                    ▼
                    ┌─────────────────────────────┐
                    │   Remote Server             │
                    │ ─────────────────────────── │
                    │ • WordPress Installation    │
                    │ • Database Server           │
                    │ • WP-CLI (if available)     │
                    └─────────────────────────────┘
```

---

## Push Operation Flow

```
User clicks "Push"
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ PushController.push(site_id)                                    │
└─────────────────────────────────────────────────────────────────┘
    │
    ├──► ConfigService.get_site(site_id)
    │        └──► Load from ~/.wp-deploy/sites.yaml
    │
    ├──► ConfigService.get_password(site_id)
    │        └──► Retrieve from OS keyring
    │
    ├──► GitService.get_changed_files(last_commit, HEAD)
    │    [OR get_all_tracked_files() if first push]
    │        └──► Use GitPython to get diff
    │
    ├──► filter_files(files, exclude_patterns)
    │        └──► Apply pattern matching (fnmatch)
    │
    ├──► SFTPService.connect(host, port, user, password)
    │        └──► Paramiko SSH connection
    │
    ├──► For each file in files_to_push:
    │    │
    │    ├──► Check if local file exists
    │    │
    │    ├──► mkdir_recursive(remote_dir)
    │    │        └──► Create nested remote directories
    │    │
    │    ├──► upload_file(local_path, remote_path)
    │    │    │
    │    │    ├──► sftp.put() with progress callback
    │    │    ├──► Preserve file permissions (chmod)
    │    │    └──► Update UI with progress
    │    │
    │    └──► Record in stats: files_pushed++, bytes_transferred += filesize
    │
    ├──► SFTPService.disconnect()
    │        └──► Close SFTP and SSH connections
    │
    ├──► ConfigService.update_last_pushed_commit(site_id, current_commit)
    │        └──► Update in sites.yaml
    │
    ├──► ConfigService.update_sync_state(site_id, OperationState)
    │        └──► Record in sync_state.json:
    │            ├── timestamp: ISO datetime
    │            ├── status: "success" or "partial"
    │            ├── files_count: number uploaded
    │            ├── bytes_transferred: total bytes
    │            ├── commit_hash: current HEAD
    │            └── commit_message: HEAD message
    │
    └──► Return (success, message, stats)
            │
            ▼
        Display success message and stats in UI
```

---

## Pull Operation Flow

```
User clicks "Pull"
    │
    ▼
Display Date Picker Dialog
    │
    ▼ [User selects start_date and end_date]
    │
┌─────────────────────────────────────────────────────────────────┐
│ PullController.pull(site_id, start_date, end_date)             │
└─────────────────────────────────────────────────────────────────┘
    │
    ├──► ConfigService.get_site(site_id)
    │        └──► Load from ~/.wp-deploy/sites.yaml
    │
    ├──► ConfigService.get_password(site_id)
    │        └──► Retrieve from OS keyring
    │
    ├──► SFTPService.connect(host, port, user, password)
    │        └──► Paramiko SSH connection
    │
    ├──► For each include_path in pull_include_paths:
    │    │    (e.g., "wp-content/uploads", "wp-content/themes/my-theme")
    │    │
    │    ├──► Check if remote_path exists
    │    │
    │    └──► list_files_recursive(remote_path, start_date, end_date)
    │         │
    │         ├──► SFTP listdir_attr() for recursive scan
    │         ├──► Filter by modification date (start_date < mtime < end_date)
    │         └──► Return [(filepath, mod_datetime), ...]
    │
    ├──► Collect all_files from all include_paths
    │
    ├──► filter_files(file_paths, exclude_patterns)
    │        └──► Apply pattern matching
    │
    ├──► For each file in filtered_files:
    │    │
    │    ├──► Calculate local_path:
    │    │        local_path = site.local_path + rel_path
    │    │
    │    ├──► os.makedirs(local_dir, exist_ok=True)
    │    │        └──► Create local directories as needed
    │    │
    │    ├──► download_file(remote_path, local_path)
    │    │    │
    │    │    └──► sftp.get() with progress callback
    │    │
    │    └──► Record in stats: files_pulled++, bytes_transferred += filesize
    │
    ├──► SFTPService.disconnect()
    │        └──► Close SFTP and SSH connections
    │
    ├──► ConfigService.update_sync_state(site_id, OperationState)
    │        └──► Record in sync_state.json:
    │            ├── timestamp: ISO datetime
    │            ├── status: "success" or "partial"
    │            ├── files_count: number downloaded
    │            ├── bytes_transferred: total bytes
    │            ├── date_range_start: start_date ISO
    │            └── date_range_end: end_date ISO
    │
    └──► Return (success, message, stats)
            │
            ▼
        Display success message and stats in UI
```

---

## Configuration Storage Structure

```
~/.wp-deploy/
│
├── sites.yaml
│   └── Contains:
│       - sites:
│           - id: abc12345
│             name: "My Site"
│             local_path: /path/to/local
│             git_repo_path: /path/to/git
│             remote_host: example.com
│             remote_port: 22
│             remote_path: /var/www/html
│             remote_username: siteuser
│             site_url: https://example.com
│             exclude_patterns:
│               - "*.log"
│               - "wp-config.php"
│               - ".git/"
│             pull_include_paths:
│               - "wp-content/uploads"
│               - "wp-content/themes/custom"
│             last_pushed_commit: abc123def456...
│             database_config:
│               - local_db_name: mysite_db
│               - local_db_host: localhost
│               - local_db_port: 3306
│               - local_db_user: root
│               - ...
│
├── sync_state.json
│   └── Contains:
│       {
│         "abc12345": {
│           "last_push": {
│             "timestamp": "2024-10-20T15:30:00",
│             "status": "success",
│             "files_count": 42,
│             "bytes_transferred": 2048000,
│             "commit_hash": "abc123def456...",
│             "commit_message": "Update theme files"
│           },
│           "last_pull": {
│             "timestamp": "2024-10-20T14:20:00",
│             "status": "success",
│             "files_count": 128,
│             "bytes_transferred": 5242880,
│             "date_range_start": "2024-10-18T00:00:00",
│             "date_range_end": "2024-10-20T00:00:00"
│           },
│           "last_db_push": {...},
│           "last_db_pull": {...}
│         }
│       }
│
└── logs/
    ├── sftp.log
    ├── ssh.log
    ├── git.log
    ├── push.log
    ├── pull.log
    └── config.log
```

---

## Credentials Storage (OS Keyring)

```
Operating System Keyring Storage:

macOS Keychain:
├── Service: wp-deploy
│   ├── Account: site-abc12345  → Value: [ssh_password]
│   └── (One entry per configured site)
│
└── Service: wp-deploy-db
    ├── Account: abc12345_local  → Value: [local_db_password]
    └── Account: abc12345_remote → Value: [remote_db_password]

Windows Credential Manager:
├── Generic Credential: wp-deploy:site-abc12345 → [ssh_password]
├── Generic Credential: wp-deploy-db:abc12345_local → [local_db_password]
└── Generic Credential: wp-deploy-db:abc12345_remote → [remote_db_password]

Linux Secret Service:
├── Collection: wp-deploy
│   ├── Item: site-abc12345 → [ssh_password]
│   └── (Similar structure to others)
└── Collection: wp-deploy-db
    ├── Item: abc12345_local → [local_db_password]
    └── Item: abc12345_remote → [remote_db_password]
```

---

## SSH/SFTP Connection Lifecycle

```
┌─────────────────────────────────────────────────────────────┐
│           SFTP Service Connection Lifecycle                 │
└─────────────────────────────────────────────────────────────┘

INITIALIZATION:
┌──────────────────────────────────┐
│ SFTPService(host, port, user,    │
│             password/key_path)   │
└──────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────────────┐
│ Decision: Authentication Method                  │
├──────────────────────────────────────────────────┤
│ ┌──────────────────┐    ┌──────────────────────┐│
│ │ Password Auth    │    │ SSH Key Auth         ││
│ ├──────────────────┤    ├──────────────────────┤│
│ │ ssh_client.      │    │ ssh_client.          ││
│ │ connect(         │    │ connect(             ││
│ │   host=host,     │    │   host=host,         ││
│ │   port=port,     │    │   port=port,         ││
│ │   username=user, │    │   username=user,     ││
│ │   password=pwd   │    │   key_filename=key   ││
│ │ )                │    │ )                    ││
│ └──────────────────┘    └──────────────────────┘│
└──────────────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────────────┐
│ SSH Connection Established                       │
│ • Paramiko SSHClient ready                      │
│ • Host key policy: AutoAddPolicy()              │
└──────────────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────────────┐
│ Open SFTP Channel                                │
│ sftp_client = ssh_client.open_sftp()             │
└──────────────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────────────┐
│ READY FOR OPERATIONS:                            │
├──────────────────────────────────────────────────┤
│ • upload_file()                                 │
│ • download_file()                               │
│ • list_files_recursive()                        │
│ • mkdir_recursive()                             │
│ • path_exists()                                 │
└──────────────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────────────┐
│ CLEANUP (on success or error):                   │
├──────────────────────────────────────────────────┤
│ sftp_client.close()                             │
│ ssh_client.close()                              │
└──────────────────────────────────────────────────┘

CONTEXT MANAGER SUPPORT:
┌──────────────────────────────────────────────────┐
│ with SFTPService(host, port, user, pwd) as sftp: │
│     sftp.upload_file(local, remote)             │
│ # Auto-disconnects on context exit              │
└──────────────────────────────────────────────────┘
```

---

## File Filtering Pattern Matching Logic

```
┌─────────────────────────────────────────────────────────┐
│ File Filtering: should_exclude(file_path, patterns)     │
└─────────────────────────────────────────────────────────┘

Input: file_path = "wp-content/uploads/2024/10/image.log"
       exclude_patterns = ["*.log", "wp-config.php", ".git/", ...]

    │
    ▼
┌───────────────────────────────────────────────────────────┐
│ For each pattern in exclude_patterns:                    │
└───────────────────────────────────────────────────────────┘
    │
    ├─► Pattern: "*.log"
    │   │
    │   └─► fnmatch(file_path, pattern)
    │       fnmatch("wp-content/uploads/2024/10/image.log", "*.log")
    │       Result: FALSE
    │       │
    │       ├─► Check path directory matching: /{pattern}/ in /{file_path}/
    │       │   Result: FALSE
    │       │
    │       └─► Check filename matching:
    │           fnmatch(basename, pattern)
    │           fnmatch("image.log", "*.log")
    │           Result: TRUE ──► EXCLUDE FILE
    │
    └─► (short-circuit: file is excluded)

OUTPUT: should_exclude() returns TRUE
        └─► File "wp-content/uploads/2024/10/image.log" 
            will NOT be transferred


DEFAULT EXCLUDE PATTERNS:
─────────────────────────
*.log                  ◄─── All log files
wp-config.php          ◄─── WordPress main config
wp-config-local.php    ◄─── Local overrides
.git/                  ◄─── Git repository
node_modules/          ◄─── Node packages
.DS_Store              ◄─── macOS metadata
.htaccess              ◄─── Apache config
*.sql                  ◄─── SQL backup files
*.sql.gz               ◄─── Compressed SQL
.env                   ◄─── Environment variables
.env.local             ◄─── Local environment
```

---

## UI Component Hierarchy

```
┌──────────────────────────────────────────────────────────┐
│              MainWindow (root)                            │
│              1100x700 px                                  │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  ┌────────────────────────────────────────────────────┐  │
│  │ Notebook (Tabs)                                    │  │
│  ├────────────────────────────────────────────────────┤  │
│  │                                                     │  │
│  │ ┌─ Sites Tab ─────────────────────────────────────┐│  │
│  │ │ • Site list (Treeview)                          ││  │
│  │ │ • [+ Add Site] [Edit] [Delete]                  ││  │
│  │ │ • [Push] [Pull] [Database] buttons              ││  │
│  │ │ • Progress display area                          ││  │
│  │ └─────────────────────────────────────────────────┘│  │
│  │                                                     │  │
│  │ ┌─ Database Tab ──────────────────────────────────┐│  │
│  │ │ • Database sync interface                       ││  │
│  │ │ • [Push DB] [Pull DB] buttons                   ││  │
│  │ │ • Status display                                ││  │
│  │ └─────────────────────────────────────────────────┘│  │
│  │                                                     │  │
│  │ ┌─ Logs Tab ──────────────────────────────────────┐│  │
│  │ │ • Log viewer (scrolled text)                    ││  │
│  │ │ • [Clear] [Export] buttons                      ││  │
│  │ └─────────────────────────────────────────────────┘│  │
│  │                                                     │  │
│  │ ┌─ Settings Tab ──────────────────────────────────┐│  │
│  │ │ • Application preferences                       ││  │
│  │ │ • Theme selector                                ││  │
│  │ │ • Logging level                                 ││  │
│  │ └─────────────────────────────────────────────────┘│  │
│  │                                                     │  │
│  └────────────────────────────────────────────────────┘  │
│                                                           │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│         SiteDialog (Modal Dialog)                         │
│         950x750 px                                        │
├──────────────────────────────────────────────────────────┤
│                                                           │
│ ┌─ Basic Information ─────────────────────────────────┐  │
│ │ • Site Name:        [Input]                         │  │
│ │ • Local Path:       [Input] [Browse]                │  │
│ │ • Git Repo Path:    [Input] [Browse] [Same as]      │  │
│ │   Status: ✓ Git repository                          │  │
│ └─────────────────────────────────────────────────────┘  │
│                                                           │
│ ┌─ Notebook (Tabs) ───────────────────────────────────┐  │
│ │                                                     │  │
│ │ ┌─ SSH/SFTP ──────────────────────────────────────┐│  │
│ │ │ Remote Server:                                  ││  │
│ │ │   Host:          [Input]                        ││  │
│ │ │   Port:          [22]                           ││  │
│ │ │   Username:      [Input]                        ││  │
│ │ │   Password:      [*****]                        ││  │
│ │ │   Remote Path:   [Input]                        ││  │
│ │ │   Site URL:      [Input]                        ││  │
│ │ │                                                 ││  │
│ │ │ Pull Include Paths:                             ││  │
│ │ │ [ScrolledText] 6 rows                           ││  │
│ │ └─────────────────────────────────────────────────┘│  │
│ │                                                     │  │
│ │ ┌─ Database ──────────────────────────────────────┐│  │
│ │ │   ┌─ Local Database ───────────┐                ││  │
│ │ │   │ DB Name:    [Input]         │                ││  │
│ │ │   │ Host:       [localhost]     │                ││  │
│ │ │   │ Port:       [3306]          │                ││  │
│ │ │   │ User:       [root]          │                ││  │
│ │ │   │ Password:   [*****]         │                ││  │
│ │ │   │ [Auto-detect]               │                ││  │
│ │ │   └─────────────────────────────┘                ││  │
│ │ │                                                  ││  │
│ │ │   ┌─ Remote Database ──────────┐                ││  │
│ │ │   │ DB Name:    [Input]         │                ││  │
│ │ │   │ Host:       [localhost]     │                ││  │
│ │ │   │ Port:       [3306]          │                ││  │
│ │ │   │ User:       [Input]         │                ││  │
│ │ │   │ Password:   [*****]         │                ││  │
│ │ │   │ [Auto-detect]               │                ││  │
│ │ │   └─────────────────────────────┘                ││  │
│ │ │                                                  ││  │
│ │ │   ┌─ Advanced Options ─────────┐                ││  │
│ │ │   │ Exclude Tables:             │                ││  │
│ │ │   │ [ScrolledText] 6 rows       │                ││  │
│ │ │   │ ☑ Backup before import     │                ││  │
│ │ │   │ ☑ Require confirmation     │                ││  │
│ │ │   └─────────────────────────────┘                ││  │
│ │ │                                                  ││  │
│ │ │ [Test Local] [Test Remote]                      ││  │
│ │ └──────────────────────────────────────────────────┘│  │
│ │                                                     │  │
│ └─────────────────────────────────────────────────────┘  │
│                                                           │
│ [Save Site] [Cancel]                                     │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

---

## Threading Model for Operations

```
Main Thread (UI)
    │
    ├─► User clicks "Push" button
    │       │
    │       └──► Button event handler
    │           ├─► Validate inputs
    │           ├─► Show ProgressDialog
    │           └─► Start background thread:
    │               │
    │               └─► def push_thread():
    │                   └──► push_controller.push(
    │                       site_id,
    │                       progress_callback=update_ui
    │                       )
    │
    └─► Background Thread (Push Operation)
            │
            ├─► Perform SFTP operations
            │   • Connect
            │   • Upload files
            │   • Call progress_callback(current, total, msg)
            │   • Disconnect
            │
            └─► Call main thread callback:
                self.root.after(0, lambda: update_ui_result(stats))
                    │
                    └──► Main thread updates UI
```


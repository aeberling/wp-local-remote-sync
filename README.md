# WordPress Deployment Tool

A desktop application for synchronizing WordPress sites between Local by Flywheel and remote hosting platforms (Kinsta, etc.) using Git-based version tracking and SFTP file transfer.

## Features

- **Push to Remote**: Upload changed files based on Git commits
- **Pull from Remote**: Download files based on date ranges and specific paths
- **Git Integration**: Tracks commits to identify which files have changed
- **Secure Credentials**: Passwords stored in system keyring
- **Selective Sync**: Configure which paths to include/exclude
- **Progress Tracking**: Real-time feedback during transfers
- **Multiple Sites**: Manage configurations for multiple WordPress sites

## Installation

### Requirements

- Python 3.8 or higher
- Git installed and configured
- SFTP access to your remote server

### Setup

1. **Clone or download this repository**

2. **Create a virtual environment** (recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Starting the Application

```bash
python main.py
```

This will launch the GUI application.

### First-Time Setup

1. **Add a Site Configuration**:
   - Go to the **Configuration** tab
   - Click **Add Site**
   - Fill in the form:
     - **Site Name**: A friendly name for your site
     - **Local Path**: Path to your WordPress installation (e.g., `/Users/yourname/Local Sites/mysite/app/public`)
     - **Git Repo Path**: Path to Git repository (usually same as Local Path)
     - **Host**: SFTP server hostname (e.g., `sftp.kinsta.com`)
     - **Port**: Usually `22`
     - **Username**: Your SFTP username
     - **Password**: Your SFTP password (stored securely in system keyring)
     - **Remote Path**: Path on remote server (e.g., `/www/mysite_123/public`)
     - **Pull Include Paths**: Paths to sync when pulling (one per line)
       ```
       wp-content/uploads
       wp-content/themes/my-theme
       wp-content/plugins/my-plugin
       ```
   - Click **Save**

2. **Test the Connection**:
   - Select your site in the Configuration tab
   - Click **Test Connection**
   - Verify the connection is successful

### Push to Remote

1. Make changes to your local WordPress files
2. Commit changes to Git:
   ```bash
   git add .
   git commit -m "Update theme styles"
   ```
3. Open the deployment tool
4. Go to **Push to Remote** tab
5. Select your site from the dropdown
6. Click **Preview Files** to see what will be uploaded
7. Click **Push to Remote** to upload files
8. Confirm the operation

The tool will:
- Compare the current commit with the last pushed commit
- Upload only changed files
- Update the last pushed commit reference

### Pull from Remote

1. Open the deployment tool
2. Go to **Pull from Remote** tab
3. Select your site from the dropdown
4. Set the date range:
   - Use the quick buttons: "Last 7 Days" or "Last 30 Days"
   - Or enter custom dates in YYYY-MM-DD format
5. Review/edit the include paths (will use site defaults if not specified)
6. Click **Preview Files** to see what will be downloaded
7. Click **Pull from Remote** to download files
8. Confirm the operation

The tool will:
- Find all files in the specified paths modified within the date range
- Download and overwrite local files
- Create directories as needed

## Configuration Files

Configuration files are stored in your home directory:

- **macOS/Linux**: `~/.wp-deploy/`
- **Windows**: `%APPDATA%\wp-deploy\`

Files:
- `sites.yaml` - Site configurations
- `sync_state.json` - Sync state tracking
- `logs/operations.log` - Operation logs

## Exclude Patterns

By default, these files/patterns are excluded from sync:

```
*.log
wp-config.php
wp-config-local.php
.git/
node_modules/
.DS_Store
.htaccess
*.sql
*.sql.gz
.env
.env.local
```

## Troubleshooting

### "Git repository not found"

Make sure your Git Repo Path is correct and contains a valid Git repository:
```bash
cd /path/to/your/site
git status
```

### "SFTP connection failed"

1. Verify your SFTP credentials in the hosting dashboard
2. Check that your firewall allows outbound connections on port 22
3. Ensure your IP is whitelisted (if required by your host)

### "No files to push"

Make sure you've committed your changes to Git:
```bash
git add .
git commit -m "Your commit message"
```

### "Password not found in keyring"

The password storage failed. Try:
1. Edit the site configuration
2. Re-enter the password
3. Save the configuration

## Logs

View detailed logs at:
- **macOS/Linux**: `~/.wp-deploy/logs/operations.log`
- **Windows**: `%APPDATA%\wp-deploy\logs\operations.log`

## Security Notes

- Passwords are stored in your system's keyring (Keychain on macOS, Credential Manager on Windows)
- SFTP connections use secure protocols
- Sensitive files (wp-config.php, .env) are excluded by default
- All operations are logged for audit purposes

## Workflow Examples

### Daily Development Workflow

1. Work on your local WordPress site
2. Commit changes: `git commit -m "Update header styles"`
3. Open deployment tool
4. Push changes to remote server
5. Changes go live immediately

### Pulling Client Uploads

1. Client uploads images via WordPress admin on live site
2. Open deployment tool
3. Pull last 7 days from `wp-content/uploads`
4. Images now available locally for testing

## Limitations (Current Version)

- Database synchronization not included (files only)
- No conflict resolution (last write wins)
- No automatic rollback on errors
- Large files (>100MB) may timeout depending on connection

## Future Enhancements

See `DEVELOPMENT_DOCUMENTATION.md` for planned features:
- Database synchronization
- Conflict resolution
- Automatic backups
- Real-time sync
- Kinsta API integration

## Support

For issues or questions, refer to:
- `DEVELOPMENT_DOCUMENTATION.md` - Technical details
- `~/.wp-deploy/logs/operations.log` - Operation logs

## License

This tool is provided as-is for personal and commercial use.

---

**Note**: Always test on a staging environment before pushing to production!

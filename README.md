# WordPress Deployment Tool

<div align="center">
  <img src="assets/icon.png" alt="WordPress Deployment Tool Logo" width="200"/>
</div>

A desktop application for synchronizing WordPress sites between Local by Flywheel and remote hosting platforms (Kinsta, etc.) using Git-based version tracking and SFTP file transfer.

## Features

- **Push to Remote**: Upload changed files based on Git commits
- **Pull from Remote**: Download files based on date ranges and specific paths
- **Database Sync**: Push and pull MySQL databases between local and remote
- **Auto-detect Database**: Automatically reads database credentials from wp-config.php files
- **Git Integration**: Tracks commits to identify which files have changed
- **Secure Credentials**: Passwords stored in system keyring
- **Selective Sync**: Configure which paths to include/exclude
- **Progress Tracking**: Real-time feedback during transfers
- **Multiple Sites**: Manage configurations for multiple WordPress sites
- **URL Replacement**: Automatically handles WordPress URL changes during database sync

## Installation

### Requirements

- Python 3.8 or higher
- Git installed and configured
- SFTP access to your remote server
- **WP-CLI** (WordPress Command Line) for database sync features
  - **macOS**: `brew install wp-cli`
  - **Linux**: [Installation Guide](https://wp-cli.org/#installing)
  - **Remote server**: Usually pre-installed by hosting providers (Kinsta, WP Engine, etc.)

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
       wp-content/themes/
       wp-content/plugins/
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

### Database Sync

The tool can synchronize MySQL databases between local and remote WordPress installations, with automatic URL replacement and backup creation.

#### Configure Database

1. Go to the **Configuration** tab
2. Select your site
3. Click **Configure Database**
4. **Option 1: Auto-detect (Recommended)**
   - Click **Auto-detect from wp-config.php** button for Local Database
   - Click **Auto-detect from wp-config.php** button for Remote Database
   - The tool will automatically read your wp-config.php files and populate all fields
   - Review the detected configuration

5. **Option 2: Manual Entry**
   - **Local Database**: Name, host (usually localhost), port (3306), username, password
   - **Remote Database**: Name, host (usually localhost via SSH), port (3306), username, password
   - **Local URL**: Your local WordPress URL (e.g., `http://mysite.local`)
   - **Remote URL**: Your production WordPress URL (e.g., `https://mysite.com`)

6. **Exclude Tables**: Tables to skip during sync (e.g., `wp_users`, `wp_usermeta`)
7. Click **Test Local Connection** and **Test Remote Connection** to verify
8. Click **Save**

**Note**: Auto-detection reads database credentials from your WordPress wp-config.php files, making configuration quick and error-free.

#### Push Database to Remote

⚠️ **Warning**: This will **OVERWRITE** your production database with your local database!

1. Go to **Push to Remote** tab
2. Select your site
3. Click **Push Database**
4. Review the warning dialog carefully
5. Confirm the operation

The tool will:
- Export your local database
- Create a backup of the remote database
- Upload and import the database to remote
- Replace local URLs with remote URLs (handles WordPress serialized data)

**Use case**: Pushing a complete site redesign or major content changes to production.

#### Pull Database from Remote

1. Go to **Pull from Remote** tab
2. Select your site
3. Click **Pull Database**
4. Confirm the operation

The tool will:
- Export the remote database
- Create a backup of your local database
- Download and import the database locally
- Replace remote URLs with local URLs

**Use case**: Getting the latest production content/posts to your local development environment.

#### Database Sync Safety Features

- **Automatic Backups**: Creates a backup before every import (with timestamp)
- **Confirmation Dialogs**: Requires confirmation before destructive operations
- **Table Exclusions**: Skip sensitive tables (users, sessions) when pushing to production
- **URL Replacement**: Uses WP-CLI to properly handle WordPress serialized data
- **WP-CLI Verification**: Checks that WP-CLI is available before operations

#### Common Exclude Tables

When pushing to production, you typically want to exclude:
```
wp_users           # Don't overwrite production users
wp_usermeta        # Don't overwrite user metadata
wp_sessions        # Temporary session data
```

For WooCommerce sites, also exclude:
```
wp_woocommerce_sessions
wp_woocommerce_orders
wp_woocommerce_order_items
```

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

### "WP-CLI not found"

Database sync requires WP-CLI to be installed:

**On Local (macOS)**:
```bash
brew install wp-cli
wp --version  # Verify installation
```

**On Remote Server**:
- Most managed WordPress hosts (Kinsta, WP Engine, Flywheel) have WP-CLI pre-installed
- Check with your hosting provider if you get this error
- Test via SSH: `ssh user@host 'wp --version'`

### "Database import failed"

1. Verify database credentials are correct
2. Check that the database user has proper permissions (CREATE, DROP, INSERT, etc.)
3. Review logs at `~/.wp-deploy/logs/operations.log` for detailed error messages
4. Ensure there's enough disk space on the target system

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

- No conflict resolution for files (last write wins)
- No automatic rollback on errors
- Large files (>100MB) may timeout depending on connection
- Database sync requires WP-CLI on both local and remote systems

## Future Enhancements

See `DEVELOPMENT_DOCUMENTATION.md` for planned features:
- Conflict resolution for file sync
- Scheduled database pulls
- Database diff viewer
- Multi-environment support (dev → staging → production)
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

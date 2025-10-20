# Quick Start Guide

Get up and running with the WordPress Deployment Tool in 5 minutes.

## Step 1: Install Dependencies

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Step 2: Prepare Your Local Site

Make sure your local WordPress site:
1. Is managed by Local by Flywheel
2. Has Git initialized:
   ```bash
   cd /path/to/your/local/site/app/public
   git init
   git add .
   git commit -m "Initial commit"
   ```

## Step 3: Get Your SFTP Credentials

For Kinsta:
1. Log into MyKinsta dashboard
2. Go to your site
3. Navigate to Info > SFTP/SSH
4. Note down:
   - Host (e.g., `sftp.kinsta.com`)
   - Port (usually `22`)
   - Username (e.g., `yoursite_123`)
   - Password
   - Path (e.g., `/www/yoursite_123/public`)

## Step 4: Launch the Tool

```bash
python main.py
```

## Step 5: Add Your First Site

1. Click the **Configuration** tab
2. Click **Add Site**
3. Fill in the form:
   - **Site Name**: "My Production Site"
   - **Local Path**: Browse to your Local site (e.g., `/Users/yourname/Local Sites/mysite/app/public`)
   - **Git Repo Path**: Click "Same as Local"
   - **Host**: Enter your SFTP host
   - **Port**: 22
   - **Username**: Your SFTP username
   - **Password**: Your SFTP password
   - **Remote Path**: Your remote site path
   - **Pull Include Paths**: Leave default or customize
4. Click **Save**
5. Click **Test Connection** to verify

## Step 6: Push Your First Update

1. Make a change to your local site
2. Commit it:
   ```bash
   git add .
   git commit -m "Test update"
   ```
3. Go to **Push to Remote** tab
4. Select your site
5. Click **Preview Files**
6. Click **Push to Remote**
7. Confirm

Done! Your changes are now live.

## Step 7: Pull Files from Remote

1. Go to **Pull from Remote** tab
2. Select your site
3. Click "Last 7 Days" for date range
4. Click **Preview Files**
5. Click **Pull from Remote**
6. Confirm

Files from the remote server are now local.

## Common First-Time Issues

### "Git repository not found"

```bash
cd /path/to/your/site
git init
git add .
git commit -m "Initial commit"
```

### "SFTP connection failed"

Double-check your credentials in the hosting dashboard.

### "No files to push"

Make sure you committed your changes:
```bash
git status
git add .
git commit -m "Your changes"
```

## Next Steps

- Review `README.md` for detailed documentation
- Check `DEVELOPMENT_DOCUMENTATION.md` for technical details
- Configure exclude patterns for your needs
- Set up multiple sites

## Tips

1. **Always commit before pushing**: The tool tracks Git commits
2. **Test on staging first**: Before pushing to production
3. **Preview before acting**: Use preview buttons to see what will change
4. **Check logs**: `~/.wp-deploy/logs/operations.log` for troubleshooting
5. **Backup first**: Keep backups of important files

## Workflow Example

**Daily Development**:
```bash
# 1. Work on local site
# 2. Commit changes
git add .
git commit -m "Update homepage"

# 3. Push to remote
python main.py  # Use GUI to push

# 4. Changes are live!
```

**Getting Client Uploads**:
```bash
# 1. Client uploads images via WordPress
# 2. Pull recent files
python main.py  # Use GUI to pull last 7 days

# 3. Images are now local!
```

That's it! You're ready to use the WordPress Deployment Tool.

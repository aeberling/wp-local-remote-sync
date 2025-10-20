"""
Database pull controller for downloading database from remote server
"""
import os
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Tuple, Callable, List
from ..services.config_service import ConfigService
from ..services.ssh_service import SSHService
from ..services.sftp_service import SFTPService
from ..services.database_service import DatabaseService
from ..utils.logger import setup_logger


class DBPullController:
    """Handles database pull operations from remote to local"""

    def __init__(self, config_service: ConfigService):
        self.config_service = config_service
        self.logger = setup_logger('db_pull')

    def pull(self, site_id: str, exclude_tables: List[str] = None,
             progress_callback: Callable = None) -> Tuple[bool, str, dict]:
        """
        Pull remote database to local installation

        Args:
            site_id: Site identifier
            exclude_tables: Additional tables to exclude (merged with config)
            progress_callback: Callback function(step, total_steps, message)

        Returns:
            Tuple of (success, message, stats_dict)
        """
        self.logger.info(f"Starting database pull operation for site: {site_id}")

        # Get site configuration
        site = self.config_service.get_site(site_id)
        if not site:
            return False, f"Site not found: {site_id}", {}

        if not site.database_config:
            return False, "Database not configured for this site", {}

        # Get passwords
        ssh_password = self.config_service.get_password(site_id)
        if not ssh_password:
            return False, "SSH password not found in keyring", {}

        stats = {
            'tables_exported': 0,
            'tables_imported': 0,
            'bytes_transferred': 0,
            'urls_replaced': 0,
            'backup_created': ''
        }

        temp_local_file = None
        temp_remote_file = None

        try:
            total_steps = 10
            current_step = 0

            # Step 1: Verify WP-CLI locally
            current_step += 1
            if progress_callback:
                progress_callback(current_step, total_steps, "Verifying WP-CLI locally")

            ssh_service = SSHService(site.remote_host, site.remote_port, site.remote_username, ssh_password)
            db_service = DatabaseService(site, ssh_service)

            success, version = db_service.verify_wp_cli_local()
            if not success:
                return False, f"WP-CLI not available locally: {version}", stats

            # Step 2: Connect to remote server
            current_step += 1
            if progress_callback:
                progress_callback(current_step, total_steps, "Connecting to remote server")

            ssh_service.connect()

            # Step 3: Verify WP-CLI remotely
            current_step += 1
            if progress_callback:
                progress_callback(current_step, total_steps, "Verifying WP-CLI on remote server")

            success, version = db_service.verify_wp_cli_remote()
            if not success:
                ssh_service.disconnect()
                return False, f"WP-CLI not available on remote server: {version}", stats

            # Step 4: Prepare exclude tables list
            current_step += 1
            if progress_callback:
                progress_callback(current_step, total_steps, "Preparing database export")

            all_exclude_tables = site.database_config.exclude_tables.copy() if site.database_config.exclude_tables else []
            if exclude_tables:
                all_exclude_tables.extend(exclude_tables)

            # Step 5: Export remote database
            current_step += 1
            if progress_callback:
                progress_callback(current_step, total_steps, "Exporting remote database")

            temp_remote_file = f"/tmp/db-pull-{site_id}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.sql"

            success, msg = db_service.export_remote_database(temp_remote_file, all_exclude_tables)
            if not success:
                ssh_service.disconnect()
                return False, f"Failed to export remote database: {msg}", stats

            # Count tables
            success, tables = db_service.get_remote_table_list()
            if success:
                stats['tables_exported'] = len(tables) - len(all_exclude_tables)

            # Step 6: Search-replace URLs on remote (before download)
            current_step += 1
            if progress_callback:
                progress_callback(current_step, total_steps, "Updating URLs for local environment")

            # Create a copy with replaced URLs
            temp_remote_file_replaced = f"/tmp/db-pull-{site_id}-replaced-{datetime.now().strftime('%Y%m%d-%H%M%S')}.sql"

            if site.database_config.remote_url and site.database_config.local_url:
                # Import the exported database, do search-replace, then export again
                # For simplicity, we'll do search-replace after importing locally
                temp_remote_file_replaced = temp_remote_file
            else:
                temp_remote_file_replaced = temp_remote_file

            # Step 7: Download database from remote
            current_step += 1
            if progress_callback:
                progress_callback(current_step, total_steps, "Downloading database from remote server")

            temp_local_file = os.path.join(tempfile.gettempdir(), f"db-pull-{site_id}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.sql")

            sftp = SFTPService(site.remote_host, site.remote_port, site.remote_username, ssh_password)
            sftp.connect()
            success, msg = sftp.download_file(temp_remote_file_replaced, temp_local_file)
            sftp.disconnect()

            if not success:
                ssh_service.disconnect()
                return False, f"Failed to download database: {msg}", stats

            file_size = os.path.getsize(temp_local_file)
            stats['bytes_transferred'] = file_size

            # Step 8: Backup local database
            current_step += 1
            if progress_callback:
                progress_callback(current_step, total_steps, "Creating local database backup")

            if site.database_config.backup_before_import:
                timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                backup_file = f"local-backup-{timestamp}.sql"
                backup_path = os.path.join(tempfile.gettempdir(), backup_file)

                success, msg = db_service.export_local_database(backup_path)

                if success:
                    stats['backup_created'] = backup_file
                else:
                    self.logger.warning(f"Failed to create local backup: {msg}")

            # Step 9: Import database locally
            current_step += 1
            if progress_callback:
                progress_callback(current_step, total_steps, "Importing database locally")

            success, msg = db_service.import_local_database(temp_local_file, backup_first=False)
            if not success:
                ssh_service.disconnect()
                return False, f"Failed to import database locally: {msg}", stats

            stats['tables_imported'] = stats['tables_exported']

            # Step 10: Search-replace URLs locally
            current_step += 1
            if progress_callback:
                progress_callback(current_step, total_steps, "Updating URLs in local database")

            if site.database_config.remote_url and site.database_config.local_url:
                success, msg, replace_stats = db_service.search_replace_local(
                    site.database_config.remote_url,
                    site.database_config.local_url
                )
                if success:
                    stats['urls_replaced'] = replace_stats.get('replacements', 0)
                else:
                    self.logger.warning(f"URL replacement failed: {msg}")

            # Cleanup remote temp files
            try:
                cleanup_command = f"rm -f {temp_remote_file}"
                if temp_remote_file_replaced != temp_remote_file:
                    cleanup_command += f" {temp_remote_file_replaced}"
                ssh_service.execute_command(cleanup_command)
            except:
                pass

            # Disconnect
            ssh_service.disconnect()

            # Update last pulled timestamp
            site.last_db_pulled_at = datetime.now().isoformat()
            self.config_service.update_site(site)

            success_msg = f"Database pulled successfully: {stats['tables_exported']} tables"
            if stats['urls_replaced'] > 0:
                success_msg += f", {stats['urls_replaced']} URLs replaced"

            self.logger.info(success_msg)
            return True, success_msg, stats

        except Exception as e:
            error_msg = f"Database pull failed: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg, stats

        finally:
            # Cleanup local temp file
            if temp_local_file and os.path.exists(temp_local_file):
                try:
                    os.remove(temp_local_file)
                except:
                    pass

    def get_pull_preview(self, site_id: str) -> Tuple[bool, str, dict]:
        """
        Dry-run: Show what would be pulled

        Args:
            site_id: Site identifier

        Returns:
            Tuple of (success, message, preview_dict)
        """
        try:
            site = self.config_service.get_site(site_id)
            if not site:
                return False, f"Site not found: {site_id}", {}

            if not site.database_config:
                return False, "Database not configured for this site", {}

            preview = {
                'remote_tables': [],
                'excluded_tables': site.database_config.exclude_tables,
                'urls_to_replace': [],
                'local_backup_will_be_created': site.database_config.backup_before_import,
                'estimated_size_mb': 0
            }

            # Get SSH password
            ssh_password = self.config_service.get_password(site_id)
            if ssh_password:
                try:
                    # Connect and get table list
                    ssh_service = SSHService(site.remote_host, site.remote_port, site.remote_username, ssh_password)
                    ssh_service.connect()

                    db_service = DatabaseService(site, ssh_service)
                    success, tables = db_service.get_remote_table_list()
                    if success:
                        preview['remote_tables'] = tables

                    ssh_service.disconnect()
                except:
                    pass

            # URL replacements
            if site.database_config.remote_url and site.database_config.local_url:
                preview['urls_to_replace'] = [
                    (site.database_config.remote_url, site.database_config.local_url)
                ]

            return True, "Preview generated successfully", preview

        except Exception as e:
            return False, str(e), {}

    def _format_bytes(self, bytes_size: int) -> str:
        """Format bytes to human-readable string"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.1f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.1f} TB"

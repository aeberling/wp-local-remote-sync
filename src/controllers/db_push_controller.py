"""
Database push controller for uploading database to remote server
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


class DBPushController:
    """Handles database push operations from local to remote"""

    def __init__(self, config_service: ConfigService):
        self.config_service = config_service
        self.logger = setup_logger('db_push')

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
        """
        self.logger.info(f"Starting database push operation for site: {site_id}")

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

            all_exclude_tables = site.database_config.exclude_tables.copy()
            if exclude_tables:
                all_exclude_tables.extend(exclude_tables)

            # Step 5: Export local database
            current_step += 1
            if progress_callback:
                progress_callback(current_step, total_steps, "Exporting local database")

            temp_local_file = os.path.join(tempfile.gettempdir(), f"db-push-{site_id}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.sql")

            success, msg = db_service.export_local_database(temp_local_file, all_exclude_tables)
            if not success:
                ssh_service.disconnect()
                return False, f"Failed to export local database: {msg}", stats

            file_size = os.path.getsize(temp_local_file)
            stats['bytes_transferred'] = file_size

            # Count tables
            success, tables = db_service.get_local_table_list()
            if success:
                stats['tables_exported'] = len(tables) - len(all_exclude_tables)

            # Step 6: Search-replace URLs in exported file
            current_step += 1
            if progress_callback:
                progress_callback(current_step, total_steps, "Replacing URLs for remote environment")

            # We need to import to temp, do search-replace, then export again
            # For now, we'll do search-replace after import on remote
            # This is safer and uses WP-CLI's built-in serialized data handling

            # Step 7: Upload database to remote
            current_step += 1
            if progress_callback:
                progress_callback(current_step, total_steps, f"Uploading database ({self._format_bytes(file_size)})")

            temp_remote_file = f"/tmp/db-push-{site_id}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.sql"

            sftp = SFTPService(site.remote_host, site.remote_port, site.remote_username, ssh_password)
            sftp.connect()
            success, msg = sftp.upload_file(temp_local_file, temp_remote_file)
            sftp.disconnect()

            if not success:
                ssh_service.disconnect()
                return False, f"Failed to upload database: {msg}", stats

            # Step 8: Backup remote database
            current_step += 1
            if progress_callback:
                progress_callback(current_step, total_steps, "Creating remote database backup")

            if site.database_config.backup_before_import:
                timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                backup_file = f"remote-backup-{timestamp}.sql"
                success, msg = db_service.export_remote_database(backup_file)

                if success:
                    stats['backup_created'] = backup_file
                else:
                    self.logger.warning(f"Failed to create remote backup: {msg}")

            # Step 9: Import database on remote
            current_step += 1
            if progress_callback:
                progress_callback(current_step, total_steps, "Importing database on remote server")

            success, msg = db_service.import_remote_database(temp_remote_file, backup_first=False)
            if not success:
                ssh_service.disconnect()
                return False, f"Failed to import database on remote: {msg}", stats

            stats['tables_imported'] = stats['tables_exported']

            # Step 10: Search-replace URLs on remote
            current_step += 1
            if progress_callback:
                progress_callback(current_step, total_steps, "Updating URLs in remote database")

            if site.database_config.local_url and site.database_config.remote_url:
                success, msg, replace_stats = db_service.search_replace_remote(
                    site.database_config.local_url,
                    site.database_config.remote_url
                )
                if success:
                    stats['urls_replaced'] = replace_stats.get('replacements', 0)
                else:
                    self.logger.warning(f"URL replacement failed: {msg}")

            # Cleanup remote temp file
            try:
                cleanup_command = f"rm -f {temp_remote_file}"
                ssh_service.execute_command(cleanup_command)
            except:
                pass

            # Disconnect
            ssh_service.disconnect()

            # Update last pushed timestamp
            site.last_db_pushed_at = datetime.now().isoformat()
            self.config_service.update_site(site)

            success_msg = f"Database pushed successfully: {stats['tables_exported']} tables"
            if stats['urls_replaced'] > 0:
                success_msg += f", {stats['urls_replaced']} URLs replaced"

            self.logger.info(success_msg)
            return True, success_msg, stats

        except Exception as e:
            error_msg = f"Database push failed: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg, stats

        finally:
            # Cleanup local temp file
            if temp_local_file and os.path.exists(temp_local_file):
                try:
                    os.remove(temp_local_file)
                except:
                    pass

    def get_push_preview(self, site_id: str) -> Tuple[bool, str, dict]:
        """
        Dry-run: Show what would be pushed

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
                'local_tables': [],
                'excluded_tables': site.database_config.exclude_tables,
                'urls_to_replace': [],
                'remote_backup_will_be_created': site.database_config.backup_before_import,
                'estimated_size_mb': 0
            }

            # Get table list
            db_service = DatabaseService(site)
            success, tables = db_service.get_local_table_list()
            if success:
                preview['local_tables'] = tables

            # URL replacements
            if site.database_config.local_url and site.database_config.remote_url:
                preview['urls_to_replace'] = [
                    (site.database_config.local_url, site.database_config.remote_url)
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

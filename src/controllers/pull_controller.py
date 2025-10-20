"""
Pull controller for downloading files from remote server
"""
import os
from pathlib import Path
from datetime import datetime
from typing import List, Callable, Tuple
from ..services.sftp_service import SFTPService
from ..services.config_service import ConfigService
from ..models.sync_state import OperationState
from ..utils.patterns import filter_files
from ..utils.logger import setup_logger


class PullController:
    """Handles pull operations from remote to local"""

    def __init__(self, config_service: ConfigService):
        self.config_service = config_service
        self.logger = setup_logger('pull')

    def pull(self, site_id: str, start_date: datetime, end_date: datetime,
             include_paths: List[str] = None, progress_callback: Callable = None) -> Tuple[bool, str, dict]:
        """
        Pull files from remote to local

        Args:
            site_id: Site identifier
            start_date: Start date for file filter
            end_date: End date for file filter
            include_paths: List of paths to include (relative to remote_path)
            progress_callback: Optional callback(current, total, message)

        Returns:
            Tuple of (success, message, stats_dict)
        """
        self.logger.info(f"Starting pull operation for site: {site_id}")
        self.logger.info(f"Date range: {start_date} to {end_date}")

        # Get site configuration
        site = self.config_service.get_site(site_id)
        if not site:
            return False, f"Site not found: {site_id}", {}

        # Get password
        password = self.config_service.get_password(site_id)
        if not password:
            return False, "Password not found in keyring", {}

        # Use provided include paths or site defaults
        if include_paths is None:
            include_paths = site.pull_include_paths

        if not include_paths:
            return False, "No include paths specified", {}

        stats = {
            'files_pulled': 0,
            'files_failed': 0,
            'bytes_transferred': 0,
            'files': []
        }

        try:
            # Connect to SFTP
            sftp = SFTPService(site.remote_host, site.remote_port, site.remote_username, password)
            sftp.connect()

            # Collect all files from include paths
            all_files = []
            for include_path in include_paths:
                include_path = include_path.strip()
                if not include_path:
                    continue

                remote_path = os.path.join(site.remote_path, include_path).replace('\\', '/')

                # Check if path exists
                if not sftp.path_exists(remote_path):
                    self.logger.warning(f"Remote path does not exist: {remote_path}")
                    continue

                # List files recursively with date filter
                files = sftp.list_files_recursive(remote_path, start_date, end_date)
                all_files.extend(files)

            if not all_files:
                sftp.disconnect()
                self.logger.info("No files found matching criteria")
                return True, "No files found matching criteria", stats

            # Filter files by exclude patterns
            file_paths = [f[0] for f in all_files]
            filtered_paths = filter_files(file_paths, site.exclude_patterns)

            # Create filtered list with dates
            files_to_pull = [(path, date) for path, date in all_files if path in filtered_paths]

            self.logger.info(f"Found {len(files_to_pull)} files to pull")

            # Download files
            total_files = len(files_to_pull)
            for i, (remote_file, mod_date) in enumerate(files_to_pull):
                if progress_callback:
                    # Get relative path for display
                    rel_path = remote_file.replace(site.remote_path, '').lstrip('/')
                    progress_callback(i + 1, total_files, f"Downloading {rel_path}")

                # Calculate local path
                # Remove remote_path prefix to get relative path
                rel_path = remote_file.replace(site.remote_path, '').lstrip('/')
                local_file = os.path.join(site.local_path, rel_path)

                # Download file
                success, message = sftp.download_file(remote_file, local_file)

                if success:
                    stats['files_pulled'] += 1
                    file_size = os.path.getsize(local_file)
                    stats['bytes_transferred'] += file_size
                    stats['files'].append(rel_path)
                else:
                    stats['files_failed'] += 1
                    self.logger.error(f"Failed to download {remote_file}: {message}")

            # Disconnect SFTP
            sftp.disconnect()

            # Update sync state
            operation_state = OperationState(
                timestamp=datetime.now().isoformat(),
                status='success' if stats['files_failed'] == 0 else 'partial',
                files_count=stats['files_pulled'],
                bytes_transferred=stats['bytes_transferred'],
                date_range_start=start_date.isoformat(),
                date_range_end=end_date.isoformat()
            )
            sync_state = self.config_service.get_sync_state(site_id)
            sync_state.last_pull = operation_state
            self.config_service.update_sync_state(sync_state)

            success_msg = f"Pull completed: {stats['files_pulled']} files downloaded"
            if stats['files_failed'] > 0:
                success_msg += f", {stats['files_failed']} failed"

            self.logger.info(success_msg)
            return True, success_msg, stats

        except Exception as e:
            error_msg = f"Pull failed: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg, stats

    def get_files_to_pull(self, site_id: str, start_date: datetime, end_date: datetime,
                          include_paths: List[str] = None) -> Tuple[bool, str, List[Tuple[str, datetime]]]:
        """
        Get list of files that would be pulled (dry run)

        Args:
            site_id: Site identifier
            start_date: Start date for file filter
            end_date: End date for file filter
            include_paths: List of paths to include

        Returns:
            Tuple of (success, message, files_list)
        """
        try:
            site = self.config_service.get_site(site_id)
            if not site:
                return False, f"Site not found: {site_id}", []

            password = self.config_service.get_password(site_id)
            if not password:
                return False, "Password not found in keyring", []

            if include_paths is None:
                include_paths = site.pull_include_paths

            if not include_paths:
                return False, "No include paths specified", []

            # Connect to SFTP
            sftp = SFTPService(site.remote_host, site.remote_port, site.remote_username, password)
            sftp.connect()

            # Collect all files
            all_files = []
            for include_path in include_paths:
                include_path = include_path.strip()
                if not include_path:
                    continue

                remote_path = os.path.join(site.remote_path, include_path).replace('\\', '/')

                if not sftp.path_exists(remote_path):
                    continue

                files = sftp.list_files_recursive(remote_path, start_date, end_date)
                all_files.extend(files)

            sftp.disconnect()

            # Filter files
            file_paths = [f[0] for f in all_files]
            filtered_paths = filter_files(file_paths, site.exclude_patterns)
            files_to_pull = [(path, date) for path, date in all_files if path in filtered_paths]

            return True, f"Found {len(files_to_pull)} files", files_to_pull

        except Exception as e:
            return False, str(e), []

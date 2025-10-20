"""
Push controller for uploading files to remote server
"""
import os
from pathlib import Path
from datetime import datetime
from typing import List, Callable, Tuple
from ..services.git_service import GitService
from ..services.sftp_service import SFTPService
from ..services.config_service import ConfigService
from ..models.sync_state import OperationState
from ..utils.patterns import filter_files
from ..utils.logger import setup_logger


class PushController:
    """Handles push operations from local to remote"""

    def __init__(self, config_service: ConfigService):
        self.config_service = config_service
        self.logger = setup_logger('push')

    def push(self, site_id: str, progress_callback: Callable = None) -> Tuple[bool, str, dict]:
        """
        Push files from local to remote

        Args:
            site_id: Site identifier
            progress_callback: Optional callback(current, total, message)

        Returns:
            Tuple of (success, message, stats_dict)
        """
        self.logger.info(f"Starting push operation for site: {site_id}")

        # Get site configuration
        site = self.config_service.get_site(site_id)
        if not site:
            return False, f"Site not found: {site_id}", {}

        # Get password
        password = self.config_service.get_password(site_id)
        if not password:
            return False, "Password not found in keyring", {}

        stats = {
            'files_pushed': 0,
            'files_failed': 0,
            'bytes_transferred': 0,
            'files': []
        }

        try:
            # Initialize Git service
            git_service = GitService(site.git_repo_path)
            current_commit = git_service.get_current_commit()
            commit_message = git_service.get_commit_message()

            # Determine files to push
            if site.last_pushed_commit:
                self.logger.info(f"Getting changes since commit: {site.last_pushed_commit[:7]}")
                files_to_push = git_service.get_changed_files(site.last_pushed_commit, current_commit)
            else:
                self.logger.info("No previous push found, getting all tracked files")
                files_to_push = git_service.get_all_tracked_files()

            # Filter excluded files
            files_to_push = filter_files(files_to_push, site.exclude_patterns)

            if not files_to_push:
                self.logger.info("No files to push")
                return True, "No files to push", stats

            self.logger.info(f"Found {len(files_to_push)} files to push")

            # Connect to SFTP
            sftp = SFTPService(site.remote_host, site.remote_port, site.remote_username, password)
            sftp.connect()

            # Upload files
            total_files = len(files_to_push)
            for i, file_path in enumerate(files_to_push):
                if progress_callback:
                    progress_callback(i + 1, total_files, f"Uploading {file_path}")

                local_file = os.path.join(site.local_path, file_path)
                remote_file = os.path.join(site.remote_path, file_path).replace('\\', '/')

                # Check if local file exists
                if not os.path.exists(local_file):
                    self.logger.warning(f"Local file not found, skipping: {local_file}")
                    continue

                # Upload file
                success, message = sftp.upload_file(local_file, remote_file)

                if success:
                    stats['files_pushed'] += 1
                    file_size = os.path.getsize(local_file)
                    stats['bytes_transferred'] += file_size
                    stats['files'].append(file_path)
                else:
                    stats['files_failed'] += 1
                    self.logger.error(f"Failed to upload {file_path}: {message}")

            # Disconnect SFTP
            sftp.disconnect()

            # Update last pushed commit
            self.config_service.update_last_pushed_commit(site_id, current_commit)

            # Update sync state
            operation_state = OperationState(
                timestamp=datetime.now().isoformat(),
                status='success' if stats['files_failed'] == 0 else 'partial',
                files_count=stats['files_pushed'],
                bytes_transferred=stats['bytes_transferred'],
                commit_hash=current_commit,
                commit_message=commit_message
            )
            sync_state = self.config_service.get_sync_state(site_id)
            sync_state.last_push = operation_state
            self.config_service.update_sync_state(sync_state)

            success_msg = f"Push completed: {stats['files_pushed']} files uploaded"
            if stats['files_failed'] > 0:
                success_msg += f", {stats['files_failed']} failed"

            self.logger.info(success_msg)
            return True, success_msg, stats

        except Exception as e:
            error_msg = f"Push failed: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg, stats

    def get_files_to_push(self, site_id: str) -> Tuple[bool, str, List[str]]:
        """
        Get list of files that would be pushed (dry run)

        Args:
            site_id: Site identifier

        Returns:
            Tuple of (success, message, files_list)
        """
        try:
            site = self.config_service.get_site(site_id)
            if not site:
                return False, f"Site not found: {site_id}", []

            git_service = GitService(site.git_repo_path)
            current_commit = git_service.get_current_commit()

            if site.last_pushed_commit:
                files = git_service.get_changed_files(site.last_pushed_commit, current_commit)
            else:
                files = git_service.get_all_tracked_files()

            files = filter_files(files, site.exclude_patterns)

            return True, f"Found {len(files)} files", files

        except Exception as e:
            return False, str(e), []

"""
Push controller for uploading files to remote server
"""
import os
import zipfile
import tempfile
from pathlib import Path
from datetime import datetime
from typing import List, Callable, Tuple, Dict
from collections import defaultdict
from ..services.git_service import GitService
from ..services.sftp_service import SFTPService
from ..services.ssh_service import SSHService
from ..services.config_service import ConfigService
from ..models.sync_state import OperationState
from ..utils.patterns import filter_files
from ..utils.logger import setup_logger


class PushController:
    """Handles push operations from local to remote"""

    def __init__(self, config_service: ConfigService):
        self.config_service = config_service
        self.logger = setup_logger('push')

    def _group_files_by_folder(self, files: List[str], threshold: int = 5) -> Dict[str, List[str]]:
        """
        Group files by their parent folder for compression

        Args:
            files: List of file paths
            threshold: Minimum number of files in a folder to consider for compression

        Returns:
            Dict with 'compress' (dict of folder: files) and 'individual' (list of files)
        """
        folder_files = defaultdict(list)

        # Group files by immediate parent folder
        for file_path in files:
            parts = Path(file_path).parts
            if len(parts) > 1:
                # Get parent folder (e.g., "wp-content/plugins/plugin-name")
                folder = str(Path(*parts[:-1]))
                folder_files[folder].append(file_path)
            else:
                # File at root
                folder_files['_root'].append(file_path)

        # Separate folders with many files (compress) vs few files (individual)
        to_compress = {}
        individual = []

        for folder, file_list in folder_files.items():
            if folder == '_root' or len(file_list) < threshold:
                individual.extend(file_list)
            else:
                to_compress[folder] = file_list

        return {'compress': to_compress, 'individual': individual}

    def _create_zip_from_files(self, files: List[str], local_root: str, zip_name: str) -> str:
        """
        Create a zip file from a list of files

        Args:
            files: List of relative file paths
            local_root: Local root directory
            zip_name: Name for the zip file

        Returns:
            Path to created zip file
        """
        temp_dir = tempfile.gettempdir()
        zip_path = os.path.join(temp_dir, zip_name)

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in files:
                local_file = os.path.join(local_root, file_path)
                if os.path.exists(local_file):
                    # Add file with its relative path preserved
                    zipf.write(local_file, file_path)

        return zip_path

    def _extract_zip_on_remote(self, ssh_service: SSHService, remote_zip_path: str,
                               remote_extract_path: str) -> Tuple[bool, str]:
        """
        Extract a zip file on the remote server

        Args:
            ssh_service: SSH service instance
            remote_zip_path: Path to zip file on remote
            remote_extract_path: Path to extract to

        Returns:
            Tuple of (success, message)
        """
        try:
            # Extract zip file
            command = f"cd {remote_extract_path} && unzip -o {remote_zip_path}"
            success, output, error = ssh_service.execute_command(command)

            if not success:
                return False, f"Failed to extract: {error}"

            # Delete zip file
            ssh_service.execute_command(f"rm -f {remote_zip_path}")

            return True, "Extracted successfully"

        except Exception as e:
            return False, str(e)

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
            files_skipped = 0
            for i, file_path in enumerate(files_to_push):
                if progress_callback:
                    progress_callback(i + 1, total_files, f"Uploading {file_path}")

                local_file = os.path.join(site.local_path, file_path)
                remote_file = os.path.join(site.remote_path, file_path).replace('\\', '/')

                # Check if local file exists
                if not os.path.exists(local_file):
                    self.logger.warning(f"Local file not found, skipping: {local_file}")
                    continue

                # Skip if push_newer_only is enabled and local file is not newer
                if site.push_newer_only:
                    if not sftp.is_local_newer(local_file, remote_file):
                        self.logger.info(f"Skipping {file_path} (remote is up-to-date)")
                        files_skipped += 1
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
            if files_skipped > 0:
                success_msg += f", {files_skipped} skipped"
            if stats['files_failed'] > 0:
                success_msg += f", {stats['files_failed']} failed"

            self.logger.info(success_msg)
            return True, success_msg, stats

        except Exception as e:
            error_msg = f"Push failed: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg, stats

    def push_all(self, site_id: str, progress_callback: Callable = None) -> Tuple[bool, str, dict]:
        """
        Push ALL files from git repo to remote (ignores last_pushed_commit)

        Args:
            site_id: Site identifier
            progress_callback: Optional callback(current, total, message)

        Returns:
            Tuple of (success, message, stats_dict)
        """
        self.logger.info(f"Starting push ALL operation for site: {site_id}")

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

            # Always get ALL tracked files (ignore last_pushed_commit)
            self.logger.info("Getting all tracked files from git repository")
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
            files_skipped = 0
            for i, file_path in enumerate(files_to_push):
                if progress_callback:
                    progress_callback(i + 1, total_files, f"Uploading {file_path}")

                local_file = os.path.join(site.local_path, file_path)
                remote_file = os.path.join(site.remote_path, file_path).replace('\\', '/')

                # Check if local file exists
                if not os.path.exists(local_file):
                    self.logger.warning(f"Local file not found, skipping: {local_file}")
                    continue

                # Skip if push_newer_only is enabled and local file is not newer
                if site.push_newer_only:
                    if not sftp.is_local_newer(local_file, remote_file):
                        self.logger.info(f"Skipping {file_path} (remote is up-to-date)")
                        files_skipped += 1
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

            success_msg = f"Push ALL completed: {stats['files_pushed']} files uploaded"
            if files_skipped > 0:
                success_msg += f", {files_skipped} skipped"
            if stats['files_failed'] > 0:
                success_msg += f", {stats['files_failed']} failed"

            self.logger.info(success_msg)
            return True, success_msg, stats

        except Exception as e:
            error_msg = f"Push ALL failed: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg, stats

    def push_from_commits(self, site_id: str, commit_hashes: List[str], progress_callback: Callable = None) -> Tuple[bool, str, dict]:
        """
        Push files that were changed in the specified commits

        Args:
            site_id: Site identifier
            commit_hashes: List of commit hashes to push files from
            progress_callback: Optional callback(current, total, message)

        Returns:
            Tuple of (success, message, stats_dict)
        """
        self.logger.info(f"Starting push from commits for site: {site_id}")
        self.logger.info(f"Commits to push: {[h[:7] for h in commit_hashes]}")

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
            'files': [],
            'commits_pushed': len(commit_hashes)
        }

        try:
            # Initialize Git service
            git_service = GitService(site.git_repo_path)

            # Get all files changed in the selected commits
            files_to_push = git_service.get_files_in_commits(commit_hashes)

            # Filter excluded files
            files_to_push = filter_files(files_to_push, site.exclude_patterns)

            if not files_to_push:
                self.logger.info("No files to push from selected commits")
                return True, "No files to push from selected commits", stats

            self.logger.info(f"Found {len(files_to_push)} unique files from {len(commit_hashes)} commits")

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

            # Update sync state
            current_commit = git_service.get_current_commit()
            commit_message = f"Pushed files from {len(commit_hashes)} selected commits"

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

            success_msg = f"Push from commits completed: {stats['files_pushed']} files uploaded from {len(commit_hashes)} commits"
            if stats['files_failed'] > 0:
                success_msg += f", {stats['files_failed']} failed"

            self.logger.info(success_msg)
            return True, success_msg, stats

        except Exception as e:
            error_msg = f"Push from commits failed: {str(e)}"
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

    def push_folders(self, site_id: str, folders: List[str], progress_callback: Callable = None) -> Tuple[bool, str, dict]:
        """
        Push specific folders by compressing, transferring, and extracting on remote

        Args:
            site_id: Site identifier
            folders: List of folder paths relative to local_path
            progress_callback: Optional callback(current, total, message)

        Returns:
            Tuple of (success, message, stats_dict)
        """
        self.logger.info(f"Starting push folders operation for site: {site_id}")

        # Get site configuration
        site = self.config_service.get_site(site_id)
        if not site:
            return False, f"Site not found: {site_id}", {}

        # Get password
        password = self.config_service.get_password(site_id)
        if not password:
            return False, "Password not found in keyring", {}

        stats = {
            'folders_pushed': 0,
            'folders_failed': 0,
            'bytes_transferred': 0,
            'folders': []
        }

        try:
            # Connect to SFTP and SSH
            sftp = SFTPService(site.remote_host, site.remote_port, site.remote_username, password)
            sftp.connect()

            ssh = SSHService(site.remote_host, site.remote_port, site.remote_username, password)
            ssh.connect()

            total_folders = len(folders)

            for i, folder in enumerate(folders):
                folder = folder.strip()
                if not folder:
                    continue

                if progress_callback:
                    progress_callback(i + 1, total_folders, f"Processing {folder}")

                # Ensure folder path doesn't start with /
                if folder.startswith('/'):
                    folder = folder[1:]

                local_folder = os.path.join(site.local_path, folder)

                # Check if local folder exists
                if not os.path.exists(local_folder):
                    self.logger.warning(f"Local folder not found: {local_folder}")
                    stats['folders_failed'] += 1
                    if progress_callback:
                        progress_callback(i + 1, total_folders, f"❌ Folder not found: {folder}")
                    continue

                if not os.path.isdir(local_folder):
                    self.logger.warning(f"Path is not a directory: {local_folder}")
                    stats['folders_failed'] += 1
                    if progress_callback:
                        progress_callback(i + 1, total_folders, f"❌ Not a directory: {folder}")
                    continue

                # Count files before compression
                file_count = sum(len(files) for _, _, files in os.walk(local_folder))

                # Create zip file
                if progress_callback:
                    progress_callback(i + 1, total_folders, f"Compressing {folder} ({file_count} files)")

                timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
                zip_filename = f"push-folder-{site_id}-{i}-{timestamp}.zip"
                temp_zip_path = os.path.join(tempfile.gettempdir(), zip_filename)

                try:
                    with zipfile.ZipFile(temp_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                        # Walk through the directory
                        files_added = 0
                        for root, dirs, files in os.walk(local_folder):
                            for file in files:
                                file_path = os.path.join(root, file)
                                # Calculate relative path from local_path (not local_folder)
                                arcname = os.path.relpath(file_path, site.local_path)
                                zipf.write(file_path, arcname)
                                files_added += 1

                                # Update progress every 50 files
                                if progress_callback and files_added % 50 == 0:
                                    progress_callback(i + 1, total_folders,
                                                    f"Compressing {folder} ({files_added}/{file_count} files)")

                    zip_size = os.path.getsize(temp_zip_path)
                    zip_size_mb = zip_size / (1024 * 1024)
                    self.logger.info(f"Created zip: {temp_zip_path} ({zip_size} bytes)")

                except Exception as e:
                    self.logger.error(f"Failed to create zip for {folder}: {e}")
                    stats['folders_failed'] += 1
                    if progress_callback:
                        progress_callback(i + 1, total_folders, f"❌ Compression failed: {folder}")
                    if os.path.exists(temp_zip_path):
                        os.remove(temp_zip_path)
                    continue

                # Upload zip file
                if progress_callback:
                    progress_callback(i + 1, total_folders, f"Uploading {folder} ({zip_size_mb:.1f} MB)")

                remote_zip_path = f"/tmp/{zip_filename}"
                success, message = sftp.upload_file(temp_zip_path, remote_zip_path)

                if not success:
                    self.logger.error(f"Failed to upload zip for {folder}: {message}")
                    stats['folders_failed'] += 1
                    if progress_callback:
                        progress_callback(i + 1, total_folders, f"❌ Upload failed: {folder}")
                    os.remove(temp_zip_path)
                    continue

                stats['bytes_transferred'] += zip_size

                # Extract on remote
                if progress_callback:
                    progress_callback(i + 1, total_folders, f"Extracting {folder} on remote...")

                # Extract directly to remote_path, which will overwrite existing files
                extract_command = f"cd {site.remote_path} && unzip -o {remote_zip_path}"
                success, output, error = ssh.execute_command(extract_command)

                if not success:
                    self.logger.error(f"Failed to extract {folder}: {error}")
                    stats['folders_failed'] += 1
                    if progress_callback:
                        progress_callback(i + 1, total_folders, f"❌ Extraction failed: {folder}")
                    # Clean up remote zip
                    ssh.execute_command(f"rm -f {remote_zip_path}")
                    os.remove(temp_zip_path)
                    continue

                # Clean up remote zip file
                if progress_callback:
                    progress_callback(i + 1, total_folders, f"Cleaning up {folder}...")
                ssh.execute_command(f"rm -f {remote_zip_path}")

                # Clean up local temp file
                os.remove(temp_zip_path)

                stats['folders_pushed'] += 1
                stats['folders'].append(folder)
                self.logger.info(f"Successfully pushed folder: {folder}")

                if progress_callback:
                    progress_callback(i + 1, total_folders, f"✓ Completed {folder}")

            # Disconnect
            sftp.disconnect()
            ssh.disconnect()

            if stats['folders_pushed'] == 0 and stats['folders_failed'] > 0:
                return False, f"All folders failed to push", stats

            success_msg = f"Push folders completed: {stats['folders_pushed']} folders pushed"
            if stats['folders_failed'] > 0:
                success_msg += f", {stats['folders_failed']} failed"

            self.logger.info(success_msg)
            return True, success_msg, stats

        except Exception as e:
            error_msg = f"Push folders failed: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg, stats

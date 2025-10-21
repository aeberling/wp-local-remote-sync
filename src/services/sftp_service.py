"""
SFTP service for file transfer operations
"""
import paramiko
import os
import stat
from pathlib import Path
from typing import List, Tuple, Callable
from datetime import datetime
from ..utils.logger import setup_logger


class SFTPService:
    """Handles SFTP operations for file transfer"""

    def __init__(self, host: str, port: int, username: str, password: str = None, key_path: str = None):
        """
        Initialize SFTP service

        Args:
            host: SFTP server hostname
            port: SFTP server port
            username: SFTP username
            password: SFTP password (optional if using key)
            key_path: Path to SSH private key (optional)
        """
        self.logger = setup_logger('sftp')
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.key_path = key_path

        self.ssh_client = None
        self.sftp_client = None

    def connect(self):
        """Establish SFTP connection"""
        try:
            self.logger.info(f"Connecting to {self.host}:{self.port} as {self.username}")

            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            # Connect with password or key
            if self.key_path:
                self.ssh_client.connect(
                    hostname=self.host,
                    port=self.port,
                    username=self.username,
                    key_filename=self.key_path
                )
            else:
                self.ssh_client.connect(
                    hostname=self.host,
                    port=self.port,
                    username=self.username,
                    password=self.password
                )

            self.sftp_client = self.ssh_client.open_sftp()
            self.logger.info("SFTP connection established")
            return True

        except Exception as e:
            self.logger.error(f"Failed to connect: {e}")
            raise ConnectionError(f"Failed to connect to SFTP server: {e}")

    def disconnect(self):
        """Close SFTP connection"""
        try:
            if self.sftp_client:
                self.sftp_client.close()
            if self.ssh_client:
                self.ssh_client.close()
            self.logger.info("SFTP connection closed")
        except Exception as e:
            self.logger.error(f"Error closing connection: {e}")

    def test_connection(self) -> Tuple[bool, str]:
        """
        Test SFTP connection

        Returns:
            Tuple of (success, message)
        """
        try:
            self.connect()
            self.disconnect()
            return True, "Connection successful"
        except Exception as e:
            return False, str(e)

    def mkdir_recursive(self, remote_path: str):
        """
        Create directory recursively on remote server

        Args:
            remote_path: Remote directory path
        """
        dirs = []
        path = remote_path

        # Build list of directories to create
        while path and path != '/':
            dirs.append(path)
            path = os.path.dirname(path)

        # Create directories from parent to child
        for directory in reversed(dirs):
            try:
                self.sftp_client.stat(directory)
            except FileNotFoundError:
                self.sftp_client.mkdir(directory)
                self.logger.info(f"Created remote directory: {directory}")

    def upload_file(self, local_path: str, remote_path: str, progress_callback: Callable = None) -> Tuple[bool, str]:
        """
        Upload a file to remote server

        Args:
            local_path: Local file path
            remote_path: Remote file path
            progress_callback: Optional callback for progress (bytes_transferred, total_bytes)

        Returns:
            Tuple of (success, message)
        """
        try:
            # Ensure remote directory exists
            remote_dir = os.path.dirname(remote_path)
            if remote_dir:
                self.mkdir_recursive(remote_dir)

            # Upload file
            file_size = os.path.getsize(local_path)

            def progress_wrapper(bytes_transferred, total_bytes):
                if progress_callback:
                    progress_callback(bytes_transferred, total_bytes)

            self.sftp_client.put(local_path, remote_path, callback=progress_wrapper if progress_callback else None)

            # Preserve file permissions
            local_stat = os.stat(local_path)
            try:
                self.sftp_client.chmod(remote_path, local_stat.st_mode)
            except:
                pass  # Some servers don't allow chmod

            self.logger.info(f"Uploaded: {local_path} -> {remote_path} ({self._format_bytes(file_size)})")
            return True, f"Uploaded {os.path.basename(local_path)}"

        except Exception as e:
            error_msg = f"Failed to upload {local_path}: {e}"
            self.logger.error(error_msg)
            return False, error_msg

    def download_file(self, remote_path: str, local_path: str, progress_callback: Callable = None) -> Tuple[bool, str]:
        """
        Download a file from remote server

        Args:
            remote_path: Remote file path
            local_path: Local file path
            progress_callback: Optional callback for progress

        Returns:
            Tuple of (success, message)
        """
        try:
            # Ensure local directory exists
            local_dir = os.path.dirname(local_path)
            if local_dir:
                os.makedirs(local_dir, exist_ok=True)

            # Download file
            def progress_wrapper(bytes_transferred, total_bytes):
                if progress_callback:
                    progress_callback(bytes_transferred, total_bytes)

            self.sftp_client.get(remote_path, local_path, callback=progress_wrapper if progress_callback else None)

            file_size = os.path.getsize(local_path)
            self.logger.info(f"Downloaded: {remote_path} -> {local_path} ({self._format_bytes(file_size)})")
            return True, f"Downloaded {os.path.basename(local_path)}"

        except Exception as e:
            error_msg = f"Failed to download {remote_path}: {e}"
            self.logger.error(error_msg)
            return False, error_msg

    def list_files_recursive(self, remote_path: str, start_date: datetime = None, end_date: datetime = None) -> List[Tuple[str, datetime]]:
        """
        List all files recursively in a remote directory with modification dates

        Args:
            remote_path: Remote directory path
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            List of tuples (file_path, modification_date)
        """
        files = []

        def recurse(path):
            try:
                for item in self.sftp_client.listdir_attr(path):
                    item_path = os.path.join(path, item.filename)

                    if stat.S_ISDIR(item.st_mode):
                        # It's a directory, recurse into it
                        recurse(item_path)
                    elif stat.S_ISREG(item.st_mode):
                        # It's a file
                        mod_time = datetime.fromtimestamp(item.st_mtime)

                        # Apply date filter if provided
                        if start_date and mod_time < start_date:
                            continue
                        if end_date and mod_time > end_date:
                            continue

                        files.append((item_path, mod_time))

            except Exception as e:
                self.logger.error(f"Error listing {path}: {e}")

        recurse(remote_path)
        self.logger.info(f"Found {len(files)} files in {remote_path}")
        return files

    def path_exists(self, remote_path: str) -> bool:
        """Check if a remote path exists"""
        try:
            self.sftp_client.stat(remote_path)
            return True
        except FileNotFoundError:
            return False

    def get_remote_mtime(self, remote_path: str) -> float:
        """
        Get modification time of a remote file

        Args:
            remote_path: Remote file path

        Returns:
            Modification time as float (seconds since epoch), or 0 if file doesn't exist
        """
        try:
            stat_info = self.sftp_client.stat(remote_path)
            return stat_info.st_mtime
        except FileNotFoundError:
            return 0

    def is_local_newer(self, local_path: str, remote_path: str) -> bool:
        """
        Check if local file is newer than remote file

        Args:
            local_path: Local file path
            remote_path: Remote file path

        Returns:
            True if local file is newer or remote doesn't exist, False otherwise
        """
        try:
            # Get local file modification time
            local_mtime = os.path.getmtime(local_path)

            # Get remote file modification time (0 if doesn't exist)
            remote_mtime = self.get_remote_mtime(remote_path)

            # If remote doesn't exist, local is "newer"
            if remote_mtime == 0:
                return True

            # Compare modification times
            return local_mtime > remote_mtime

        except Exception as e:
            self.logger.warning(f"Error comparing file times for {local_path}: {e}")
            # On error, assume we should upload
            return True

    def is_remote_newer(self, remote_path: str, local_path: str) -> bool:
        """
        Check if remote file is newer than local file

        Args:
            remote_path: Remote file path
            local_path: Local file path

        Returns:
            True if remote file is newer or local doesn't exist, False otherwise
        """
        try:
            # Get remote file modification time
            remote_mtime = self.get_remote_mtime(remote_path)

            # If remote doesn't exist, we shouldn't pull it
            if remote_mtime == 0:
                return False

            # Get local file modification time (0 if doesn't exist)
            if not os.path.exists(local_path):
                return True

            local_mtime = os.path.getmtime(local_path)

            # Compare modification times
            return remote_mtime > local_mtime

        except Exception as e:
            self.logger.warning(f"Error comparing file times for {remote_path}: {e}")
            # On error, assume we should download
            return True

    def _format_bytes(self, bytes_size: int) -> str:
        """Format bytes to human-readable string"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.1f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.1f} TB"

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()

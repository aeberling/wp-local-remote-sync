"""
SSH service for remote command execution
"""
import paramiko
from typing import Tuple, Optional
from ..utils.logger import setup_logger


class SSHService:
    """Handles SSH operations for remote command execution"""

    def __init__(self, host: str, port: int, username: str, password: str = None, key_path: str = None):
        """
        Initialize SSH service

        Args:
            host: SSH server hostname
            port: SSH server port
            username: SSH username
            password: SSH password (optional if using key)
            key_path: Path to SSH private key (optional)
        """
        self.logger = setup_logger('ssh')
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.key_path = key_path

        self.ssh_client = None

    def connect(self):
        """Establish SSH connection"""
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

            self.logger.info("SSH connection established")
            return True

        except Exception as e:
            self.logger.error(f"Failed to connect: {e}")
            raise ConnectionError(f"Failed to connect to SSH server: {e}")

    def disconnect(self):
        """Close SSH connection"""
        try:
            if self.ssh_client:
                self.ssh_client.close()
            self.logger.info("SSH connection closed")
        except Exception as e:
            self.logger.error(f"Error closing connection: {e}")

    def execute_command(self, command: str, timeout: int = 300) -> Tuple[bool, str, str]:
        """
        Execute a command on remote server

        Args:
            command: Shell command to execute
            timeout: Command timeout in seconds (default 5 minutes)

        Returns:
            Tuple of (success, stdout, stderr)
        """
        try:
            if not self.ssh_client:
                raise ConnectionError("Not connected to SSH server")

            self.logger.info(f"Executing command: {command}")

            stdin, stdout, stderr = self.ssh_client.exec_command(command, timeout=timeout)

            # Get exit status
            exit_status = stdout.channel.recv_exit_status()

            # Read output
            stdout_text = stdout.read().decode('utf-8')
            stderr_text = stderr.read().decode('utf-8')

            success = exit_status == 0

            if success:
                self.logger.info(f"Command completed successfully")
            else:
                self.logger.error(f"Command failed with exit status {exit_status}")
                self.logger.error(f"stderr: {stderr_text}")

            return success, stdout_text, stderr_text

        except Exception as e:
            error_msg = f"Error executing command: {e}"
            self.logger.error(error_msg)
            return False, "", str(e)

    def test_wp_cli(self, wordpress_path: str) -> Tuple[bool, str]:
        """
        Test if WP-CLI is available on remote server

        Args:
            wordpress_path: Remote WordPress installation path

        Returns:
            Tuple of (available, version_string)
        """
        try:
            command = f"cd {wordpress_path} && wp --version"
            success, stdout, stderr = self.execute_command(command, timeout=30)

            if success:
                version = stdout.strip()
                self.logger.info(f"WP-CLI found: {version}")
                return True, version
            else:
                self.logger.warning("WP-CLI not found on remote server")
                return False, stderr

        except Exception as e:
            error_msg = f"Error testing WP-CLI: {e}"
            self.logger.error(error_msg)
            return False, error_msg

    def test_connection(self) -> Tuple[bool, str]:
        """
        Test SSH connection

        Returns:
            Tuple of (success, message)
        """
        try:
            self.connect()
            # Test with simple command
            success, stdout, stderr = self.execute_command("echo 'Connection successful'", timeout=10)
            self.disconnect()

            if success:
                return True, "Connection successful"
            else:
                return False, stderr

        except Exception as e:
            return False, str(e)

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()

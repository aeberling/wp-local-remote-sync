"""
Database service for WordPress database operations
"""
import subprocess
import shlex
import os
import tempfile
from typing import Tuple, List, Optional
from datetime import datetime
from ..models.site_config import SiteConfig
from .ssh_service import SSHService
from ..utils.logger import setup_logger


class DatabaseService:
    """Handles WordPress database operations using WP-CLI"""

    def __init__(self, site_config: SiteConfig, ssh_service: SSHService = None):
        """
        Initialize database service

        Args:
            site_config: Site configuration
            ssh_service: Optional SSH service for remote operations
        """
        self.logger = setup_logger('database')
        self.site_config = site_config
        self.ssh_service = ssh_service

        if not site_config.database_config:
            raise ValueError("Site configuration does not have database configuration")

        self.db_config = site_config.database_config

    def _get_local_mysql_path(self) -> Optional[str]:
        """
        Detect and return Local by Flywheel MySQL path if available

        Returns:
            MySQL bin path or None if not using Local
        """
        try:
            import platform
            if platform.system() == 'Darwin':  # macOS
                local_services_path = os.path.expanduser("~/Library/Application Support/Local/lightning-services")

                if os.path.exists(local_services_path):
                    # Find MySQL directories
                    mysql_dirs = [d for d in os.listdir(local_services_path) if d.startswith('mysql-')]

                    if mysql_dirs:
                        # Sort and get the latest version
                        mysql_dirs.sort(reverse=True)
                        latest_mysql = mysql_dirs[0]

                        # Construct path to MySQL bin
                        mysql_bin_path = os.path.join(
                            local_services_path,
                            latest_mysql,
                            'bin/darwin-arm64/bin'
                        )

                        # Also check intel path
                        if not os.path.exists(mysql_bin_path):
                            mysql_bin_path = os.path.join(
                                local_services_path,
                                latest_mysql,
                                'bin/darwin/bin'
                            )

                        if os.path.exists(mysql_bin_path):
                            self.logger.info(f"Using Local by Flywheel MySQL from: {mysql_bin_path}")
                            return mysql_bin_path
        except Exception as e:
            self.logger.debug(f"Could not detect Local MySQL: {e}")

        return None

    def _get_mysql_socket_path(self) -> Optional[str]:
        """
        Detect MySQL socket path for Local by Flywheel or system MySQL

        Returns:
            Socket path or None if not found
        """
        try:
            import platform
            if platform.system() == 'Darwin':  # macOS
                # Check Local by Flywheel socket locations
                # Local stores sockets in site-specific directories
                local_sites_path = os.path.expanduser("~/Library/Application Support/Local/run")
                
                if os.path.exists(local_sites_path):
                    # Look for socket files in Local's run directory
                    for item in os.listdir(local_sites_path):
                        item_path = os.path.join(local_sites_path, item)
                        if os.path.isdir(item_path):
                            # Check for mysql.sock in subdirectories
                            socket_path = os.path.join(item_path, "mysql.sock")
                            if os.path.exists(socket_path):
                                self.logger.info(f"Found Local MySQL socket at: {socket_path}")
                                return socket_path
                            
                            # Also check for mysql.sock in the root of run directory
                            root_socket = os.path.join(local_sites_path, "mysql.sock")
                            if os.path.exists(root_socket):
                                self.logger.info(f"Found Local MySQL socket at: {root_socket}")
                                return root_socket
                
                # Check if we can determine socket from Local site path
                # Local sites are typically in ~/Local Sites/
                local_sites_dir = os.path.expanduser("~/Local Sites")
                if os.path.exists(local_sites_dir) and self.site_config.local_path:
                    # Try to extract site name from local_path
                    # e.g., "/Users/name/Local Sites/mysite/app/public" -> "mysite"
                    path_parts = self.site_config.local_path.split(os.sep)
                    if "Local Sites" in path_parts:
                        idx = path_parts.index("Local Sites")
                        if idx + 1 < len(path_parts):
                            site_name = path_parts[idx + 1]
                            site_socket = os.path.join(
                                local_sites_path, 
                                site_name.replace(" ", "-").lower(),
                                "mysql.sock"
                            )
                            if os.path.exists(site_socket):
                                self.logger.info(f"Found Local MySQL socket for site at: {site_socket}")
                                return site_socket
                
                # Check common system MySQL socket locations
                common_sockets = [
                    "/tmp/mysql.sock",
                    "/var/mysql/mysql.sock",
                    "/var/run/mysqld/mysqld.sock",
                ]
                
                for socket_path in common_sockets:
                    if os.path.exists(socket_path):
                        self.logger.info(f"Found MySQL socket at: {socket_path}")
                        return socket_path
                        
        except Exception as e:
            self.logger.debug(f"Could not detect MySQL socket: {e}")

        return None

    def _get_mysql_connection_params(self) -> dict:
        """
        Get MySQL connection parameters from wp-config.php or database config
        
        Returns:
            Dictionary with connection parameters for MySQL client tools
        """
        params = {}
        
        try:
            # Try to read from wp-config.php
            wp_config_path = os.path.join(self.site_config.local_path, 'wp-config.php')
            if os.path.exists(wp_config_path):
                from ..utils.wp_config_parser import WPConfigParser
                config = WPConfigParser.parse_file(wp_config_path)
                
                db_host = config.get('db_host', 'localhost')
                
                # If host is localhost, check if we should use socket or TCP/IP
                if db_host == 'localhost' or db_host.startswith('localhost:'):
                    socket_path = self._get_mysql_socket_path()
                    if socket_path:
                        # Use socket connection - mysqldump will use this
                        params['MYSQL_UNIX_PORT'] = socket_path
                        self.logger.info(f"Using MySQL socket: {socket_path}")
                    else:
                        # No socket found - try to force TCP/IP
                        # Note: WP-CLI reads from wp-config.php, so this might not work
                        # But we can try setting environment variables that mysqldump might respect
                        self.logger.warning(
                            "MySQL socket not found. WP-CLI may fail to connect. "
                            "Consider updating wp-config.php DB_HOST to '127.0.0.1' for TCP/IP connection."
                        )
                        # Try to use TCP/IP - but WP-CLI might still use socket
                        # This is a best-effort attempt
                        params['MYSQL_TCP_PORT'] = '3306'
                elif ':' in db_host:
                    # Host includes port (e.g., "127.0.0.1:3306" or "localhost:3306")
                    host, port = db_host.split(':', 1)
                    if host == 'localhost':
                        # Even if specified as localhost:port, try socket first
                        socket_path = self._get_mysql_socket_path()
                        if socket_path:
                            params['MYSQL_UNIX_PORT'] = socket_path
                        else:
                            params['MYSQL_TCP_PORT'] = port
                    else:
                        params['MYSQL_TCP_PORT'] = port
                else:
                    # Explicit host (not localhost)
                    params['MYSQL_TCP_PORT'] = '3306'
                    
        except Exception as e:
            self.logger.debug(f"Could not get MySQL connection params: {e}")
        
        return params

    def _execute_local_command(self, command: str, timeout: int = 300) -> Tuple[bool, str, str]:
        """
        Execute a command locally

        Args:
            command: Command to execute
            timeout: Command timeout in seconds

        Returns:
            Tuple of (success, stdout, stderr)
        """
        try:
            self.logger.info(f"Executing local command: {command}")

            # Prepare environment with Local's MySQL if available
            env = os.environ.copy()
            mysql_path = self._get_local_mysql_path()

            if mysql_path:
                # Prepend Local's MySQL to PATH
                current_path = env.get('PATH', '')
                env['PATH'] = f"{mysql_path}:{current_path}"

            # Set MySQL connection parameters to handle socket issues
            mysql_params = self._get_mysql_connection_params()
            env.update(mysql_params)

            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.site_config.local_path,
                env=env
            )

            success = result.returncode == 0

            if success:
                self.logger.info("Command completed successfully")
            else:
                self.logger.error(f"Command failed with return code {result.returncode}")
                self.logger.error(f"stderr: {result.stderr}")

            return success, result.stdout, result.stderr

        except subprocess.TimeoutExpired:
            error_msg = f"Command timed out after {timeout} seconds"
            self.logger.error(error_msg)
            return False, "", error_msg
        except Exception as e:
            error_msg = f"Error executing command: {e}"
            self.logger.error(error_msg)
            return False, "", str(e)

    def verify_wp_cli_local(self) -> Tuple[bool, str]:
        """
        Verify WP-CLI is installed and accessible locally

        Returns:
            Tuple of (available, version_or_error)
        """
        success, stdout, stderr = self._execute_local_command("wp --version", timeout=10)

        if success:
            version = stdout.strip()
            self.logger.info(f"WP-CLI found locally: {version}")
            return True, version
        else:
            error_msg = "WP-CLI not found locally. Please install WP-CLI: https://wp-cli.org/"
            self.logger.error(error_msg)
            return False, error_msg

    def verify_wp_cli_remote(self) -> Tuple[bool, str]:
        """
        Verify WP-CLI is installed and accessible on remote server

        Returns:
            Tuple of (available, version_or_error)
        """
        if not self.ssh_service:
            return False, "SSH service not configured"

        return self.ssh_service.test_wp_cli(self.site_config.remote_path)

    def export_local_database(self, output_path: str, exclude_tables: List[str] = None) -> Tuple[bool, str]:
        """
        Export local WordPress database using WP-CLI

        Args:
            output_path: Local path to save SQL dump
            exclude_tables: Tables to exclude from export

        Returns:
            Tuple of (success, message)
        """
        try:
            # Build command
            command = f"wp db export {shlex.quote(output_path)}"

            if exclude_tables:
                tables_arg = ','.join(exclude_tables)
                command += f" --exclude_tables={shlex.quote(tables_arg)}"

            command += " --add-drop-table"

            # Execute command
            success, stdout, stderr = self._execute_local_command(command)

            if success:
                file_size = os.path.getsize(output_path)
                msg = f"Exported local database to {output_path} ({self._format_bytes(file_size)})"
                self.logger.info(msg)
                return True, msg
            else:
                # Check if this is a socket connection error
                error_msg = stderr
                if "Can't connect to local MySQL server through socket" in stderr or "mysql.sock" in stderr:
                    # Provide helpful guidance
                    wp_config_path = os.path.join(self.site_config.local_path, 'wp-config.php')
                    guidance = (
                        f"\n\nMySQL socket connection failed. To fix this:\n"
                        f"1. Open {wp_config_path}\n"
                        f"2. Find the line: define('DB_HOST', 'localhost');\n"
                        f"3. Change it to: define('DB_HOST', '127.0.0.1');\n"
                        f"   (This forces TCP/IP connection instead of socket)\n"
                        f"4. Save the file and try again.\n"
                        f"\nAlternatively, ensure your MySQL server is running and the socket file exists."
                    )
                    error_msg = f"Failed to export local database: {stderr}{guidance}"
                
                return False, error_msg

        except Exception as e:
            error_msg = f"Error exporting local database: {e}"
            self.logger.error(error_msg)
            return False, error_msg

    def import_local_database(self, sql_file: str, backup_first: bool = True) -> Tuple[bool, str]:
        """
        Import database to local WordPress installation

        Args:
            sql_file: Path to SQL dump file
            backup_first: Create backup before import

        Returns:
            Tuple of (success, message)
        """
        try:
            backup_file = None

            # Create backup if requested
            if backup_first:
                timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                backup_file = f"local-backup-{timestamp}.sql"
                backup_path = os.path.join(tempfile.gettempdir(), backup_file)

                self.logger.info(f"Creating backup before import: {backup_path}")
                success, msg = self.export_local_database(backup_path)

                if not success:
                    return False, f"Failed to create backup: {msg}"

            # Import database
            command = f"wp db import {shlex.quote(sql_file)}"
            success, stdout, stderr = self._execute_local_command(command)

            if success:
                msg = f"Successfully imported database from {sql_file}"
                if backup_file:
                    msg += f" (backup: {backup_file})"
                self.logger.info(msg)
                return True, msg
            else:
                return False, f"Failed to import database: {stderr}"

        except Exception as e:
            error_msg = f"Error importing local database: {e}"
            self.logger.error(error_msg)
            return False, error_msg

    def export_remote_database(self, output_filename: str, exclude_tables: List[str] = None) -> Tuple[bool, str]:
        """
        Export remote database using WP-CLI via SSH

        Args:
            output_filename: Filename for SQL dump on remote server
            exclude_tables: Tables to exclude from export

        Returns:
            Tuple of (success, message)
        """
        try:
            if not self.ssh_service:
                return False, "SSH service not configured"

            # Build command
            command = f"cd {shlex.quote(self.site_config.remote_path)} && "
            command += f"wp db export {shlex.quote(output_filename)}"

            if exclude_tables:
                tables_arg = ','.join(exclude_tables)
                command += f" --exclude_tables={shlex.quote(tables_arg)}"

            command += " --add-drop-table"

            # Execute command
            success, stdout, stderr = self.ssh_service.execute_command(command)

            if success:
                msg = f"Exported remote database to {output_filename}"
                self.logger.info(msg)
                return True, msg
            else:
                return False, f"Failed to export remote database: {stderr}"

        except Exception as e:
            error_msg = f"Error exporting remote database: {e}"
            self.logger.error(error_msg)
            return False, error_msg

    def import_remote_database(self, sql_filename: str, backup_first: bool = True) -> Tuple[bool, str]:
        """
        Import database to remote WordPress installation

        Args:
            sql_filename: Filename of SQL dump on remote server
            backup_first: Create backup before import

        Returns:
            Tuple of (success, message)
        """
        try:
            if not self.ssh_service:
                return False, "SSH service not configured"

            backup_file = None

            # Create backup if requested
            if backup_first:
                timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                backup_file = f"remote-backup-{timestamp}.sql"

                self.logger.info(f"Creating remote backup before import: {backup_file}")
                success, msg = self.export_remote_database(backup_file)

                if not success:
                    return False, f"Failed to create remote backup: {msg}"

            # Import database
            command = f"cd {shlex.quote(self.site_config.remote_path)} && "
            command += f"wp db import {shlex.quote(sql_filename)}"

            success, stdout, stderr = self.ssh_service.execute_command(command)

            if success:
                msg = f"Successfully imported database to remote from {sql_filename}"
                if backup_file:
                    msg += f" (backup: {backup_file})"
                self.logger.info(msg)
                return True, msg
            else:
                return False, f"Failed to import remote database: {stderr}"

        except Exception as e:
            error_msg = f"Error importing remote database: {e}"
            self.logger.error(error_msg)
            return False, error_msg

    def search_replace_local(self, search: str, replace: str, dry_run: bool = False) -> Tuple[bool, str, dict]:
        """
        Search and replace in local database (handles serialized data)

        Args:
            search: String to search for (e.g., old URL)
            replace: String to replace with (e.g., new URL)
            dry_run: If True, report changes without making them

        Returns:
            Tuple of (success, message, stats_dict)
        """
        try:
            stats = {'replacements': 0, 'tables': 0}

            # Build command with explicit table prefix to handle cases where
            # wp-config.php prefix doesn't match the actual database tables
            command = f"wp search-replace {shlex.quote(search)} {shlex.quote(replace)}"
            command += " --all-tables-with-prefix"
            command += " --report-changed-only --format=count"

            if dry_run:
                command += " --dry-run"

            # Execute command
            success, stdout, stderr = self._execute_local_command(command)

            if success:
                try:
                    stats['replacements'] = int(stdout.strip())
                except:
                    stats['replacements'] = 0

                action = "would be replaced" if dry_run else "replaced"
                msg = f"Search-replace: {stats['replacements']} instances {action}"
                self.logger.info(msg)
                return True, msg, stats
            else:
                return False, f"Failed to search-replace: {stderr}", stats

        except Exception as e:
            error_msg = f"Error in search-replace: {e}"
            self.logger.error(error_msg)
            return False, error_msg, stats

    def search_replace_remote(self, search: str, replace: str, dry_run: bool = False) -> Tuple[bool, str, dict]:
        """
        Search and replace in remote database via SSH

        Args:
            search: String to search for
            replace: String to replace with
            dry_run: If True, report changes without making them

        Returns:
            Tuple of (success, message, stats_dict)
        """
        try:
            if not self.ssh_service:
                return False, "SSH service not configured", {}

            stats = {'replacements': 0, 'tables': 0}

            # Build command with explicit table prefix to handle cases where
            # wp-config.php prefix doesn't match the actual database tables
            command = f"cd {shlex.quote(self.site_config.remote_path)} && "
            command += f"wp search-replace {shlex.quote(search)} {shlex.quote(replace)}"
            command += " --all-tables-with-prefix"
            command += " --report-changed-only --format=count"

            if dry_run:
                command += " --dry-run"

            # Execute command
            success, stdout, stderr = self.ssh_service.execute_command(command)

            if success:
                try:
                    stats['replacements'] = int(stdout.strip())
                except:
                    stats['replacements'] = 0

                action = "would be replaced" if dry_run else "replaced"
                msg = f"Remote search-replace: {stats['replacements']} instances {action}"
                self.logger.info(msg)
                return True, msg, stats
            else:
                return False, f"Failed to search-replace on remote: {stderr}", stats

        except Exception as e:
            error_msg = f"Error in remote search-replace: {e}"
            self.logger.error(error_msg)
            return False, error_msg, stats

    def get_local_table_list(self) -> Tuple[bool, List[str]]:
        """
        Get list of tables in local database

        Returns:
            Tuple of (success, table_list)
        """
        try:
            command = "wp db tables --format=csv"
            success, stdout, stderr = self._execute_local_command(command, timeout=30)

            if success:
                tables = [table.strip() for table in stdout.split('\n') if table.strip()]
                self.logger.info(f"Found {len(tables)} tables in local database")
                return True, tables
            else:
                return False, []

        except Exception as e:
            self.logger.error(f"Error getting local table list: {e}")
            return False, []

    def get_remote_table_list(self) -> Tuple[bool, List[str]]:
        """
        Get list of tables in remote database via SSH

        Returns:
            Tuple of (success, table_list)
        """
        try:
            if not self.ssh_service:
                return False, []

            command = f"cd {shlex.quote(self.site_config.remote_path)} && wp db tables --format=csv"
            success, stdout, stderr = self.ssh_service.execute_command(command, timeout=30)

            if success:
                tables = [table.strip() for table in stdout.split('\n') if table.strip()]
                self.logger.info(f"Found {len(tables)} tables in remote database")
                return True, tables
            else:
                return False, []

        except Exception as e:
            self.logger.error(f"Error getting remote table list: {e}")
            return False, []

    def _format_bytes(self, bytes_size: int) -> str:
        """Format bytes to human-readable string"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.1f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.1f} TB"

    def replace_table_prefix_in_sql(self, sql_file: str, old_prefix: str, new_prefix: str) -> Tuple[bool, str]:
        """
        Replace table prefix in SQL dump file

        Args:
            sql_file: Path to SQL file
            old_prefix: Old table prefix (e.g., 'wp_')
            new_prefix: New table prefix (e.g., 'wpmu_')

        Returns:
            Tuple of (success, message)
        """
        try:
            if old_prefix == new_prefix:
                return True, "Table prefixes are the same, no changes needed"

            self.logger.info(f"Replacing table prefix in {sql_file}: {old_prefix} -> {new_prefix}")

            # Read SQL file
            with open(sql_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Replace table names in common SQL commands
            import re

            # Match table names in various SQL contexts
            patterns = [
                # CREATE TABLE
                (rf'CREATE TABLE (`|"){old_prefix}', rf'CREATE TABLE \1{new_prefix}'),
                # DROP TABLE
                (rf'DROP TABLE IF EXISTS (`|"){old_prefix}', rf'DROP TABLE IF EXISTS \1{new_prefix}'),
                # INSERT INTO
                (rf'INSERT INTO (`|"){old_prefix}', rf'INSERT INTO \1{new_prefix}'),
                # LOCK TABLES
                (rf'LOCK TABLES (`|"){old_prefix}', rf'LOCK TABLES \1{new_prefix}'),
                # UNLOCK TABLES
                (rf'UNLOCK TABLES (`|"){old_prefix}', rf'UNLOCK TABLES \1{new_prefix}'),
                # ALTER TABLE
                (rf'ALTER TABLE (`|"){old_prefix}', rf'ALTER TABLE \1{new_prefix}'),
                # References in constraints and keys
                (rf'REFERENCES (`|"){old_prefix}', rf'REFERENCES \1{new_prefix}'),
            ]

            replacements = 0
            for pattern, replacement in patterns:
                content, count = re.subn(pattern, replacement, content)
                replacements += count

            # Write modified content back
            with open(sql_file, 'w', encoding='utf-8') as f:
                f.write(content)

            msg = f"Replaced table prefix in SQL file: {replacements} replacements"
            self.logger.info(msg)
            return True, msg

        except Exception as e:
            error_msg = f"Error replacing table prefix in SQL file: {e}"
            self.logger.error(error_msg)
            return False, error_msg

    def update_wp_options_prefix(self, old_prefix: str, new_prefix: str, remote: bool = False) -> Tuple[bool, str]:
        """
        Update WordPress options and usermeta tables to reflect new table prefix

        This updates:
        1. Option names in wp_options that reference the old prefix
           (e.g., wp_user_roles -> wpmu_user_roles)
        2. User meta keys in wp_usermeta that reference the old prefix
           (e.g., wp_capabilities -> wpmu_capabilities)

        Args:
            old_prefix: Old table prefix
            new_prefix: New table prefix
            remote: If True, update on remote server

        Returns:
            Tuple of (success, message)
        """
        try:
            if old_prefix == new_prefix:
                return True, "Table prefixes are the same, no changes needed"

            self.logger.info(f"Updating WordPress options and usermeta for prefix change: {old_prefix} -> {new_prefix}")

            target = "remote" if remote else "local"

            # Update option names in wp_options table
            sql_query_options = f"UPDATE {new_prefix}options SET option_name = REPLACE(option_name, '{old_prefix}', '{new_prefix}') WHERE option_name LIKE '{old_prefix}%'"

            # Update meta keys in wp_usermeta table (CRITICAL for user capabilities!)
            sql_query_usermeta = f"UPDATE {new_prefix}usermeta SET meta_key = REPLACE(meta_key, '{old_prefix}', '{new_prefix}') WHERE meta_key LIKE '{old_prefix}%'"

            # Combine both queries
            combined_query = f"{sql_query_options}; {sql_query_usermeta};"

            if remote:
                command = f"cd {shlex.quote(self.site_config.remote_path)} && wp db query {shlex.quote(combined_query)}"
                success, stdout, stderr = self.ssh_service.execute_command(command)
            else:
                command = f"wp db query {shlex.quote(combined_query)}"
                success, stdout, stderr = self._execute_local_command(command)

            if success:
                msg = f"Updated WordPress options and usermeta for {target} database"
                self.logger.info(msg)
                return True, msg
            else:
                return False, f"Failed to update WordPress options/usermeta: {stderr}"

        except Exception as e:
            error_msg = f"Error updating WordPress options/usermeta: {e}"
            self.logger.error(error_msg)
            return False, error_msg

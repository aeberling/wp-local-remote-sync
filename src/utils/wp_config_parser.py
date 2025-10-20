"""
WordPress wp-config.php parser utility
"""
import re
import os
from typing import Dict, Optional, Tuple


class WPConfigParser:
    """Parse WordPress wp-config.php files to extract database configuration"""

    @staticmethod
    def parse_file(file_path: str) -> Dict[str, str]:
        """
        Parse a wp-config.php file and extract database configuration

        Args:
            file_path: Path to wp-config.php file

        Returns:
            Dictionary with database configuration
        """
        config = {
            'db_name': '',
            'db_user': '',
            'db_password': '',
            'db_host': 'localhost',
            'table_prefix': 'wp_',
            'site_url': '',
            'home_url': ''
        }

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"wp-config.php not found at: {file_path}")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Extract database name
            match = re.search(r"define\s*\(\s*['\"]DB_NAME['\"]\s*,\s*['\"]([^'\"]+)['\"]\s*\)", content)
            if match:
                config['db_name'] = match.group(1)

            # Extract database user
            match = re.search(r"define\s*\(\s*['\"]DB_USER['\"]\s*,\s*['\"]([^'\"]+)['\"]\s*\)", content)
            if match:
                config['db_user'] = match.group(1)

            # Extract database password
            match = re.search(r"define\s*\(\s*['\"]DB_PASSWORD['\"]\s*,\s*['\"]([^'\"]+)['\"]\s*\)", content)
            if match:
                config['db_password'] = match.group(1)

            # Extract database host
            match = re.search(r"define\s*\(\s*['\"]DB_HOST['\"]\s*,\s*['\"]([^'\"]+)['\"]\s*\)", content)
            if match:
                config['db_host'] = match.group(1)

            # Extract table prefix
            match = re.search(r"\$table_prefix\s*=\s*['\"]([^'\"]+)['\"]\s*;", content)
            if match:
                config['table_prefix'] = match.group(1)

            # Extract WP_SITEURL if defined
            match = re.search(r"define\s*\(\s*['\"]WP_SITEURL['\"]\s*,\s*['\"]([^'\"]+)['\"]\s*\)", content)
            if match:
                config['site_url'] = match.group(1)

            # Extract WP_HOME if defined
            match = re.search(r"define\s*\(\s*['\"]WP_HOME['\"]\s*,\s*['\"]([^'\"]+)['\"]\s*\)", content)
            if match:
                config['home_url'] = match.group(1)

            return config

        except Exception as e:
            raise Exception(f"Error parsing wp-config.php: {e}")

    @staticmethod
    def parse_remote_file(file_content: str) -> Dict[str, str]:
        """
        Parse wp-config.php content from remote server

        Args:
            file_content: Content of wp-config.php file as string

        Returns:
            Dictionary with database configuration
        """
        config = {
            'db_name': '',
            'db_user': '',
            'db_password': '',
            'db_host': 'localhost',
            'table_prefix': 'wp_',
            'site_url': '',
            'home_url': ''
        }

        try:
            # Extract database name
            match = re.search(r"define\s*\(\s*['\"]DB_NAME['\"]\s*,\s*['\"]([^'\"]+)['\"]\s*\)", file_content)
            if match:
                config['db_name'] = match.group(1)

            # Extract database user
            match = re.search(r"define\s*\(\s*['\"]DB_USER['\"]\s*,\s*['\"]([^'\"]+)['\"]\s*\)", file_content)
            if match:
                config['db_user'] = match.group(1)

            # Extract database password
            match = re.search(r"define\s*\(\s*['\"]DB_PASSWORD['\"]\s*,\s*['\"]([^'\"]+)['\"]\s*\)", file_content)
            if match:
                config['db_password'] = match.group(1)

            # Extract database host
            match = re.search(r"define\s*\(\s*['\"]DB_HOST['\"]\s*,\s*['\"]([^'\"]+)['\"]\s*\)", file_content)
            if match:
                config['db_host'] = match.group(1)

            # Extract table prefix
            match = re.search(r"\$table_prefix\s*=\s*['\"]([^'\"]+)['\"]\s*;", file_content)
            if match:
                config['table_prefix'] = match.group(1)

            # Extract WP_SITEURL if defined
            match = re.search(r"define\s*\(\s*['\"]WP_SITEURL['\"]\s*,\s*['\"]([^'\"]+)['\"]\s*\)", file_content)
            if match:
                config['site_url'] = match.group(1)

            # Extract WP_HOME if defined
            match = re.search(r"define\s*\(\s*['\"]WP_HOME['\"]\s*,\s*['\"]([^'\"]+)['\"]\s*\)", file_content)
            if match:
                config['home_url'] = match.group(1)

            return config

        except Exception as e:
            raise Exception(f"Error parsing wp-config.php content: {e}")

    @staticmethod
    def get_site_url_from_wpcli(wordpress_path: str, remote: bool = False, ssh_command_executor=None) -> Optional[str]:
        """
        Get site URL using WP-CLI

        Args:
            wordpress_path: Path to WordPress installation
            remote: If True, execute remotely via SSH
            ssh_command_executor: Callable for executing remote SSH commands

        Returns:
            Site URL or None if failed
        """
        try:
            import subprocess

            if remote and ssh_command_executor:
                # Execute remotely
                command = f"cd {wordpress_path} && wp option get siteurl"
                success, stdout, stderr = ssh_command_executor(command)
                if success:
                    return stdout.strip()
            else:
                # Execute locally
                result = subprocess.run(
                    ['wp', 'option', 'get', 'siteurl'],
                    cwd=wordpress_path,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    return result.stdout.strip()

        except Exception:
            pass

        return None

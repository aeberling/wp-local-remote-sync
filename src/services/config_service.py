"""
Configuration service for managing site configurations
"""
import yaml
import keyring
import json
from pathlib import Path
from typing import List, Optional
from ..models.site_config import SiteConfig
from ..models.sync_state import SyncState, OperationState
from ..utils.logger import setup_logger


class ConfigService:
    """Manages site configurations and sync state"""

    def __init__(self):
        self.logger = setup_logger('config')
        self.config_dir = Path.home() / '.wp-deploy'
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self.sites_file = self.config_dir / 'sites.yaml'
        self.sync_state_file = self.config_dir / 'sync_state.json'

        # Initialize files if they don't exist
        if not self.sites_file.exists():
            self._save_sites([])
        if not self.sync_state_file.exists():
            self._save_sync_states({})

    def _save_sites(self, sites: List[SiteConfig]):
        """Save sites to YAML file"""
        data = {'sites': [site.to_dict() for site in sites]}
        with open(self.sites_file, 'w') as f:
            yaml.dump(data, f, default_flow_style=False)
        self.logger.info(f"Saved {len(sites)} site(s) to configuration")

    def _load_sites(self) -> List[SiteConfig]:
        """Load sites from YAML file"""
        try:
            with open(self.sites_file, 'r') as f:
                data = yaml.safe_load(f)
                if data and 'sites' in data:
                    return [SiteConfig.from_dict(site) for site in data['sites']]
                return []
        except Exception as e:
            self.logger.error(f"Error loading sites: {e}")
            return []

    def _save_sync_states(self, states: dict):
        """Save sync states to JSON file"""
        with open(self.sync_state_file, 'w') as f:
            json.dump(states, f, indent=2)

    def _load_sync_states(self) -> dict:
        """Load sync states from JSON file"""
        try:
            with open(self.sync_state_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Error loading sync states: {e}")
            return {}

    def add_site(self, site: SiteConfig, password: str = None):
        """Add a new site configuration"""
        sites = self._load_sites()

        # Check if site ID already exists
        if any(s.id == site.id for s in sites):
            raise ValueError(f"Site with ID {site.id} already exists")

        sites.append(site)
        self._save_sites(sites)

        # Store password in keyring if provided
        if password:
            self.set_password(site.id, password)

        self.logger.info(f"Added site: {site.name} ({site.id})")
        return site

    def update_site(self, site: SiteConfig):
        """Update an existing site configuration"""
        sites = self._load_sites()
        for i, s in enumerate(sites):
            if s.id == site.id:
                sites[i] = site
                self._save_sites(sites)
                self.logger.info(f"Updated site: {site.name} ({site.id})")
                return site

        raise ValueError(f"Site with ID {site.id} not found")

    def delete_site(self, site_id: str):
        """Delete a site configuration"""
        sites = self._load_sites()
        sites = [s for s in sites if s.id != site_id]
        self._save_sites(sites)

        # Remove passwords from keyring
        try:
            keyring.delete_password("wp-deploy", f"site-{site_id}")
        except:
            pass

        # Remove database passwords from keyring
        for db_type in ['local', 'remote']:
            try:
                keyring.delete_password("wp-deploy-db", f"{site_id}_{db_type}")
            except:
                pass

        self.logger.info(f"Deleted site: {site_id}")

    def get_site(self, site_id: str) -> Optional[SiteConfig]:
        """Get a site by ID"""
        sites = self._load_sites()
        for site in sites:
            if site.id == site_id:
                return site
        return None

    def get_all_sites(self) -> List[SiteConfig]:
        """Get all site configurations"""
        return self._load_sites()

    def set_password(self, site_id: str, password: str):
        """Store password in system keyring"""
        keyring.set_password("wp-deploy", f"site-{site_id}", password)
        self.logger.info(f"Password stored for site: {site_id}")

    def get_password(self, site_id: str) -> Optional[str]:
        """Retrieve password from system keyring"""
        try:
            return keyring.get_password("wp-deploy", f"site-{site_id}")
        except Exception as e:
            self.logger.error(f"Error retrieving password for {site_id}: {e}")
            return None

    def set_database_password(self, site_id: str, db_type: str, password: str):
        """
        Store database password in system keyring

        Args:
            site_id: Site identifier
            db_type: 'local' or 'remote'
            password: Database password
        """
        if db_type not in ['local', 'remote']:
            raise ValueError("db_type must be 'local' or 'remote'")

        keyring.set_password("wp-deploy-db", f"{site_id}_{db_type}", password)
        self.logger.info(f"Database password stored for site {site_id} ({db_type})")

    def get_database_password(self, site_id: str, db_type: str) -> Optional[str]:
        """
        Retrieve database password from system keyring

        Args:
            site_id: Site identifier
            db_type: 'local' or 'remote'

        Returns:
            Password string or None if not found
        """
        if db_type not in ['local', 'remote']:
            raise ValueError("db_type must be 'local' or 'remote'")

        try:
            return keyring.get_password("wp-deploy-db", f"{site_id}_{db_type}")
        except Exception as e:
            self.logger.error(f"Error retrieving database password for {site_id} ({db_type}): {e}")
            return None

    def update_last_pushed_commit(self, site_id: str, commit_hash: str):
        """Update the last pushed commit for a site"""
        site = self.get_site(site_id)
        if site:
            site.last_pushed_commit = commit_hash
            self.update_site(site)

    def get_sync_state(self, site_id: str) -> SyncState:
        """Get sync state for a site"""
        states = self._load_sync_states()
        if site_id in states:
            return SyncState.from_dict(site_id, states[site_id])
        return SyncState(site_id=site_id)

    def update_sync_state(self, sync_state: SyncState):
        """Update sync state for a site"""
        states = self._load_sync_states()
        states[sync_state.site_id] = sync_state.to_dict()
        self._save_sync_states(states)
        self.logger.info(f"Updated sync state for site: {sync_state.site_id}")

    def export_site_to_json(self, site_id: str, file_path: str) -> bool:
        """
        Export a site configuration to a JSON file, including credentials.

        Args:
            site_id: The ID of the site to export
            file_path: Path to save the JSON file

        Returns:
            True if export was successful, False otherwise
        """
        site = self.get_site(site_id)
        if not site:
            self.logger.error(f"Site not found: {site_id}")
            return False

        try:
            # Build export data with site config
            export_data = {
                'version': '1.0',
                'export_type': 'wp-deploy-site',
                'site': site.to_dict(),
                'credentials': {}
            }

            # Include SSH password if available
            ssh_password = self.get_password(site_id)
            if ssh_password:
                export_data['credentials']['ssh_password'] = ssh_password

            # Include database passwords if available
            local_db_password = self.get_database_password(site_id, 'local')
            if local_db_password:
                export_data['credentials']['local_db_password'] = local_db_password

            remote_db_password = self.get_database_password(site_id, 'remote')
            if remote_db_password:
                export_data['credentials']['remote_db_password'] = remote_db_password

            # Write to file
            with open(file_path, 'w') as f:
                json.dump(export_data, f, indent=2)

            self.logger.info(f"Exported site '{site.name}' to {file_path}")
            return True

        except Exception as e:
            self.logger.error(f"Error exporting site: {e}")
            return False

    def import_site_from_json(self, file_path: str) -> Optional[SiteConfig]:
        """
        Import a site configuration from a JSON file, including credentials.

        A new unique ID is generated for the imported site to avoid conflicts.

        Args:
            file_path: Path to the JSON file to import

        Returns:
            The imported SiteConfig if successful, None otherwise
        """
        import uuid
        from datetime import datetime

        try:
            with open(file_path, 'r') as f:
                import_data = json.load(f)

            # Validate export format
            if import_data.get('export_type') != 'wp-deploy-site':
                self.logger.error("Invalid export file format")
                return None

            site_data = import_data.get('site')
            if not site_data:
                self.logger.error("No site data found in export file")
                return None

            credentials = import_data.get('credentials', {})

            # Generate a new unique ID to avoid conflicts
            new_id = uuid.uuid4().hex[:8]
            site_data['id'] = new_id

            # Reset timestamps
            site_data['created_at'] = datetime.now().isoformat()
            site_data['updated_at'] = datetime.now().isoformat()

            # Reset sync tracking fields (these are specific to the original site)
            site_data['last_pushed_commit'] = ''
            site_data['last_db_pushed_at'] = ''
            site_data['last_db_pulled_at'] = ''

            # Create site config from data
            site = SiteConfig.from_dict(site_data)

            # Add the site (without password initially)
            self.add_site(site)

            # Store credentials in keyring
            if credentials.get('ssh_password'):
                self.set_password(new_id, credentials['ssh_password'])

            if credentials.get('local_db_password'):
                self.set_database_password(new_id, 'local', credentials['local_db_password'])

            if credentials.get('remote_db_password'):
                self.set_database_password(new_id, 'remote', credentials['remote_db_password'])

            self.logger.info(f"Imported site '{site.name}' with ID {new_id}")
            return site

        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in import file: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error importing site: {e}")
            return None

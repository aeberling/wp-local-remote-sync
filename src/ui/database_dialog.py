"""
Database configuration dialog
"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from ..models.database_config import DatabaseConfig


class DatabaseDialog:
    """Dialog for configuring database settings"""

    def __init__(self, parent, config_service, site):
        self.config_service = config_service
        self.site = site
        self.result = None

        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Database Configuration - {site.name}")
        self.dialog.geometry("800x700")

        self.create_widgets()

        if site.database_config:
            self.load_database_data()

        # Center dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (self.dialog.winfo_width() // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")

        # Better focus handling for macOS
        self.dialog.update_idletasks()
        self.dialog.lift()
        self.dialog.attributes('-topmost', True)
        self.dialog.update()
        self.dialog.attributes('-topmost', False)

        # Force event processing
        self.dialog.update()
        self.dialog.focus_force()

        # Set focus to first field
        self.local_db_name_entry.focus_set()

        # Bind Escape key to cancel
        self.dialog.bind('<Escape>', lambda e: self.cancel())

    def create_widgets(self):
        """Create dialog widgets"""
        # Main frame with scrollbar
        main_frame = ttk.Frame(self.dialog, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Canvas for scrolling
        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Local Database Section
        local_db_frame = ttk.LabelFrame(scrollable_frame, text="Local Database", padding=10)
        local_db_frame.pack(fill=tk.X, pady=5, padx=5)

        row = 0
        ttk.Label(local_db_frame, text="Database Name:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.local_db_name_entry = ttk.Entry(local_db_frame, width=40)
        self.local_db_name_entry.grid(row=row, column=1, sticky=tk.W, pady=5, padx=5)

        row += 1
        ttk.Label(local_db_frame, text="Host:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.local_db_host_entry = ttk.Entry(local_db_frame, width=40)
        self.local_db_host_entry.grid(row=row, column=1, sticky=tk.W, pady=5, padx=5)
        self.local_db_host_entry.insert(0, "localhost")

        row += 1
        ttk.Label(local_db_frame, text="Port:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.local_db_port_entry = ttk.Entry(local_db_frame, width=40)
        self.local_db_port_entry.grid(row=row, column=1, sticky=tk.W, pady=5, padx=5)
        self.local_db_port_entry.insert(0, "3306")

        row += 1
        ttk.Label(local_db_frame, text="Username:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.local_db_user_entry = ttk.Entry(local_db_frame, width=40)
        self.local_db_user_entry.grid(row=row, column=1, sticky=tk.W, pady=5, padx=5)
        self.local_db_user_entry.insert(0, "root")

        row += 1
        ttk.Label(local_db_frame, text="Password:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.local_db_password_entry = ttk.Entry(local_db_frame, width=40, show="*")
        self.local_db_password_entry.grid(row=row, column=1, sticky=tk.W, pady=5, padx=5)

        row += 1
        auto_detect_local_btn = ttk.Button(local_db_frame, text="🔍 Auto-detect from wp-config.php",
                                          command=self.auto_detect_local_database)
        auto_detect_local_btn.grid(row=row, column=0, columnspan=2, pady=10, ipady=5, ipadx=10)

        # Remote Database Section
        remote_db_frame = ttk.LabelFrame(scrollable_frame, text="Remote Database (via SSH)", padding=10)
        remote_db_frame.pack(fill=tk.X, pady=5, padx=5)

        row = 0
        ttk.Label(remote_db_frame, text="Database Name:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.remote_db_name_entry = ttk.Entry(remote_db_frame, width=40)
        self.remote_db_name_entry.grid(row=row, column=1, sticky=tk.W, pady=5, padx=5)

        row += 1
        ttk.Label(remote_db_frame, text="Host:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.remote_db_host_entry = ttk.Entry(remote_db_frame, width=40)
        self.remote_db_host_entry.grid(row=row, column=1, sticky=tk.W, pady=5, padx=5)
        self.remote_db_host_entry.insert(0, "localhost")
        ttk.Label(remote_db_frame, text="(Usually 'localhost' via SSH)", foreground="gray").grid(row=row, column=2, sticky=tk.W, padx=5)

        row += 1
        ttk.Label(remote_db_frame, text="Port:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.remote_db_port_entry = ttk.Entry(remote_db_frame, width=40)
        self.remote_db_port_entry.grid(row=row, column=1, sticky=tk.W, pady=5, padx=5)
        self.remote_db_port_entry.insert(0, "3306")

        row += 1
        ttk.Label(remote_db_frame, text="Username:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.remote_db_user_entry = ttk.Entry(remote_db_frame, width=40)
        self.remote_db_user_entry.grid(row=row, column=1, sticky=tk.W, pady=5, padx=5)

        row += 1
        ttk.Label(remote_db_frame, text="Password:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.remote_db_password_entry = ttk.Entry(remote_db_frame, width=40, show="*")
        self.remote_db_password_entry.grid(row=row, column=1, sticky=tk.W, pady=5, padx=5)

        row += 1
        auto_detect_remote_btn = ttk.Button(remote_db_frame, text="🔍 Auto-detect from wp-config.php",
                                           command=self.auto_detect_remote_database)
        auto_detect_remote_btn.grid(row=row, column=0, columnspan=2, pady=10, ipady=5, ipadx=10)

        # WordPress URLs Section
        urls_frame = ttk.LabelFrame(scrollable_frame, text="WordPress URLs", padding=10)
        urls_frame.pack(fill=tk.X, pady=5, padx=5)

        row = 0
        ttk.Label(urls_frame, text="Local URL:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.local_url_entry = ttk.Entry(urls_frame, width=40)
        self.local_url_entry.grid(row=row, column=1, sticky=tk.W, pady=5, padx=5)
        ttk.Label(urls_frame, text="e.g., http://mysite.local", foreground="gray").grid(row=row, column=2, sticky=tk.W, padx=5)

        row += 1
        ttk.Label(urls_frame, text="Remote URL:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.remote_url_entry = ttk.Entry(urls_frame, width=40)
        self.remote_url_entry.grid(row=row, column=1, sticky=tk.W, pady=5, padx=5)
        ttk.Label(urls_frame, text="e.g., https://mysite.com", foreground="gray").grid(row=row, column=2, sticky=tk.W, padx=5)

        # Advanced Options Section
        advanced_frame = ttk.LabelFrame(scrollable_frame, text="Advanced Options", padding=10)
        advanced_frame.pack(fill=tk.X, pady=5, padx=5)

        row = 0
        ttk.Label(advanced_frame, text="Exclude Tables:").grid(row=row, column=0, sticky=tk.NW, pady=5)
        ttk.Label(advanced_frame, text="(one per line)", foreground="gray").grid(row=row, column=1, sticky=tk.W, pady=5)

        row += 1
        self.exclude_tables_text = scrolledtext.ScrolledText(advanced_frame, width=50, height=6)
        self.exclude_tables_text.grid(row=row, column=0, columnspan=3, sticky=tk.W, pady=5, padx=5)

        # Add common examples
        default_excludes = "wp_users\nwp_usermeta"
        self.exclude_tables_text.insert('1.0', default_excludes)

        row += 1
        self.backup_before_import_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(advanced_frame, text="Create backup before import",
                       variable=self.backup_before_import_var).grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=5)

        row += 1
        self.require_confirmation_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(advanced_frame, text="Require confirmation when pushing to production",
                       variable=self.require_confirmation_var).grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=5)

        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Buttons
        button_frame = ttk.Frame(self.dialog, padding=10)
        button_frame.pack(fill=tk.X)

        ttk.Button(button_frame, text="Test Local Connection", command=self.test_local_connection).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Test Remote Connection", command=self.test_remote_connection).pack(side=tk.LEFT, padx=5)

        ttk.Button(button_frame, text="Save", command=self.save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.cancel).pack(side=tk.RIGHT, padx=5)

    def load_database_data(self):
        """Load existing database configuration into form"""
        db_config = self.site.database_config

        # Local database
        self.local_db_name_entry.delete(0, tk.END)
        self.local_db_name_entry.insert(0, db_config.local_db_name)

        self.local_db_host_entry.delete(0, tk.END)
        self.local_db_host_entry.insert(0, db_config.local_db_host)

        self.local_db_port_entry.delete(0, tk.END)
        self.local_db_port_entry.insert(0, str(db_config.local_db_port))

        self.local_db_user_entry.delete(0, tk.END)
        self.local_db_user_entry.insert(0, db_config.local_db_user)

        # Load password from keyring
        local_password = self.config_service.get_database_password(self.site.id, 'local')
        if local_password:
            self.local_db_password_entry.delete(0, tk.END)
            self.local_db_password_entry.insert(0, local_password)

        # Remote database
        self.remote_db_name_entry.delete(0, tk.END)
        self.remote_db_name_entry.insert(0, db_config.remote_db_name)

        self.remote_db_host_entry.delete(0, tk.END)
        self.remote_db_host_entry.insert(0, db_config.remote_db_host)

        self.remote_db_port_entry.delete(0, tk.END)
        self.remote_db_port_entry.insert(0, str(db_config.remote_db_port))

        self.remote_db_user_entry.delete(0, tk.END)
        self.remote_db_user_entry.insert(0, db_config.remote_db_user)

        # Load password from keyring
        remote_password = self.config_service.get_database_password(self.site.id, 'remote')
        if remote_password:
            self.remote_db_password_entry.delete(0, tk.END)
            self.remote_db_password_entry.insert(0, remote_password)

        # URLs
        self.local_url_entry.delete(0, tk.END)
        self.local_url_entry.insert(0, db_config.local_url)

        self.remote_url_entry.delete(0, tk.END)
        self.remote_url_entry.insert(0, db_config.remote_url)

        # Exclude tables
        self.exclude_tables_text.delete('1.0', tk.END)
        if db_config.exclude_tables:
            self.exclude_tables_text.insert('1.0', '\n'.join(db_config.exclude_tables))

        # Options
        self.backup_before_import_var.set(db_config.backup_before_import)
        self.require_confirmation_var.set(db_config.require_confirmation_on_push)

    def test_local_connection(self):
        """Test local database connection"""
        try:
            from ..services.database_service import DatabaseService

            # Create temporary database config
            db_config = self.get_database_config()
            if not db_config:
                return

            # Create temporary site config
            temp_site = self.site
            temp_site.database_config = db_config

            db_service = DatabaseService(temp_site)

            # Test WP-CLI locally
            success, version = db_service.verify_wp_cli_local()

            if success:
                # Try to get table list
                success, tables = db_service.get_local_table_list()
                if success:
                    messagebox.showinfo("Success",
                                      f"Local database connection successful!\n\n"
                                      f"WP-CLI Version: {version}\n"
                                      f"Tables found: {len(tables)}")
                else:
                    messagebox.showwarning("Partial Success",
                                         f"WP-CLI found ({version}), but couldn't access database.\n\n"
                                         f"Please check database credentials.")
            else:
                messagebox.showerror("Error",
                                   f"WP-CLI not found locally.\n\n{version}\n\n"
                                   f"Please install WP-CLI: https://wp-cli.org/")

        except Exception as e:
            messagebox.showerror("Error", f"Test failed: {str(e)}")

    def test_remote_connection(self):
        """Test remote database connection"""
        try:
            from ..services.ssh_service import SSHService
            from ..services.database_service import DatabaseService

            # Create temporary database config
            db_config = self.get_database_config()
            if not db_config:
                return

            # Get SSH password
            ssh_password = self.config_service.get_password(self.site.id)
            if not ssh_password:
                messagebox.showerror("Error", "SSH password not found. Please configure the site first.")
                return

            # Create SSH service
            ssh_service = SSHService(self.site.remote_host, self.site.remote_port,
                                    self.site.remote_username, ssh_password)

            # Create temporary site config
            temp_site = self.site
            temp_site.database_config = db_config

            db_service = DatabaseService(temp_site, ssh_service)

            # Connect and test
            ssh_service.connect()

            # Test WP-CLI remotely
            success, version = db_service.verify_wp_cli_remote()

            if success:
                # Try to get table list
                success, tables = db_service.get_remote_table_list()
                if success:
                    messagebox.showinfo("Success",
                                      f"Remote database connection successful!\n\n"
                                      f"WP-CLI Version: {version}\n"
                                      f"Tables found: {len(tables)}")
                else:
                    messagebox.showwarning("Partial Success",
                                         f"WP-CLI found ({version}), but couldn't access database.\n\n"
                                         f"Please check database credentials.")
            else:
                messagebox.showerror("Error",
                                   f"WP-CLI not found on remote server.\n\n{version}\n\n"
                                   f"Please contact your hosting provider.")

            ssh_service.disconnect()

        except Exception as e:
            messagebox.showerror("Error", f"Test failed: {str(e)}")

    def get_database_config(self):
        """Get database configuration from form"""
        try:
            # Get exclude tables
            exclude_text = self.exclude_tables_text.get('1.0', tk.END).strip()
            exclude_tables = [t.strip() for t in exclude_text.split('\n') if t.strip()]

            db_config = DatabaseConfig(
                local_db_name=self.local_db_name_entry.get(),
                local_db_host=self.local_db_host_entry.get(),
                local_db_port=int(self.local_db_port_entry.get()),
                local_db_user=self.local_db_user_entry.get(),
                remote_db_name=self.remote_db_name_entry.get(),
                remote_db_host=self.remote_db_host_entry.get(),
                remote_db_port=int(self.remote_db_port_entry.get()),
                remote_db_user=self.remote_db_user_entry.get(),
                local_url=self.local_url_entry.get(),
                remote_url=self.remote_url_entry.get(),
                exclude_tables=exclude_tables,
                backup_before_import=self.backup_before_import_var.get(),
                require_confirmation_on_push=self.require_confirmation_var.get()
            )

            return db_config

        except ValueError as e:
            messagebox.showerror("Validation Error", f"Invalid port number: {e}")
            return None

    def save(self):
        """Save database configuration"""
        # Validate required fields
        if not self.local_db_name_entry.get():
            messagebox.showerror("Validation Error", "Local database name is required")
            self.local_db_name_entry.focus()
            return

        if not self.remote_db_name_entry.get():
            messagebox.showerror("Validation Error", "Remote database name is required")
            self.remote_db_name_entry.focus()
            return

        # Get database config
        db_config = self.get_database_config()
        if not db_config:
            return

        # Update site configuration
        self.site.database_config = db_config

        # Save passwords to keyring
        local_password = self.local_db_password_entry.get()
        if local_password:
            self.config_service.set_database_password(self.site.id, 'local', local_password)

        remote_password = self.remote_db_password_entry.get()
        if remote_password:
            self.config_service.set_database_password(self.site.id, 'remote', remote_password)

        # Update site in config
        self.config_service.update_site(self.site)

        self.result = True
        self.dialog.destroy()

    def auto_detect_local_database(self):
        """Auto-detect local database configuration from wp-config.php"""
        try:
            import os
            from ..utils.wp_config_parser import WPConfigParser

            # Build path to wp-config.php
            wp_config_path = os.path.join(self.site.local_path, 'wp-config.php')

            if not os.path.exists(wp_config_path):
                messagebox.showerror("Not Found",
                                   f"wp-config.php not found at:\n{wp_config_path}\n\n"
                                   f"Please check your local path in site configuration.")
                return

            # Parse wp-config.php
            config = WPConfigParser.parse_file(wp_config_path)

            # Populate form fields
            if config['db_name']:
                self.local_db_name_entry.delete(0, tk.END)
                self.local_db_name_entry.insert(0, config['db_name'])

            if config['db_user']:
                self.local_db_user_entry.delete(0, tk.END)
                self.local_db_user_entry.insert(0, config['db_user'])

            if config['db_password']:
                self.local_db_password_entry.delete(0, tk.END)
                self.local_db_password_entry.insert(0, config['db_password'])

            if config['db_host']:
                # Parse host and port if host contains port (e.g., "localhost:3307")
                if ':' in config['db_host']:
                    host, port = config['db_host'].split(':', 1)
                    self.local_db_host_entry.delete(0, tk.END)
                    self.local_db_host_entry.insert(0, host)
                    self.local_db_port_entry.delete(0, tk.END)
                    self.local_db_port_entry.insert(0, port)
                else:
                    self.local_db_host_entry.delete(0, tk.END)
                    self.local_db_host_entry.insert(0, config['db_host'])

            # Try to get site URL using WP-CLI
            site_url = config.get('site_url') or config.get('home_url')
            if not site_url:
                site_url = WPConfigParser.get_site_url_from_wpcli(self.site.local_path)

            if site_url:
                self.local_url_entry.delete(0, tk.END)
                self.local_url_entry.insert(0, site_url)

            messagebox.showinfo("Success",
                              f"Local database configuration detected!\n\n"
                              f"Database: {config['db_name']}\n"
                              f"User: {config['db_user']}\n"
                              f"Host: {config['db_host']}\n"
                              f"URL: {site_url or 'Not detected'}")

        except Exception as e:
            messagebox.showerror("Error", f"Auto-detection failed:\n\n{str(e)}")

    def auto_detect_remote_database(self):
        """Auto-detect remote database configuration from wp-config.php"""
        try:
            from ..services.ssh_service import SSHService
            from ..utils.wp_config_parser import WPConfigParser

            # Get SSH password
            ssh_password = self.config_service.get_password(self.site.id)
            if not ssh_password:
                messagebox.showerror("Error",
                                   "SSH password not found.\n\n"
                                   "Please configure the site first with SSH credentials.")
                return

            # Create SSH service
            ssh_service = SSHService(self.site.remote_host, self.site.remote_port,
                                    self.site.remote_username, ssh_password)

            # Connect
            ssh_service.connect()

            # Read wp-config.php from remote
            import shlex
            wp_config_path = f"{self.site.remote_path}/wp-config.php"
            command = f"cat {shlex.quote(wp_config_path)}"

            success, stdout, stderr = ssh_service.execute_command(command)

            if not success:
                ssh_service.disconnect()
                messagebox.showerror("Error",
                                   f"Could not read wp-config.php from remote server:\n\n{stderr}\n\n"
                                   f"Path: {wp_config_path}")
                return

            # Parse wp-config.php content
            config = WPConfigParser.parse_remote_file(stdout)

            # Populate form fields
            if config['db_name']:
                self.remote_db_name_entry.delete(0, tk.END)
                self.remote_db_name_entry.insert(0, config['db_name'])

            if config['db_user']:
                self.remote_db_user_entry.delete(0, tk.END)
                self.remote_db_user_entry.insert(0, config['db_user'])

            if config['db_password']:
                self.remote_db_password_entry.delete(0, tk.END)
                self.remote_db_password_entry.insert(0, config['db_password'])

            if config['db_host']:
                # Parse host and port if host contains port (e.g., "localhost:3307")
                if ':' in config['db_host']:
                    host, port = config['db_host'].split(':', 1)
                    self.remote_db_host_entry.delete(0, tk.END)
                    self.remote_db_host_entry.insert(0, host)
                    self.remote_db_port_entry.delete(0, tk.END)
                    self.remote_db_port_entry.insert(0, port)
                else:
                    self.remote_db_host_entry.delete(0, tk.END)
                    self.remote_db_host_entry.insert(0, config['db_host'])

            # Try to get site URL using WP-CLI
            site_url = config.get('site_url') or config.get('home_url')
            if not site_url:
                site_url = WPConfigParser.get_site_url_from_wpcli(
                    self.site.remote_path,
                    remote=True,
                    ssh_command_executor=ssh_service.execute_command
                )

            if site_url:
                self.remote_url_entry.delete(0, tk.END)
                self.remote_url_entry.insert(0, site_url)

            ssh_service.disconnect()

            messagebox.showinfo("Success",
                              f"Remote database configuration detected!\n\n"
                              f"Database: {config['db_name']}\n"
                              f"User: {config['db_user']}\n"
                              f"Host: {config['db_host']}\n"
                              f"URL: {site_url or 'Not detected'}")

        except Exception as e:
            messagebox.showerror("Error", f"Auto-detection failed:\n\n{str(e)}")

    def cancel(self):
        """Cancel and close dialog"""
        self.result = False
        self.dialog.destroy()

    def show(self):
        """Show dialog and wait for result"""
        self.dialog.wait_window()
        return self.result

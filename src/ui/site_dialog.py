"""
Site configuration dialog with tabbed interface
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import uuid
import os
import shlex
from ..models.site_config import SiteConfig
from ..models.database_config import DatabaseConfig


class SiteDialog:
    """Dialog for adding/editing site configuration"""

    def __init__(self, parent, config_service, site=None):
        self.config_service = config_service
        self.site = site
        self.result = None

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Add Site" if site is None else "Edit Site")
        self.dialog.geometry("950x750")

        self.create_widgets()

        if site:
            self.load_site_data()

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
        self.name_entry.focus_set()

        # Bind Escape key to cancel
        self.dialog.bind('<Escape>', lambda e: self.cancel())

    def create_widgets(self):
        """Create dialog widgets with tabbed interface"""
        # Main frame
        main_frame = ttk.Frame(self.dialog, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Create main notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=5)

        # Tab 1: Site Configuration
        self.site_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.site_frame, text="Site")
        self.create_site_tab()

        # Tab 2: Database Configuration
        self.db_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.db_frame, text="Database")
        self.create_database_tab()

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)

        self.save_button = ttk.Button(button_frame, text="💾 Save Site", command=self.save,
                                      style="Accent.TButton")
        self.save_button.pack(side=tk.LEFT, padx=5, ipady=10, ipadx=20)

        self.cancel_button = ttk.Button(button_frame, text="✖ Cancel", command=self.cancel)
        self.cancel_button.pack(side=tk.LEFT, padx=5, ipady=10, ipadx=20)

    def create_site_tab(self):
        """Create Site tab with sub-tabs for Basic Info, SSH/SFTP, and Advanced"""
        # Create notebook for site sub-tabs
        self.site_notebook = ttk.Notebook(self.site_frame)
        self.site_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Sub-tab 1: Basic Information
        basic_tab = ttk.Frame(self.site_notebook)
        self.site_notebook.add(basic_tab, text="Basic Info")
        self.create_basic_info_tab(basic_tab)

        # Sub-tab 2: SSH/SFTP
        ssh_tab = ttk.Frame(self.site_notebook)
        self.site_notebook.add(ssh_tab, text="SSH / SFTP")
        self.create_ssh_tab(ssh_tab)

        # Sub-tab 3: Advanced Options
        advanced_tab = ttk.Frame(self.site_notebook)
        self.site_notebook.add(advanced_tab, text="Advanced")
        self.create_advanced_tab(advanced_tab)

    def create_basic_info_tab(self, parent):
        """Create Basic Information fields"""
        # Create scrollable frame
        canvas = tk.Canvas(parent)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Basic info fields
        basic_frame = ttk.LabelFrame(scrollable_frame, text="Site Information", padding=10)
        basic_frame.pack(fill=tk.X, pady=5, padx=10)

        row = 0
        ttk.Label(basic_frame, text="Site Name:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.name_entry = ttk.Entry(basic_frame, width=50)
        self.name_entry.grid(row=row, column=1, sticky=tk.W, pady=5, padx=5)

        row += 1
        ttk.Label(basic_frame, text="Local Path:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.local_path_entry = ttk.Entry(basic_frame, width=50)
        self.local_path_entry.grid(row=row, column=1, sticky=tk.W, pady=5, padx=5)
        self.browse_local_btn = ttk.Button(basic_frame, text="📁 Browse", command=self.browse_local)
        self.browse_local_btn.grid(row=row, column=2, padx=5, ipady=5, ipadx=8)

        row += 1
        ttk.Label(basic_frame, text="Git Repo Path:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.git_path_entry = ttk.Entry(basic_frame, width=50)
        self.git_path_entry.grid(row=row, column=1, sticky=tk.W, pady=5, padx=5)
        self.browse_git_btn = ttk.Button(basic_frame, text="📁 Browse", command=self.browse_git)
        self.browse_git_btn.grid(row=row, column=2, padx=5, ipady=5, ipadx=8)
        same_btn = ttk.Button(basic_frame, text="Same as Local", command=self.same_as_local)
        same_btn.grid(row=row, column=3, padx=5, ipady=5, ipadx=8)

        row += 1
        self.git_status_label = ttk.Label(basic_frame, text="", foreground="gray")
        self.git_status_label.grid(row=row, column=1, sticky=tk.W, pady=2, padx=5)

        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def create_ssh_tab(self, parent):
        """Create SSH/SFTP configuration fields"""
        # Create scrollable frame
        canvas = tk.Canvas(parent)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Remote Server
        remote_frame = ttk.LabelFrame(scrollable_frame, text="Remote Server (SSH/SFTP)", padding=10)
        remote_frame.pack(fill=tk.X, padx=10, pady=10)

        row = 0
        ttk.Label(remote_frame, text="Host:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.host_entry = ttk.Entry(remote_frame, width=50)
        self.host_entry.grid(row=row, column=1, sticky=tk.W, pady=5, padx=5)

        row += 1
        ttk.Label(remote_frame, text="Port:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.port_entry = ttk.Entry(remote_frame, width=10)
        self.port_entry.grid(row=row, column=1, sticky=tk.W, pady=5, padx=5)
        self.port_entry.insert(0, "22")

        row += 1
        ttk.Label(remote_frame, text="Username:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.username_entry = ttk.Entry(remote_frame, width=50)
        self.username_entry.grid(row=row, column=1, sticky=tk.W, pady=5, padx=5)

        row += 1
        ttk.Label(remote_frame, text="Password:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.password_entry = ttk.Entry(remote_frame, width=50, show="*")
        self.password_entry.grid(row=row, column=1, sticky=tk.W, pady=5, padx=5)

        row += 1
        ttk.Label(remote_frame, text="Remote Path:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.remote_path_entry = ttk.Entry(remote_frame, width=50)
        self.remote_path_entry.grid(row=row, column=1, sticky=tk.W, pady=5, padx=5)

        row += 1
        ttk.Label(remote_frame, text="Site URL:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.site_url_entry = ttk.Entry(remote_frame, width=50)
        self.site_url_entry.grid(row=row, column=1, sticky=tk.W, pady=5, padx=5)
        ttk.Label(remote_frame, text="(e.g., https://yoursite.com)", foreground="gray").grid(row=row, column=2, sticky=tk.W, pady=5)

        # Test connection button
        test_button_frame = ttk.LabelFrame(scrollable_frame, text="Connection Test", padding=10)
        test_button_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Button(test_button_frame, text="🔌 Test SSH Connection",
                  command=self.test_ssh_connection).pack(pady=5, ipady=5, ipadx=10)

        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def create_advanced_tab(self, parent):
        """Create Advanced options fields"""
        # Create scrollable frame
        canvas = tk.Canvas(parent)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Transfer options
        options_frame = ttk.LabelFrame(scrollable_frame, text="Transfer Options", padding=10)
        options_frame.pack(fill=tk.X, padx=10, pady=10)

        self.push_newer_only_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Push/Pull Newer Files Only (skip files that haven't changed)",
                       variable=self.push_newer_only_var).pack(anchor=tk.W, pady=5)
        ttk.Label(options_frame, text="When enabled, only transfers files if they are newer than the destination version.",
                 foreground="gray", wraplength=600).pack(anchor=tk.W, padx=20, pady=2)

        self.use_compression_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Use compression for folders (faster transfer of plugins/themes)",
                       variable=self.use_compression_var).pack(anchor=tk.W, pady=5)
        ttk.Label(options_frame, text="When enabled, compresses folders before transfer, then extracts on destination. Much faster for many small files.",
                 foreground="gray", wraplength=600).pack(anchor=tk.W, padx=20, pady=2)

        # Compress folders
        compress_frame = ttk.LabelFrame(scrollable_frame, text="Default Folders for 'Push Folder(s)' (one per line)", padding=10)
        compress_frame.pack(fill=tk.X, padx=10, pady=10)

        self.compress_folders_text = scrolledtext.ScrolledText(compress_frame, height=4)
        self.compress_folders_text.pack(fill=tk.BOTH, expand=True)
        self.compress_folders_text.insert(1.0, "wp-content/plugins/\nwp-content/themes/")

        # Pull include paths
        paths_frame = ttk.LabelFrame(scrollable_frame, text="Pull Include Paths (one per line)", padding=10)
        paths_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.include_paths_text = scrolledtext.ScrolledText(paths_frame, height=8)
        self.include_paths_text.pack(fill=tk.BOTH, expand=True)
        self.include_paths_text.insert(1.0, "wp-content/uploads/\nwp-content/themes/\nwp-content/plugins/")

        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def create_database_tab(self):
        """Create database configuration tab with sub-tabs"""
        # Create notebook for database sub-tabs
        self.db_notebook = ttk.Notebook(self.db_frame)
        self.db_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Local Database Tab
        local_tab = ttk.Frame(self.db_notebook)
        self.db_notebook.add(local_tab, text="Local Database")
        self.create_local_database_tab(local_tab)

        # Remote Database Tab
        remote_tab = ttk.Frame(self.db_notebook)
        self.db_notebook.add(remote_tab, text="Remote Database")
        self.create_remote_database_tab(remote_tab)

        # Advanced Options Tab
        advanced_tab = ttk.Frame(self.db_notebook)
        self.db_notebook.add(advanced_tab, text="Advanced Options")
        self.create_advanced_options_tab(advanced_tab)

    def create_local_database_tab(self, parent):
        """Create local database configuration fields"""
        # Create scrollable frame
        canvas = tk.Canvas(parent)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Local Database Fields
        local_db_frame = ttk.LabelFrame(scrollable_frame, text="Connection", padding=10)
        local_db_frame.pack(fill=tk.X, pady=5, padx=10)

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
        ttk.Label(local_db_frame, text="Table Prefix:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.local_table_prefix_entry = ttk.Entry(local_db_frame, width=40)
        self.local_table_prefix_entry.grid(row=row, column=1, sticky=tk.W, pady=5, padx=5)
        self.local_table_prefix_entry.insert(0, "wp_")

        row += 1
        auto_detect_local_btn = ttk.Button(local_db_frame, text="🔍 Auto-detect from wp-config.php",
                                          command=self.auto_detect_local_database)
        auto_detect_local_btn.grid(row=row, column=0, columnspan=2, pady=10, ipady=5, ipadx=10)

        # URL Section
        url_frame = ttk.LabelFrame(scrollable_frame, text="Site URL", padding=10)
        url_frame.pack(fill=tk.X, pady=5, padx=10)

        ttk.Label(url_frame, text="Local URL:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.local_url_entry = ttk.Entry(url_frame, width=40)
        self.local_url_entry.grid(row=0, column=1, sticky=tk.W, pady=5, padx=5)
        ttk.Label(url_frame, text="e.g., http://mysite.local", foreground="gray").grid(row=0, column=2, sticky=tk.W, padx=5)

        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def create_remote_database_tab(self, parent):
        """Create remote database configuration fields"""
        # Create scrollable frame
        canvas = tk.Canvas(parent)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Remote Database Fields
        remote_db_frame = ttk.LabelFrame(scrollable_frame, text="Connection (via SSH)", padding=10)
        remote_db_frame.pack(fill=tk.X, pady=5, padx=10)

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
        ttk.Label(remote_db_frame, text="Table Prefix:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.remote_table_prefix_entry = ttk.Entry(remote_db_frame, width=40)
        self.remote_table_prefix_entry.grid(row=row, column=1, sticky=tk.W, pady=5, padx=5)
        self.remote_table_prefix_entry.insert(0, "wp_")

        row += 1
        auto_detect_remote_btn = ttk.Button(remote_db_frame, text="🔍 Auto-detect from wp-config.php",
                                           command=self.auto_detect_remote_database)
        auto_detect_remote_btn.grid(row=row, column=0, columnspan=2, pady=10, ipady=5, ipadx=10)

        # URL Section
        url_frame = ttk.LabelFrame(scrollable_frame, text="Site URL", padding=10)
        url_frame.pack(fill=tk.X, pady=5, padx=10)

        ttk.Label(url_frame, text="Remote URL:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.remote_url_entry = ttk.Entry(url_frame, width=40)
        self.remote_url_entry.grid(row=0, column=1, sticky=tk.W, pady=5, padx=5)
        ttk.Label(url_frame, text="e.g., https://mysite.com", foreground="gray").grid(row=0, column=2, sticky=tk.W, padx=5)

        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def create_advanced_options_tab(self, parent):
        """Create advanced options fields"""
        # Create scrollable frame
        canvas = tk.Canvas(parent)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Exclude Tables Section
        exclude_frame = ttk.LabelFrame(scrollable_frame, text="Exclude Tables", padding=10)
        exclude_frame.pack(fill=tk.X, pady=5, padx=10)

        ttk.Label(exclude_frame, text="Exclude these tables during sync (one per line):", foreground="gray").pack(anchor=tk.W, pady=5)
        self.exclude_tables_text = scrolledtext.ScrolledText(exclude_frame, width=50, height=6)
        self.exclude_tables_text.pack(fill=tk.BOTH, expand=True, pady=5)
        default_excludes = "wp_users\nwp_usermeta"
        self.exclude_tables_text.insert('1.0', default_excludes)

        # Safety Options Section
        safety_frame = ttk.LabelFrame(scrollable_frame, text="Safety Options", padding=10)
        safety_frame.pack(fill=tk.X, pady=5, padx=10)

        self.backup_before_import_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(safety_frame, text="Create backup before import",
                       variable=self.backup_before_import_var).pack(anchor=tk.W, pady=5)

        self.require_confirmation_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(safety_frame, text="Require confirmation when pushing to production",
                       variable=self.require_confirmation_var).pack(anchor=tk.W, pady=5)

        self.save_database_backups_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(safety_frame, text="Save database backups to /db folder",
                       variable=self.save_database_backups_var).pack(anchor=tk.W, pady=5)

        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def auto_detect_local_database(self):
        """Auto-detect local database configuration from wp-config.php"""
        try:
            from ..utils.wp_config_parser import WPConfigParser

            local_path = self.local_path_entry.get()
            if not local_path:
                messagebox.showerror("Error", "Please enter Local Path first")
                self.notebook.select(0)  # Switch to Site tab
                self.site_notebook.select(0)  # Switch to Basic Info sub-tab
                self.local_path_entry.focus()
                return

            wp_config_path = os.path.join(local_path, 'wp-config.php')

            if not os.path.exists(wp_config_path):
                messagebox.showerror("Not Found",
                                   f"wp-config.php not found at:\n{wp_config_path}\n\n"
                                   f"Please check your local path.")
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
                if ':' in config['db_host']:
                    host, port = config['db_host'].split(':', 1)
                    self.local_db_host_entry.delete(0, tk.END)
                    self.local_db_host_entry.insert(0, host)
                    self.local_db_port_entry.delete(0, tk.END)
                    self.local_db_port_entry.insert(0, port)
                else:
                    self.local_db_host_entry.delete(0, tk.END)
                    self.local_db_host_entry.insert(0, config['db_host'])

            # Table prefix
            if config.get('table_prefix'):
                self.local_table_prefix_entry.delete(0, tk.END)
                self.local_table_prefix_entry.insert(0, config['table_prefix'])

            # Try to get site URL
            site_url = config.get('site_url') or config.get('home_url')
            if not site_url:
                site_url = WPConfigParser.get_site_url_from_wpcli(local_path)

            if site_url:
                self.local_url_entry.delete(0, tk.END)
                self.local_url_entry.insert(0, site_url)

            messagebox.showinfo("Success",
                              f"Local database configuration detected!\n\n"
                              f"Database: {config['db_name']}\n"
                              f"User: {config['db_user']}\n"
                              f"Host: {config['db_host']}\n"
                              f"Table Prefix: {config.get('table_prefix', 'wp_')}\n"
                              f"URL: {site_url or 'Not detected'}")

        except Exception as e:
            messagebox.showerror("Error", f"Auto-detection failed:\n\n{str(e)}")

    def auto_detect_remote_database(self):
        """Auto-detect remote database configuration from wp-config.php using SSH"""
        try:
            from ..services.ssh_service import SSHService
            from ..utils.wp_config_parser import WPConfigParser

            # Validate SSH credentials from the form
            host = self.host_entry.get()
            port = self.port_entry.get()
            username = self.username_entry.get()
            password = self.password_entry.get()
            remote_path = self.remote_path_entry.get()

            if not all([host, port, username, password, remote_path]):
                messagebox.showerror("Missing Information",
                                   "Please fill in all SSH/SFTP fields first:\n\n"
                                   "- Host\n- Port\n- Username\n- Password\n- Remote Path")
                self.notebook.select(0)  # Switch to Site tab
                self.site_notebook.select(1)  # Switch to SSH/SFTP sub-tab
                return

            try:
                port_num = int(port)
            except ValueError:
                messagebox.showerror("Invalid Port", "Port must be a number")
                self.notebook.select(0)  # Switch to Site tab
                self.site_notebook.select(1)  # Switch to SSH/SFTP sub-tab
                self.port_entry.focus()
                return

            # Create SSH service with credentials from form
            ssh_service = SSHService(host, port_num, username, password)

            # Connect
            messagebox.showinfo("Connecting", "Connecting to remote server...")
            ssh_service.connect()

            # Read wp-config.php from remote
            wp_config_path = f"{remote_path}/wp-config.php"
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
                if ':' in config['db_host']:
                    host_part, port_part = config['db_host'].split(':', 1)
                    self.remote_db_host_entry.delete(0, tk.END)
                    self.remote_db_host_entry.insert(0, host_part)
                    self.remote_db_port_entry.delete(0, tk.END)
                    self.remote_db_port_entry.insert(0, port_part)
                else:
                    self.remote_db_host_entry.delete(0, tk.END)
                    self.remote_db_host_entry.insert(0, config['db_host'])

            # Table prefix
            if config.get('table_prefix'):
                self.remote_table_prefix_entry.delete(0, tk.END)
                self.remote_table_prefix_entry.insert(0, config['table_prefix'])

            # NOTE: We intentionally do NOT auto-update the Remote URL field here
            # because the remote database might contain the wrong URL (e.g., local URL)
            # if the local database was previously pushed to production.
            # Users should manually set the Remote URL once and it will be preserved.

            # Try to get site URL for informational purposes only
            site_url = config.get('site_url') or config.get('home_url')
            if not site_url:
                site_url = WPConfigParser.get_site_url_from_wpcli(
                    remote_path,
                    remote=True,
                    ssh_command_executor=ssh_service.execute_command
                )

            # Do NOT update remote_url_entry - leave it as the user set it

            ssh_service.disconnect()

            messagebox.showinfo("Success",
                              f"Remote database configuration detected!\n\n"
                              f"Database: {config['db_name']}\n"
                              f"User: {config['db_user']}\n"
                              f"Host: {config['db_host']}\n"
                              f"Table Prefix: {config.get('table_prefix', 'wp_')}\n"
                              f"URL in database: {site_url or 'Not detected'}\n\n"
                              f"Note: Remote URL field was NOT updated.\n"
                              f"Please set it manually if needed.")

        except Exception as e:
            messagebox.showerror("Error", f"Auto-detection failed:\n\n{str(e)}")

    def test_ssh_connection(self):
        """Test SSH connection to remote server"""
        try:
            from ..services.ssh_service import SSHService

            # Validate SSH credentials
            host = self.host_entry.get()
            port = self.port_entry.get()
            username = self.username_entry.get()
            password = self.password_entry.get()

            if not all([host, port, username, password]):
                messagebox.showerror("Missing Information",
                                   "Please fill in all SSH fields:\n\n"
                                   "- Host\n- Port\n- Username\n- Password")
                return

            try:
                port_num = int(port)
            except ValueError:
                messagebox.showerror("Invalid Port", "Port must be a number")
                self.port_entry.focus()
                return

            # Test SSH connection
            ssh_service = SSHService(host, port_num, username, password)

            try:
                ssh_service.connect()

                # Test basic command
                success, output, error = ssh_service.execute_command("pwd")

                ssh_service.disconnect()

                if success:
                    messagebox.showinfo("Success",
                                      f"✓ SSH Connection Successful!\n\n"
                                      f"Server: {host}:{port}\n"
                                      f"User: {username}\n"
                                      f"Working directory: {output.strip()}")
                else:
                    messagebox.showerror("Connection Error",
                                       f"SSH connected but command failed:\n\n{error}")

            except Exception as e:
                messagebox.showerror("Connection Failed",
                                   f"Failed to connect via SSH:\n\n{str(e)}\n\n"
                                   f"Please verify:\n"
                                   f"- Host and port are correct\n"
                                   f"- Username and password are correct\n"
                                   f"- Server is accessible from this machine")

        except Exception as e:
            messagebox.showerror("Error", f"Test failed: {str(e)}")

    def test_local_connection(self):
        """Test local database connection using WP-CLI"""
        try:
            from ..services.database_service import DatabaseService
            from ..models.site_config import SiteConfig

            # Validate required fields
            local_path = self.local_path_entry.get()
            if not local_path:
                messagebox.showerror("Error", "Please enter Local Path first")
                return

            if not self.local_db_name_entry.get():
                messagebox.showerror("Error", "Please enter Local Database Name first")
                self.local_db_name_entry.focus()
                return

            # Create temporary database config
            try:
                exclude_text = self.exclude_tables_text.get('1.0', tk.END).strip()
                exclude_tables = [t.strip() for t in exclude_text.split('\n') if t.strip()]

                database_config = DatabaseConfig(
                    local_db_name=self.local_db_name_entry.get(),
                    local_db_host=self.local_db_host_entry.get(),
                    local_db_port=int(self.local_db_port_entry.get()) if self.local_db_port_entry.get() else 3306,
                    local_db_user=self.local_db_user_entry.get(),
                    remote_db_name=self.remote_db_name_entry.get() or "dummy",
                    remote_db_host=self.remote_db_host_entry.get(),
                    remote_db_port=int(self.remote_db_port_entry.get()) if self.remote_db_port_entry.get() else 3306,
                    remote_db_user=self.remote_db_user_entry.get(),
                    local_url=self.local_url_entry.get(),
                    remote_url=self.remote_url_entry.get(),
                    exclude_tables=exclude_tables,
                    backup_before_import=self.backup_before_import_var.get(),
                    require_confirmation_on_push=self.require_confirmation_var.get(),
                    save_database_backups=self.save_database_backups_var.get()
                )
            except ValueError as e:
                messagebox.showerror("Validation Error", f"Invalid port number: {e}")
                return

            # Create temporary site config
            site_id = self.site.id if self.site else str(uuid.uuid4())[:8]
            temp_site = SiteConfig(
                id=site_id,
                name=self.name_entry.get() or "Test Site",
                local_path=local_path,
                git_repo_path=self.git_path_entry.get() or local_path,
                remote_host=self.host_entry.get() or "dummy",
                remote_port=int(self.port_entry.get()) if self.port_entry.get() else 22,
                remote_path=self.remote_path_entry.get() or "/",
                remote_username=self.username_entry.get() or "dummy",
                site_url=self.site_url_entry.get(),
                pull_include_paths=[],
                database_config=database_config
            )

            # Temporarily save password to keyring if needed
            local_password = self.local_db_password_entry.get()
            if local_password:
                self.config_service.set_database_password(site_id, 'local', local_password)

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
        """Test remote database connection using WP-CLI via SSH"""
        try:
            from ..services.ssh_service import SSHService
            from ..services.database_service import DatabaseService
            from ..models.site_config import SiteConfig

            # Validate SSH credentials
            host = self.host_entry.get()
            port = self.port_entry.get()
            username = self.username_entry.get()
            password = self.password_entry.get()
            remote_path = self.remote_path_entry.get()

            if not all([host, port, username, password, remote_path]):
                messagebox.showerror("Missing Information",
                                   "Please fill in all SSH/SFTP fields first:\n\n"
                                   "- Host\n- Port\n- Username\n- Password\n- Remote Path")
                self.notebook.select(0)  # Switch to Site tab
                self.site_notebook.select(1)  # Switch to SSH/SFTP sub-tab
                return

            if not self.remote_db_name_entry.get():
                messagebox.showerror("Error", "Please enter Remote Database Name first")
                self.remote_db_name_entry.focus()
                return

            try:
                port_num = int(port)
            except ValueError:
                messagebox.showerror("Invalid Port", "Port must be a number")
                self.notebook.select(0)  # Switch to Site tab
                self.site_notebook.select(1)  # Switch to SSH/SFTP sub-tab
                self.port_entry.focus()
                return

            # Create temporary database config
            try:
                exclude_text = self.exclude_tables_text.get('1.0', tk.END).strip()
                exclude_tables = [t.strip() for t in exclude_text.split('\n') if t.strip()]

                database_config = DatabaseConfig(
                    local_db_name=self.local_db_name_entry.get() or "dummy",
                    local_db_host=self.local_db_host_entry.get(),
                    local_db_port=int(self.local_db_port_entry.get()) if self.local_db_port_entry.get() else 3306,
                    local_db_user=self.local_db_user_entry.get(),
                    remote_db_name=self.remote_db_name_entry.get(),
                    remote_db_host=self.remote_db_host_entry.get(),
                    remote_db_port=int(self.remote_db_port_entry.get()) if self.remote_db_port_entry.get() else 3306,
                    remote_db_user=self.remote_db_user_entry.get(),
                    local_url=self.local_url_entry.get(),
                    remote_url=self.remote_url_entry.get(),
                    exclude_tables=exclude_tables,
                    backup_before_import=self.backup_before_import_var.get(),
                    require_confirmation_on_push=self.require_confirmation_var.get()
                )
            except ValueError as e:
                messagebox.showerror("Validation Error", f"Invalid port number: {e}")
                return

            # Create temporary site config
            site_id = self.site.id if self.site else str(uuid.uuid4())[:8]
            temp_site = SiteConfig(
                id=site_id,
                name=self.name_entry.get() or "Test Site",
                local_path=self.local_path_entry.get() or "/tmp",
                git_repo_path=self.git_path_entry.get() or "/tmp",
                remote_host=host,
                remote_port=port_num,
                remote_path=remote_path,
                remote_username=username,
                site_url=self.site_url_entry.get(),
                pull_include_paths=[],
                database_config=database_config
            )

            # Temporarily save password to keyring if needed
            remote_db_password = self.remote_db_password_entry.get()
            if remote_db_password:
                self.config_service.set_database_password(site_id, 'remote', remote_db_password)

            # Create SSH service
            ssh_service = SSHService(host, port_num, username, password)

            db_service = DatabaseService(temp_site, ssh_service)

            # Connect
            messagebox.showinfo("Connecting", "Connecting to remote server...")
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

    def browse_local(self):
        """Browse for local directory"""
        self.browse_local_btn.config(state=tk.DISABLED, text="Browsing...")
        initial_dir = self.local_path_entry.get().strip() or None

        directory = filedialog.askdirectory(
            parent=self.dialog,
            title="Select Local WordPress Directory",
            initialdir=initial_dir,
            mustexist=True
        )

        self.browse_local_btn.config(state=tk.NORMAL, text="📁 Browse")

        if directory:
            self.local_path_entry.delete(0, tk.END)
            self.local_path_entry.insert(0, directory)
            self.check_and_set_git_repo(directory)

        self.dialog.lift()
        self.dialog.focus_force()

    def browse_git(self):
        """Browse for Git repository directory"""
        self.browse_git_btn.config(state=tk.DISABLED, text="Browsing...")
        initial_dir = self.git_path_entry.get().strip() or None

        directory = filedialog.askdirectory(
            parent=self.dialog,
            title="Select Git Repository Directory",
            initialdir=initial_dir,
            mustexist=True
        )

        self.browse_git_btn.config(state=tk.NORMAL, text="📁 Browse")

        if directory:
            self.git_path_entry.delete(0, tk.END)
            self.git_path_entry.insert(0, directory)

        self.dialog.lift()
        self.dialog.focus_force()

    def same_as_local(self):
        """Copy local path to git path"""
        local_path = self.local_path_entry.get()
        if local_path:
            self.git_path_entry.delete(0, tk.END)
            self.git_path_entry.insert(0, local_path)
            self.check_and_set_git_repo(local_path)

    def check_and_set_git_repo(self, path):
        """Check if path is a Git repository"""
        from ..services.git_service import GitService
        try:
            git_service = GitService(path)
            current_commit = git_service.get_current_commit()
            if current_commit:
                self.git_status_label.config(text=f"✓ Git repository (commit: {current_commit[:7]})",
                                            foreground="green")
                if not self.git_path_entry.get():
                    self.git_path_entry.delete(0, tk.END)
                    self.git_path_entry.insert(0, path)
        except Exception as e:
            self.git_status_label.config(text=f"⚠ Not a Git repository", foreground="orange")

    def load_site_data(self):
        """Load existing site data into form"""
        # Basic info
        self.name_entry.insert(0, self.site.name)
        self.local_path_entry.insert(0, self.site.local_path)
        self.git_path_entry.insert(0, self.site.git_repo_path)

        # SSH/SFTP
        self.host_entry.insert(0, self.site.remote_host)
        self.port_entry.delete(0, tk.END)
        self.port_entry.insert(0, str(self.site.remote_port))
        self.username_entry.insert(0, self.site.remote_username)
        self.remote_path_entry.insert(0, self.site.remote_path)
        self.site_url_entry.insert(0, self.site.site_url if self.site.site_url else "")

        # Load password from keyring
        password = self.config_service.get_password(self.site.id)
        if password:
            self.password_entry.insert(0, password)

        # Pull paths
        if self.site.pull_include_paths:
            self.include_paths_text.delete(1.0, tk.END)
            self.include_paths_text.insert(1.0, '\n'.join(self.site.pull_include_paths))

        # Transfer options
        self.push_newer_only_var.set(self.site.push_newer_only)
        self.use_compression_var.set(self.site.use_compression)

        # Compress folders
        if self.site.compress_folders:
            self.compress_folders_text.delete(1.0, tk.END)
            self.compress_folders_text.insert(1.0, '\n'.join(self.site.compress_folders))

        # Database configuration (if exists)
        if self.site.database_config:
            db_config = self.site.database_config

            # Local database
            self.local_db_name_entry.insert(0, db_config.local_db_name)
            self.local_db_host_entry.delete(0, tk.END)
            self.local_db_host_entry.insert(0, db_config.local_db_host)
            self.local_db_port_entry.delete(0, tk.END)
            self.local_db_port_entry.insert(0, str(db_config.local_db_port))
            self.local_db_user_entry.delete(0, tk.END)
            self.local_db_user_entry.insert(0, db_config.local_db_user)
            self.local_table_prefix_entry.delete(0, tk.END)
            self.local_table_prefix_entry.insert(0, db_config.local_table_prefix)

            local_password = self.config_service.get_database_password(self.site.id, 'local')
            if local_password:
                self.local_db_password_entry.insert(0, local_password)

            # Remote database
            self.remote_db_name_entry.insert(0, db_config.remote_db_name)
            self.remote_db_host_entry.delete(0, tk.END)
            self.remote_db_host_entry.insert(0, db_config.remote_db_host)
            self.remote_db_port_entry.delete(0, tk.END)
            self.remote_db_port_entry.insert(0, str(db_config.remote_db_port))
            self.remote_db_user_entry.delete(0, tk.END)
            self.remote_db_user_entry.insert(0, db_config.remote_db_user)
            self.remote_table_prefix_entry.delete(0, tk.END)
            self.remote_table_prefix_entry.insert(0, db_config.remote_table_prefix)

            remote_password = self.config_service.get_database_password(self.site.id, 'remote')
            if remote_password:
                self.remote_db_password_entry.insert(0, remote_password)

            # URLs
            self.local_url_entry.insert(0, db_config.local_url)
            self.remote_url_entry.insert(0, db_config.remote_url)

            # Exclude tables
            if db_config.exclude_tables:
                self.exclude_tables_text.delete('1.0', tk.END)
                self.exclude_tables_text.insert('1.0', '\n'.join(db_config.exclude_tables))

            # Options
            self.backup_before_import_var.set(db_config.backup_before_import)
            self.require_confirmation_var.set(db_config.require_confirmation_on_push)
            self.save_database_backups_var.set(db_config.save_database_backups)

        # Check Git status
        self.check_and_set_git_repo(self.site.git_repo_path)

    def save(self):
        """Save site configuration"""
        # Validate required fields
        if not self.name_entry.get():
            messagebox.showerror("Validation Error", "Site name is required")
            self.name_entry.focus()
            return

        if not self.local_path_entry.get():
            messagebox.showerror("Validation Error", "Local path is required")
            self.local_path_entry.focus()
            return

        if not self.git_path_entry.get():
            messagebox.showerror("Validation Error", "Git repo path is required")
            self.git_path_entry.focus()
            return

        if not self.host_entry.get():
            messagebox.showerror("Validation Error", "Remote host is required")
            self.notebook.select(0)  # Switch to Site tab
            self.site_notebook.select(1)  # Switch to SSH/SFTP sub-tab
            self.host_entry.focus()
            return

        # Get or generate site ID
        site_id = self.site.id if self.site else str(uuid.uuid4())[:8]

        # Get pull include paths
        paths_text = self.include_paths_text.get(1.0, tk.END).strip()
        pull_include_paths = [p.strip() for p in paths_text.split('\n') if p.strip()]

        # Get compress folders
        compress_text = self.compress_folders_text.get(1.0, tk.END).strip()
        compress_folders = [p.strip() for p in compress_text.split('\n') if p.strip()]

        # Create database config if any database fields are filled
        database_config = None
        if self.local_db_name_entry.get() or self.remote_db_name_entry.get():
            try:
                exclude_text = self.exclude_tables_text.get('1.0', tk.END).strip()
                exclude_tables = [t.strip() for t in exclude_text.split('\n') if t.strip()]

                # Normalize URLs before saving
                local_url = DatabaseConfig.normalize_url(self.local_url_entry.get())
                remote_url = DatabaseConfig.normalize_url(self.remote_url_entry.get())

                # Warn if URLs were modified during normalization
                original_local = self.local_url_entry.get().strip()
                original_remote = self.remote_url_entry.get().strip()

                if original_local and local_url != original_local:
                    messagebox.showwarning("URL Modified",
                                          f"Local URL was normalized:\n\n"
                                          f"From: {original_local}\n"
                                          f"To: {local_url}")

                if original_remote and remote_url != original_remote:
                    messagebox.showwarning("URL Modified",
                                          f"Remote URL was normalized:\n\n"
                                          f"From: {original_remote}\n"
                                          f"To: {remote_url}\n\n"
                                          f"Trailing slashes have been removed and\n"
                                          f"URL format has been validated.")

                database_config = DatabaseConfig(
                    local_db_name=self.local_db_name_entry.get(),
                    local_db_host=self.local_db_host_entry.get(),
                    local_db_port=int(self.local_db_port_entry.get()) if self.local_db_port_entry.get() else 3306,
                    local_db_user=self.local_db_user_entry.get(),
                    local_table_prefix=self.local_table_prefix_entry.get() or "wp_",
                    remote_db_name=self.remote_db_name_entry.get(),
                    remote_db_host=self.remote_db_host_entry.get(),
                    remote_db_port=int(self.remote_db_port_entry.get()) if self.remote_db_port_entry.get() else 3306,
                    remote_db_user=self.remote_db_user_entry.get(),
                    remote_table_prefix=self.remote_table_prefix_entry.get() or "wp_",
                    local_url=local_url,
                    remote_url=remote_url,
                    exclude_tables=exclude_tables,
                    backup_before_import=self.backup_before_import_var.get(),
                    require_confirmation_on_push=self.require_confirmation_var.get()
                )

                # Save database passwords to keyring
                local_password = self.local_db_password_entry.get()
                if local_password:
                    self.config_service.set_database_password(site_id, 'local', local_password)

                remote_password = self.remote_db_password_entry.get()
                if remote_password:
                    self.config_service.set_database_password(site_id, 'remote', remote_password)

            except ValueError as e:
                messagebox.showerror("Validation Error", f"Invalid database port number: {e}")
                return

        # Create site config
        site_config = SiteConfig(
            id=site_id,
            name=self.name_entry.get(),
            local_path=self.local_path_entry.get(),
            git_repo_path=self.git_path_entry.get(),
            remote_host=self.host_entry.get(),
            remote_port=int(self.port_entry.get()),
            remote_path=self.remote_path_entry.get(),
            remote_username=self.username_entry.get(),
            site_url=self.site_url_entry.get(),
            pull_include_paths=pull_include_paths,
            push_newer_only=self.push_newer_only_var.get(),
            use_compression=self.use_compression_var.get(),
            compress_folders=compress_folders,
            database_config=database_config
        )

        # Save password to keyring
        password = self.password_entry.get()
        if password:
            self.config_service.set_password(site_id, password)

        # Add or update site
        try:
            if self.site:
                self.config_service.update_site(site_config)
            else:
                self.config_service.add_site(site_config, password)

            self.result = True
            self.dialog.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save site: {e}")

    def cancel(self):
        """Cancel and close dialog"""
        self.result = False
        self.dialog.destroy()

"""
Site configuration dialog
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import uuid
import os
from ..models.site_config import SiteConfig


class SiteDialog:
    """Dialog for adding/editing site configuration"""

    def __init__(self, parent, config_service, site=None):
        self.config_service = config_service
        self.site = site
        self.result = None

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Add Site" if site is None else "Edit Site")
        self.dialog.geometry("924x650")  # 32% wider than original (700 * 1.32 = 924)

        # Don't use transient or grab_set on macOS - causes focus issues
        # self.dialog.transient(parent)

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

        # Bind Return key to save when in text entries (not textarea)
        for widget in [self.name_entry, self.local_path_entry, self.git_path_entry,
                      self.host_entry, self.port_entry, self.username_entry,
                      self.password_entry, self.remote_path_entry, self.site_url_entry]:
            widget.bind('<Return>', lambda e: self.save())

    def create_widgets(self):
        """Create dialog widgets"""
        # Main frame
        main_frame = ttk.Frame(self.dialog, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Basic info
        basic_frame = ttk.LabelFrame(main_frame, text="Basic Information", padding=10)
        basic_frame.pack(fill=tk.X, pady=5)

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

        # Remote info
        remote_frame = ttk.LabelFrame(main_frame, text="Remote Server", padding=10)
        remote_frame.pack(fill=tk.X, pady=5)

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

        # Pull include paths
        paths_frame = ttk.LabelFrame(main_frame, text="Pull Include Paths (one per line)", padding=10)
        paths_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.include_paths_text = scrolledtext.ScrolledText(paths_frame, height=6)
        self.include_paths_text.pack(fill=tk.BOTH, expand=True)
        self.include_paths_text.insert(1.0, "wp-content/uploads\nwp-content/themes/my-theme\nwp-content/plugins/my-plugin")

        # Buttons - make them bigger and more clickable
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=15)

        self.save_button = ttk.Button(button_frame, text="💾 Save Site", command=self.save,
                                      style="Accent.TButton")
        self.save_button.pack(side=tk.LEFT, padx=5, ipady=10, ipadx=20)

        self.cancel_button = ttk.Button(button_frame, text="✖ Cancel", command=self.cancel)
        self.cancel_button.pack(side=tk.LEFT, padx=5, ipady=10, ipadx=20)

    def browse_local(self):
        """Browse for local directory"""
        # Disable button to show it's been clicked
        self.browse_local_btn.config(state=tk.DISABLED, text="Browsing...")

        # Get current value as initial directory
        initial_dir = self.local_path_entry.get().strip() or None

        directory = filedialog.askdirectory(
            parent=self.dialog,
            title="Select Local WordPress Directory",
            initialdir=initial_dir,
            mustexist=True
        )

        # Re-enable button
        self.browse_local_btn.config(state=tk.NORMAL, text="📁 Browse")

        if directory:
            self.local_path_entry.delete(0, tk.END)
            self.local_path_entry.insert(0, directory)
            # Auto-detect Git repository
            self.check_and_set_git_repo(directory)

        # Return focus to dialog
        self.dialog.lift()
        self.dialog.focus_force()

    def browse_git(self):
        """Browse for Git repository directory"""
        # Disable button to show it's been clicked
        self.browse_git_btn.config(state=tk.DISABLED, text="Browsing...")

        # Get current value as initial directory
        initial_dir = self.git_path_entry.get().strip() or None

        directory = filedialog.askdirectory(
            parent=self.dialog,
            title="Select Git Repository Directory",
            initialdir=initial_dir,
            mustexist=True
        )

        # Re-enable button
        self.browse_git_btn.config(state=tk.NORMAL, text="📁 Browse")

        if directory:
            self.git_path_entry.delete(0, tk.END)
            self.git_path_entry.insert(0, directory)

        # Return focus to dialog
        self.dialog.lift()
        self.dialog.focus_force()

    def same_as_local(self):
        """Set Git path same as local path"""
        local_path = self.local_path_entry.get()
        if local_path:
            self.git_path_entry.delete(0, tk.END)
            self.git_path_entry.insert(0, local_path)
            self.check_git_repo_status(local_path)

    def is_git_repository(self, path):
        """Check if a directory is a Git repository"""
        if not path or not os.path.exists(path):
            return False
        git_dir = os.path.join(path, '.git')
        return os.path.isdir(git_dir)

    def check_and_set_git_repo(self, path):
        """Check if path is a Git repo and auto-fill if it is"""
        if self.is_git_repository(path):
            self.git_path_entry.delete(0, tk.END)
            self.git_path_entry.insert(0, path)
            self.git_status_label.config(text="✓ Git repository detected", foreground="green")
        else:
            self.git_status_label.config(text="⚠ No Git repository found", foreground="orange")

    def check_git_repo_status(self, path):
        """Just check and update status without auto-filling"""
        if self.is_git_repository(path):
            self.git_status_label.config(text="✓ Git repository detected", foreground="green")
        else:
            self.git_status_label.config(text="⚠ No Git repository found", foreground="orange")

    def load_site_data(self):
        """Load existing site data into form"""
        self.name_entry.insert(0, self.site.name)
        self.local_path_entry.insert(0, self.site.local_path)
        self.git_path_entry.insert(0, self.site.git_repo_path)
        self.host_entry.insert(0, self.site.remote_host)
        self.port_entry.delete(0, tk.END)
        self.port_entry.insert(0, str(self.site.remote_port))
        self.username_entry.insert(0, self.site.remote_username)
        self.remote_path_entry.insert(0, self.site.remote_path)
        self.site_url_entry.insert(0, self.site.site_url if self.site.site_url else "")

        # Load include paths
        if self.site.pull_include_paths:
            self.include_paths_text.delete(1.0, tk.END)
            self.include_paths_text.insert(1.0, '\n'.join(self.site.pull_include_paths))

        # Load password
        password = self.config_service.get_password(self.site.id)
        if password:
            self.password_entry.insert(0, password)

    def validate(self):
        """Validate form data"""
        if not self.name_entry.get().strip():
            messagebox.showerror("Error", "Please enter site name")
            return False

        if not self.local_path_entry.get().strip():
            messagebox.showerror("Error", "Please enter local path")
            return False

        if not self.git_path_entry.get().strip():
            messagebox.showerror("Error", "Please enter Git repository path")
            return False

        if not self.host_entry.get().strip():
            messagebox.showerror("Error", "Please enter remote host")
            return False

        if not self.username_entry.get().strip():
            messagebox.showerror("Error", "Please enter remote username")
            return False

        if not self.password_entry.get().strip():
            messagebox.showerror("Error", "Please enter password")
            return False

        if not self.remote_path_entry.get().strip():
            messagebox.showerror("Error", "Please enter remote path")
            return False

        try:
            port = int(self.port_entry.get())
            if port < 1 or port > 65535:
                raise ValueError()
        except ValueError:
            messagebox.showerror("Error", "Invalid port number")
            return False

        return True

    def save(self):
        """Save site configuration"""
        import logging
        logger = logging.getLogger('wp-deploy')
        logger.info("Save button clicked in site dialog")

        # Disable button to prevent double-clicks
        self.save_button.config(state=tk.DISABLED, text="Saving...")

        if not self.validate():
            self.save_button.config(state=tk.NORMAL, text="💾 Save Site")
            return

        # Get include paths
        include_paths = [line.strip() for line in self.include_paths_text.get(1.0, tk.END).split('\n') if line.strip()]

        # Create or update site config
        if self.site:
            site_id = self.site.id
        else:
            site_id = str(uuid.uuid4())[:8]

        site_config = SiteConfig(
            id=site_id,
            name=self.name_entry.get().strip(),
            local_path=self.local_path_entry.get().strip(),
            git_repo_path=self.git_path_entry.get().strip(),
            remote_host=self.host_entry.get().strip(),
            remote_port=int(self.port_entry.get()),
            remote_path=self.remote_path_entry.get().strip(),
            remote_username=self.username_entry.get().strip(),
            site_url=self.site_url_entry.get().strip(),
            pull_include_paths=include_paths
        )

        if self.site:
            # Preserve last_pushed_commit
            site_config.last_pushed_commit = self.site.last_pushed_commit
            site_config.created_at = self.site.created_at

        password = self.password_entry.get().strip()

        try:
            if self.site:
                self.config_service.update_site(site_config)
                logger.info(f"Updated site: {site_config.name}")
            else:
                self.config_service.add_site(site_config)
                logger.info(f"Added site: {site_config.name}")

            # Save password
            self.config_service.set_password(site_id, password)

            messagebox.showinfo("Success", "Site configuration saved")
            self.result = site_config
            self.dialog.destroy()

        except Exception as e:
            logger.error(f"Failed to save site: {e}")
            messagebox.showerror("Error", f"Failed to save site: {e}")
            self.save_button.config(state=tk.NORMAL, text="💾 Save Site")

    def cancel(self):
        """Cancel dialog"""
        import logging
        logger = logging.getLogger('wp-deploy')
        logger.info("Cancel button clicked - closing dialog")

        try:
            self.dialog.destroy()
            logger.info("Dialog destroyed successfully")
        except Exception as e:
            logger.error(f"Error closing dialog: {e}")

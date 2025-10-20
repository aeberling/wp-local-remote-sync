"""
Main GUI window for WordPress deployment tool
"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from datetime import datetime, timedelta
from threading import Thread
import sys
import os
from pathlib import Path
from ..services.config_service import ConfigService
from ..controllers.push_controller import PushController
from ..controllers.pull_controller import PullController
from ..controllers.db_push_controller import DBPushController
from ..controllers.db_pull_controller import DBPullController
from ..models.site_config import SiteConfig

# Import Sun Valley theme
from .. import sv_ttk


class ProgressDialog:
    """Simple progress dialog for showing operation status"""

    def __init__(self, parent, title, message):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("400x150")

        # Center dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (self.dialog.winfo_width() // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")

        # Create widgets
        frame = ttk.Frame(self.dialog, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        self.label = ttk.Label(frame, text=message, wraplength=350)
        self.label.pack(pady=10)

        self.progress = ttk.Progressbar(frame, mode='indeterminate', length=300)
        self.progress.pack(pady=10)
        self.progress.start(10)

        # Make it appear on top
        self.dialog.lift()
        self.dialog.attributes('-topmost', True)
        self.dialog.update()
        self.dialog.attributes('-topmost', False)

    def update_message(self, message):
        """Update the message text"""
        self.label.config(text=message)
        self.dialog.update()

    def close(self):
        """Close the dialog"""
        self.progress.stop()
        self.dialog.destroy()


class MainWindow:
    """Main application window"""

    def __init__(self, root):
        self.root = root
        self.root.title("WordPress Deployment Tool")
        self.root.geometry("1100x700")  # Reduced height for better screen fit

        # Set window icon
        try:
            icon_path = Path(__file__).parent.parent.parent / 'assets' / 'icon.png'
            if icon_path.exists():
                icon = tk.PhotoImage(file=str(icon_path))
                self.root.iconphoto(True, icon)
        except Exception as e:
            pass  # Silently fail if icon not found

        # Apply Sun Valley theme - auto-detects system dark/light mode
        sv_ttk.set_theme("dark")  # or "light" - will auto-detect system preference

        # Initialize services
        self.config_service = ConfigService()
        self.push_controller = PushController(self.config_service)
        self.pull_controller = PullController(self.config_service)
        self.db_push_controller = DBPushController(self.config_service)
        self.db_pull_controller = DBPullController(self.config_service)

        # Create UI
        self.create_widgets()
        self.refresh_sites()

        # Log startup
        import logging
        logger = logging.getLogger('wp-deploy')
        logger.info("Application started with Sun Valley theme")

        # macOS focus fix - activate the app properly
        self.setup_macos_focus_fix()

        # Bind click events to restore focus
        self.root.bind('<Button-1>', self.ensure_focus)
        self.root.bind('<FocusIn>', self.on_focus_in)

    def setup_macos_focus_fix(self):
        """Setup macOS-specific focus handling"""
        import platform
        if platform.system() == 'Darwin':  # macOS
            # Force window to front and activate
            self.root.lift()
            self.root.attributes('-topmost', True)
            self.root.after(100, lambda: self.root.attributes('-topmost', False))

            # Try to activate the application using AppleScript
            try:
                import subprocess
                script = 'tell application "System Events" to set frontmost of first process whose unix id is {} to true'.format(
                    os.getpid()
                )
                subprocess.run(['osascript', '-e', script], capture_output=True)
            except Exception as e:
                import logging
                logger = logging.getLogger('wp-deploy')
                logger.debug(f"Could not activate app via AppleScript: {e}")

    def ensure_focus(self, event=None):
        """Ensure the window has focus when clicked"""
        # Only process clicks on the window itself, not its children
        if event and event.widget == self.root:
            self.root.lift()
            self.root.focus_force()

    def on_focus_in(self, event=None):
        """Handle focus gained event"""
        # Update window to ensure proper event processing
        try:
            self.root.update_idletasks()
        except:
            pass

    def create_widgets(self):
        """Create all UI widgets"""
        # Main container
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create notebook (tabs)
        self.notebook = ttk.Notebook(main_container)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Create tabs
        self.push_frame = ttk.Frame(self.notebook)
        self.pull_frame = ttk.Frame(self.notebook)
        self.config_frame = ttk.Frame(self.notebook)

        self.notebook.add(self.push_frame, text="Push to Remote")
        self.notebook.add(self.pull_frame, text="Pull from Remote")
        self.notebook.add(self.config_frame, text="Configuration")

        # Setup each tab
        self.setup_push_tab()
        self.setup_pull_tab()
        self.setup_config_tab()

        # Add log viewer at bottom
        log_frame = ttk.LabelFrame(main_container, text="Activity Log", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=False, pady=(10, 0))

        from .log_viewer import LogViewer
        self.log_viewer = LogViewer(log_frame)
        self.log_viewer.pack(fill=tk.BOTH, expand=True)

        # Button to clear logs
        clear_btn = ttk.Button(log_frame, text="Clear Log", command=self.log_viewer.clear)
        clear_btn.pack(side=tk.BOTTOM, pady=5, ipady=3, ipadx=10)

    def setup_push_tab(self):
        """Setup push tab"""
        # Site selection
        select_frame = ttk.LabelFrame(self.push_frame, text="Select Site", padding=10)
        select_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(select_frame, text="Site:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.push_site_combo = ttk.Combobox(select_frame, state="readonly", width=40)
        self.push_site_combo.grid(row=0, column=1, sticky=tk.W, pady=5, padx=5)
        self.push_site_combo.bind('<<ComboboxSelected>>', self.on_push_site_selected)

        ttk.Button(select_frame, text="Refresh", command=self.refresh_sites).grid(row=0, column=2, padx=5)

        # Preview frame
        preview_frame = ttk.LabelFrame(self.push_frame, text="Files to Push", padding=10)
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        preview_btn = ttk.Button(preview_frame, text="👁️ Preview Files", command=self.preview_push,
                                style="Accent.TButton")
        preview_btn.pack(pady=5, ipady=8, ipadx=15)

        self.push_preview_text = scrolledtext.ScrolledText(preview_frame, height=10, width=80)
        self.push_preview_text.pack(fill=tk.BOTH, expand=True, pady=5)

        # Action buttons
        button_frame = ttk.Frame(self.push_frame)
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        self.push_button = ttk.Button(button_frame, text="▲ PUSH UPDATED GIT FILES", command=self.do_push,
                                      style="Accent.TButton")
        self.push_button.pack(side=tk.LEFT, padx=5, ipady=12, ipadx=25)

        self.push_all_button = ttk.Button(button_frame, text="▲ PUSH ALL FILES", command=self.do_push_all,
                                          style="Accent.TButton")
        self.push_all_button.pack(side=tk.LEFT, padx=5, ipady=12, ipadx=25)

        self.db_push_button = ttk.Button(button_frame, text="🗄️ PUSH DATABASE", command=self.do_db_push,
                                         style="Accent.TButton")
        self.db_push_button.pack(side=tk.LEFT, padx=5, ipady=12, ipadx=25)

        # Status
        self.push_status = ttk.Label(self.push_frame, text="Ready", relief=tk.SUNKEN)
        self.push_status.pack(fill=tk.X, padx=10, pady=5)

    def setup_pull_tab(self):
        """Setup pull tab"""
        # Site selection
        select_frame = ttk.LabelFrame(self.pull_frame, text="Select Site", padding=10)
        select_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(select_frame, text="Site:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.pull_site_combo = ttk.Combobox(select_frame, state="readonly", width=40)
        self.pull_site_combo.grid(row=0, column=1, sticky=tk.W, pady=5, padx=5)

        # Date range
        date_frame = ttk.LabelFrame(self.pull_frame, text="Date Range", padding=10)
        date_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(date_frame, text="Start Date (YYYY-MM-DD):").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.start_date_entry = ttk.Entry(date_frame, width=20)
        self.start_date_entry.grid(row=0, column=1, sticky=tk.W, pady=5, padx=5)
        # Default to 7 days ago
        default_start = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        self.start_date_entry.insert(0, default_start)

        ttk.Label(date_frame, text="End Date (YYYY-MM-DD):").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.end_date_entry = ttk.Entry(date_frame, width=20)
        self.end_date_entry.grid(row=1, column=1, sticky=tk.W, pady=5, padx=5)
        # Default to today
        default_end = datetime.now().strftime("%Y-%m-%d")
        self.end_date_entry.insert(0, default_end)

        # Quick date buttons
        quick_frame = ttk.Frame(date_frame)
        quick_frame.grid(row=2, column=0, columnspan=2, pady=5)

        ttk.Button(quick_frame, text="Last 7 Days", command=lambda: self.set_date_range(7)).pack(side=tk.LEFT, padx=2)
        ttk.Button(quick_frame, text="Last 30 Days", command=lambda: self.set_date_range(30)).pack(side=tk.LEFT, padx=2)

        # Include paths
        paths_frame = ttk.LabelFrame(self.pull_frame, text="Include Paths (one per line)", padding=10)
        paths_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.pull_paths_text = scrolledtext.ScrolledText(paths_frame, height=6, width=80)
        self.pull_paths_text.pack(fill=tk.BOTH, expand=True)

        # Preview frame
        preview_frame = ttk.LabelFrame(self.pull_frame, text="Files to Pull", padding=10)
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        preview_pull_btn = ttk.Button(preview_frame, text="👁️ Preview Files", command=self.preview_pull,
                                     style="Accent.TButton")
        preview_pull_btn.pack(pady=5, ipady=8, ipadx=15)

        self.pull_preview_text = scrolledtext.ScrolledText(preview_frame, height=8, width=80)
        self.pull_preview_text.pack(fill=tk.BOTH, expand=True, pady=5)

        # Action buttons
        button_frame = ttk.Frame(self.pull_frame)
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        self.pull_button = ttk.Button(button_frame, text="▼ PULL FILES", command=self.do_pull,
                                      style="Accent.TButton")
        self.pull_button.pack(side=tk.LEFT, padx=5, ipady=12, ipadx=25)

        self.db_pull_button = ttk.Button(button_frame, text="🗄️ PULL DATABASE", command=self.do_db_pull,
                                         style="Accent.TButton")
        self.db_pull_button.pack(side=tk.LEFT, padx=5, ipady=12, ipadx=25)

        # Status
        self.pull_status = ttk.Label(self.pull_frame, text="Ready", relief=tk.SUNKEN)
        self.pull_status.pack(fill=tk.X, padx=10, pady=5)

    def setup_config_tab(self):
        """Setup configuration tab"""
        # Site list with radio buttons
        list_frame = ttk.LabelFrame(self.config_frame, text="Sites", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create a canvas with scrollbar for sites
        canvas = tk.Canvas(list_frame, bg='#1e1e1e', highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=canvas.yview)
        self.sites_scroll_frame = ttk.Frame(canvas)

        self.sites_scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.sites_scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.selected_site_var = tk.StringVar()
        self.site_radiobuttons = []

        # Buttons
        button_frame = ttk.Frame(self.config_frame)
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        add_btn = ttk.Button(button_frame, text="➕ Add Site", command=self.add_site_dialog,
                            style="Accent.TButton")
        add_btn.pack(side=tk.LEFT, padx=5, ipady=8, ipadx=12)

        edit_btn = ttk.Button(button_frame, text="✏️ Edit Site", command=self.edit_site_dialog)
        edit_btn.pack(side=tk.LEFT, padx=5, ipady=8, ipadx=12)

        delete_btn = ttk.Button(button_frame, text="🗑️ Delete Site", command=self.delete_site)
        delete_btn.pack(side=tk.LEFT, padx=5, ipady=8, ipadx=12)

        test_btn = ttk.Button(button_frame, text="🔌 Test Connection", command=self.test_connection)
        test_btn.pack(side=tk.LEFT, padx=5, ipady=8, ipadx=12)

    def refresh_sites(self):
        """Refresh site list in all dropdowns and radio buttons"""
        sites = self.config_service.get_all_sites()

        # Update comboboxes
        site_names = [f"{site.name} ({site.id})" for site in sites]
        self.push_site_combo['values'] = site_names
        self.pull_site_combo['values'] = site_names

        # Clear existing radio buttons
        for widget in self.sites_scroll_frame.winfo_children():
            widget.destroy()
        self.site_radiobuttons = []

        # Create radio buttons for each site
        for i, site in enumerate(sites):
            # Frame for each site entry
            site_frame = ttk.Frame(self.sites_scroll_frame)
            site_frame.pack(fill=tk.X, padx=5, pady=3)

            # Radio button with site name and host
            rb = ttk.Radiobutton(
                site_frame,
                text=f"{site.name} - {site.remote_host}",
                variable=self.selected_site_var,
                value=site.id,
                style="TRadiobutton"
            )
            rb.pack(side=tk.LEFT, fill=tk.X, expand=True)

            # Preview button if URL is set
            if site.site_url:
                preview_btn = ttk.Button(
                    site_frame,
                    text="🌐 Preview",
                    command=lambda url=site.site_url: self.open_site_url(url),
                    width=12
                )
                preview_btn.pack(side=tk.RIGHT, padx=2)

            self.site_radiobuttons.append(rb)

        # Select first site if available
        if sites:
            self.selected_site_var.set(sites[0].id)
            self.push_site_combo.current(0)
            self.pull_site_combo.current(0)
            self.on_push_site_selected(None)

    def on_push_site_selected(self, event):
        """Handle site selection in push tab"""
        # Load site's pull include paths for reference
        site_id = self.get_selected_site_id(self.push_site_combo)
        if site_id:
            site = self.config_service.get_site(site_id)
            if site:
                self.push_preview_text.delete(1.0, tk.END)
                self.push_preview_text.insert(1.0, f"Site: {site.name}\n")
                self.push_preview_text.insert(tk.END, f"Local: {site.local_path}\n")
                self.push_preview_text.insert(tk.END, f"Remote: {site.remote_host}:{site.remote_path}\n\n")
                self.push_preview_text.insert(tk.END, "Click 'Preview Files' to see files that will be pushed.")

    def get_selected_site_id(self, combo):
        """Extract site ID from combobox selection"""
        selection = combo.get()
        if selection:
            # Extract ID from "Name (ID)" format
            return selection.split('(')[-1].rstrip(')')
        return None

    def set_date_range(self, days):
        """Set date range to last N days"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        self.start_date_entry.delete(0, tk.END)
        self.start_date_entry.insert(0, start_date.strftime("%Y-%m-%d"))

        self.end_date_entry.delete(0, tk.END)
        self.end_date_entry.insert(0, end_date.strftime("%Y-%m-%d"))

    def preview_push(self):
        """Preview files that will be pushed"""
        site_id = self.get_selected_site_id(self.push_site_combo)
        if not site_id:
            messagebox.showwarning("Warning", "Please select a site")
            return

        self.push_preview_text.delete(1.0, tk.END)
        self.push_preview_text.insert(1.0, "Loading...\n")

        def preview_thread():
            success, message, files = self.push_controller.get_files_to_push(site_id)

            def update_ui():
                self.push_preview_text.delete(1.0, tk.END)
                if success:
                    self.push_preview_text.insert(1.0, f"{message}\n\n")
                    if files:
                        for file in files:
                            self.push_preview_text.insert(tk.END, f"{file}\n")
                    else:
                        self.push_preview_text.insert(tk.END, "No files to push.")
                else:
                    self.push_preview_text.insert(1.0, f"Error: {message}")

            self.root.after(0, update_ui)

        Thread(target=preview_thread, daemon=True).start()

    def preview_pull(self):
        """Preview files that will be pulled"""
        site_id = self.get_selected_site_id(self.pull_site_combo)
        if not site_id:
            messagebox.showwarning("Warning", "Please select a site")
            return

        # Parse dates
        try:
            start_date = datetime.strptime(self.start_date_entry.get().strip(), "%Y-%m-%d")
            end_date = datetime.strptime(self.end_date_entry.get().strip(), "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Error", "Invalid date format. Use YYYY-MM-DD")
            return

        # Get include paths
        include_paths = [line.strip() for line in self.pull_paths_text.get(1.0, tk.END).split('\n') if line.strip()]

        if not include_paths:
            # Load from site config
            site = self.config_service.get_site(site_id)
            if site and site.pull_include_paths:
                include_paths = site.pull_include_paths
                # Display them
                self.pull_paths_text.delete(1.0, tk.END)
                self.pull_paths_text.insert(1.0, '\n'.join(include_paths))
            else:
                messagebox.showwarning("Warning", "Please specify include paths")
                return

        self.pull_preview_text.delete(1.0, tk.END)
        self.pull_preview_text.insert(1.0, "Loading...\n")

        def preview_thread():
            success, message, files = self.pull_controller.get_files_to_pull(site_id, start_date, end_date, include_paths)

            def update_ui():
                self.pull_preview_text.delete(1.0, tk.END)
                if success:
                    self.pull_preview_text.insert(1.0, f"{message}\n\n")
                    if files:
                        for file_path, mod_date in files:
                            self.pull_preview_text.insert(tk.END, f"{file_path}\n")
                    else:
                        self.pull_preview_text.insert(tk.END, "No files to pull.")
                else:
                    self.pull_preview_text.insert(1.0, f"Error: {message}")

            self.root.after(0, update_ui)

        Thread(target=preview_thread, daemon=True).start()

    def do_push(self):
        """Execute push operation"""
        import logging
        logger = logging.getLogger('wp-deploy')

        logger.info("=== PUSH OPERATION STARTED ===")

        site_id = self.get_selected_site_id(self.push_site_combo)
        if not site_id:
            logger.warning("No site selected for push operation")
            messagebox.showwarning("Warning", "Please select a site")
            return

        site = self.config_service.get_site(site_id)
        logger.info(f"Selected site: {site.name} ({site_id})")
        logger.info(f"Local path: {site.local_path}")
        logger.info(f"Remote: {site.remote_host}:{site.remote_path}")

        if not messagebox.askyesno("Confirm", f"Push files to {site.remote_host}?"):
            logger.info("Push operation cancelled by user")
            return

        # Visual feedback - button clicked
        self.push_button.config(state=tk.DISABLED, text="⏳ PUSHING...")
        self.push_status.config(text="Initializing push...")
        logger.info("Starting push operation...")

        def push_thread():
            def progress_callback(current, total, message):
                status_text = f"Pushing: {current}/{total} - {message}"
                self.root.after(0, lambda: self.push_status.config(text=status_text))
                logger.info(f"Progress: {current}/{total} - {message}")

            success, message, stats = self.push_controller.push(site_id, progress_callback)

            def update_ui():
                self.push_button.config(state=tk.NORMAL, text="▲ PUSH UPDATED GIT FILES")
                self.push_status.config(text=message)

                if success:
                    logger.info(f"✓ Push completed successfully: {stats['files_pushed']} files")
                    result = f"Push completed!\n\n"
                    result += f"Files pushed: {stats['files_pushed']}\n"
                    result += f"Bytes transferred: {stats['bytes_transferred']}\n"
                    if stats['files_failed'] > 0:
                        result += f"Files failed: {stats['files_failed']}\n"
                    messagebox.showinfo("Success", result)
                else:
                    logger.error(f"✗ Push failed: {message}")
                    messagebox.showerror("Error", message)

            self.root.after(0, update_ui)

        Thread(target=push_thread, daemon=True).start()

    def do_push_all(self):
        """Execute push ALL files operation"""
        import logging
        logger = logging.getLogger('wp-deploy')

        logger.info("=== PUSH ALL OPERATION STARTED ===")

        site_id = self.get_selected_site_id(self.push_site_combo)
        if not site_id:
            logger.warning("No site selected for push all operation")
            messagebox.showwarning("Warning", "Please select a site")
            return

        site = self.config_service.get_site(site_id)
        logger.info(f"Selected site: {site.name} ({site_id})")
        logger.info(f"Local path: {site.local_path}")
        logger.info(f"Remote: {site.remote_host}:{site.remote_path}")

        if not messagebox.askyesno("Confirm", f"Push ALL files from git repo to {site.remote_host}?\n\nThis will upload all tracked files, not just changes."):
            logger.info("Push all operation cancelled by user")
            return

        # Visual feedback - button clicked
        self.push_all_button.config(state=tk.DISABLED, text="⏳ PUSHING ALL...")
        self.push_status.config(text="Initializing push all...")
        logger.info("Starting push all operation...")

        def push_all_thread():
            def progress_callback(current, total, message):
                status_text = f"Pushing: {current}/{total} - {message}"
                self.root.after(0, lambda: self.push_status.config(text=status_text))
                logger.info(f"Progress: {current}/{total} - {message}")

            success, message, stats = self.push_controller.push_all(site_id, progress_callback)

            def update_ui():
                self.push_all_button.config(state=tk.NORMAL, text="▲ PUSH ALL FILES")
                self.push_status.config(text=message)

                if success:
                    logger.info(f"✓ Push all completed successfully: {stats['files_pushed']} files")
                    result = f"Push All completed!\n\n"
                    result += f"Files pushed: {stats['files_pushed']}\n"
                    result += f"Bytes transferred: {stats['bytes_transferred']}\n"
                    if stats['files_failed'] > 0:
                        result += f"Files failed: {stats['files_failed']}\n"
                    messagebox.showinfo("Success", result)
                else:
                    logger.error(f"✗ Push all failed: {message}")
                    messagebox.showerror("Error", message)

            self.root.after(0, update_ui)

        Thread(target=push_all_thread, daemon=True).start()

    def do_pull(self):
        """Execute pull operation"""
        site_id = self.get_selected_site_id(self.pull_site_combo)
        if not site_id:
            messagebox.showwarning("Warning", "Please select a site")
            return

        # Parse dates
        try:
            start_date = datetime.strptime(self.start_date_entry.get().strip(), "%Y-%m-%d")
            end_date = datetime.strptime(self.end_date_entry.get().strip(), "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Error", "Invalid date format. Use YYYY-MM-DD")
            return

        # Get include paths
        include_paths = [line.strip() for line in self.pull_paths_text.get(1.0, tk.END).split('\n') if line.strip()]

        if not include_paths:
            site = self.config_service.get_site(site_id)
            if site and site.pull_include_paths:
                include_paths = site.pull_include_paths
            else:
                messagebox.showwarning("Warning", "Please specify include paths")
                return

        if not messagebox.askyesno("Confirm", "Pull files from remote server? This will overwrite local files."):
            return

        self.pull_button.config(state=tk.DISABLED)
        self.pull_status.config(text="Pulling...")

        def pull_thread():
            def progress_callback(current, total, message):
                status_text = f"Pulling: {current}/{total} - {message}"
                self.root.after(0, lambda: self.pull_status.config(text=status_text))

            success, message, stats = self.pull_controller.pull(site_id, start_date, end_date, include_paths, progress_callback)

            def update_ui():
                self.pull_button.config(state=tk.NORMAL)
                self.pull_status.config(text=message)

                if success:
                    result = f"Pull completed!\n\n"
                    result += f"Files pulled: {stats['files_pulled']}\n"
                    result += f"Bytes transferred: {stats['bytes_transferred']}\n"
                    if stats['files_failed'] > 0:
                        result += f"Files failed: {stats['files_failed']}\n"
                    messagebox.showinfo("Success", result)
                else:
                    messagebox.showerror("Error", message)

            self.root.after(0, update_ui)

        Thread(target=pull_thread, daemon=True).start()

    def do_db_push(self):
        """Push database to remote"""
        # Get selected site
        selection = self.push_site_combo.get()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a site first")
            return

        site_id = selection.split('(')[1].rstrip(')')
        site = self.config_service.get_site(site_id)

        # Check if database is configured
        if not site.database_config:
            messagebox.showwarning("Not Configured",
                                 "Database not configured for this site.\n\n"
                                 "Please configure database settings in the Configuration tab.")
            return

        # Show warning for production push
        if site.database_config.require_confirmation_on_push:
            result = messagebox.askyesno("⚠️ Warning: Push Database to Production",
                                        f"You are about to OVERWRITE the PRODUCTION database with your local database.\n\n"
                                        f"Site: {site.name}\n"
                                        f"From: {site.database_config.local_url or 'Local'}\n"
                                        f"To: {site.database_config.remote_url or 'Production'}\n\n"
                                        f"This will:\n"
                                        f"  • Replace all content, posts, and pages\n"
                                        f"  • Potentially affect live users\n"
                                        f"  • Create a backup first (recommended)\n\n"
                                        f"Are you absolutely sure you want to continue?")
            if not result:
                return

        # Disable button
        self.db_push_button.config(state=tk.DISABLED)
        self.push_status.config(text="Pushing database...")

        # Show progress dialog
        progress = ProgressDialog(self.root, "Database Push", "Pushing database to remote server...")

        def db_push_thread():
            success, message, stats = self.db_push_controller.push(site_id)

            def update_ui():
                progress.close()
                self.db_push_button.config(state=tk.NORMAL)

                if success:
                    self.push_status.config(text=message)
                    messagebox.showinfo("Success", f"{message}\n\n"
                                                   f"Tables: {stats.get('tables_exported', 0)}\n"
                                                   f"URLs Replaced: {stats.get('urls_replaced', 0)}\n"
                                                   f"Backup: {stats.get('backup_created', 'None')}")
                else:
                    self.push_status.config(text="Error")
                    messagebox.showerror("Error", message)

            self.root.after(0, update_ui)

        Thread(target=db_push_thread, daemon=True).start()

    def do_db_pull(self):
        """Pull database from remote"""
        # Get selected site
        selection = self.pull_site_combo.get()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a site first")
            return

        site_id = selection.split('(')[1].rstrip(')')
        site = self.config_service.get_site(site_id)

        # Check if database is configured
        if not site.database_config:
            messagebox.showwarning("Not Configured",
                                 "Database not configured for this site.\n\n"
                                 "Please configure database settings in the Configuration tab.")
            return

        # Show info dialog
        result = messagebox.askyesno("Pull Database from Production",
                                    f"You are about to overwrite your LOCAL database with the production database.\n\n"
                                    f"Site: {site.name}\n"
                                    f"From: {site.database_config.remote_url or 'Production'}\n"
                                    f"To: {site.database_config.local_url or 'Local'}\n\n"
                                    f"Your local development work in the database will be lost.\n"
                                    f"A backup of your local database will be created.\n\n"
                                    f"Continue?")
        if not result:
            return

        # Disable button
        self.db_pull_button.config(state=tk.DISABLED)
        self.pull_status.config(text="Pulling database...")

        # Show progress dialog
        progress = ProgressDialog(self.root, "Database Pull", "Pulling database from remote server...")

        def db_pull_thread():
            success, message, stats = self.db_pull_controller.pull(site_id)

            def update_ui():
                progress.close()
                self.db_pull_button.config(state=tk.NORMAL)

                if success:
                    self.pull_status.config(text=message)
                    messagebox.showinfo("Success", f"{message}\n\n"
                                                   f"Tables: {stats.get('tables_exported', 0)}\n"
                                                   f"URLs Replaced: {stats.get('urls_replaced', 0)}\n"
                                                   f"Backup: {stats.get('backup_created', 'None')}")
                else:
                    self.pull_status.config(text="Error")
                    messagebox.showerror("Error", message)

            self.root.after(0, update_ui)

        Thread(target=db_pull_thread, daemon=True).start()

    def add_site_dialog(self):
        """Show dialog to add new site"""
        from .site_dialog import SiteDialog
        dialog = SiteDialog(self.root, self.config_service)
        self.root.wait_window(dialog.dialog)
        self.refresh_sites()

    def open_site_url(self, url):
        """Open site URL in default browser"""
        import webbrowser
        import logging
        logger = logging.getLogger('wp-deploy')
        logger.info(f"Opening site URL: {url}")
        webbrowser.open(url)

    def edit_site_dialog(self):
        """Show dialog to edit selected site"""
        import logging
        logger = logging.getLogger('wp-deploy')
        logger.info("Edit Site button clicked")

        site_id = self.selected_site_var.get()
        if not site_id:
            logger.warning("No site selected for editing")
            messagebox.showwarning("Warning", "Please select a site to edit")
            return

        site = self.config_service.get_site(site_id)
        if not site:
            logger.error(f"Site not found: {site_id}")
            messagebox.showerror("Error", "Selected site not found")
            return

        logger.info(f"Editing site: {site.name}")

        from .site_dialog import SiteDialog
        dialog = SiteDialog(self.root, self.config_service, site)
        self.root.wait_window(dialog.dialog)
        self.refresh_sites()
        logger.info("Site edit dialog closed")

    def delete_site(self):
        """Delete selected site"""
        site_id = self.selected_site_var.get()
        if not site_id:
            messagebox.showwarning("Warning", "Please select a site to delete")
            return

        site = self.config_service.get_site(site_id)
        if not site:
            messagebox.showerror("Error", "Selected site not found")
            return

        if messagebox.askyesno("Confirm", f"Delete site '{site.name}'?"):
            self.config_service.delete_site(site.id)
            self.refresh_sites()
            messagebox.showinfo("Success", "Site deleted")

    def test_connection(self):
        """Test SFTP connection for selected site"""
        site_id = self.selected_site_var.get()
        if not site_id:
            messagebox.showwarning("Warning", "Please select a site to test")
            return

        site = self.config_service.get_site(site_id)
        if not site:
            messagebox.showerror("Error", "Selected site not found")
            return

        password = self.config_service.get_password(site.id)
        if not password:
            messagebox.showerror("Error", "Password not found in keyring")
            return

        # Show progress dialog immediately
        progress = ProgressDialog(
            self.root,
            "Testing Connection",
            f"Connecting to {site.remote_host}...\nPlease wait..."
        )

        def test_thread():
            from ..services.sftp_service import SFTPService

            def update_progress(msg):
                self.root.after(0, lambda: progress.update_message(msg))

            try:
                update_progress(f"Connecting to {site.remote_host}:{site.remote_port}...")
                sftp = SFTPService(site.remote_host, site.remote_port, site.remote_username, password)

                update_progress("Authenticating...")
                success, message = sftp.test_connection()

                def update_ui():
                    progress.close()
                    if success:
                        messagebox.showinfo("Success", f"Connection successful!\n\nConnected to: {site.remote_host}")
                    else:
                        messagebox.showerror("Error", f"Connection failed:\n\n{message}")

                self.root.after(0, update_ui)
            except Exception as e:
                def update_ui():
                    progress.close()
                    messagebox.showerror("Error", f"Connection failed:\n\n{str(e)}")
                self.root.after(0, update_ui)

        Thread(target=test_thread, daemon=True).start()


def run_gui():
    """Run the GUI application"""
    root = tk.Tk()
    app = MainWindow(root)
    root.mainloop()

"""
Real-time log viewer widget
"""
import tkinter as tk
from tkinter import ttk, scrolledtext
import logging
import queue
from pathlib import Path


class LogHandler(logging.Handler):
    """Custom logging handler that sends logs to a queue"""

    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        log_entry = self.format(record)
        self.log_queue.put(log_entry)


class LogViewer(ttk.Frame):
    """Real-time log viewer widget"""

    def __init__(self, parent):
        super().__init__(parent)

        # Create text widget
        self.text = scrolledtext.ScrolledText(self, height=6, width=100, wrap=tk.WORD)
        self.text.pack(fill=tk.BOTH, expand=True)

        # Configure tags for colors
        self.text.tag_config("INFO", foreground="blue")
        self.text.tag_config("WARNING", foreground="orange")
        self.text.tag_config("ERROR", foreground="red")
        self.text.tag_config("SUCCESS", foreground="green")

        # Create queue for logs
        self.log_queue = queue.Queue()

        # Set up logging handler
        self.setup_logging()

        # Start checking for new logs
        self.check_queue()

    def setup_logging(self):
        """Set up logging handler"""
        # Get root logger
        logger = logging.getLogger()

        # Create and add handler
        handler = LogHandler(self.log_queue)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                                     datefmt='%H:%M:%S')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    def check_queue(self):
        """Check for new log entries"""
        while True:
            try:
                log_entry = self.log_queue.get_nowait()
                self.add_log(log_entry)
            except queue.Empty:
                break

        # Check again in 100ms
        self.after(100, self.check_queue)

    def add_log(self, log_entry):
        """Add a log entry to the viewer"""
        self.text.insert(tk.END, log_entry + '\n')

        # Auto-scroll to bottom
        self.text.see(tk.END)

        # Limit to last 1000 lines
        lines = int(self.text.index('end-1c').split('.')[0])
        if lines > 1000:
            self.text.delete('1.0', '2.0')

    def clear(self):
        """Clear the log viewer"""
        self.text.delete('1.0', tk.END)

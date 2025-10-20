#!/usr/bin/env python3
"""
WordPress Deployment Tool
Main entry point
"""
import sys
from src.ui.main_window import run_gui


def main():
    """Main function"""
    print("WordPress Deployment Tool")
    print("=" * 50)
    print("Starting GUI application...")
    print()

    try:
        run_gui()
    except KeyboardInterrupt:
        print("\nApplication terminated by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

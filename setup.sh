#!/bin/bash

echo "WordPress Deployment Tool - Setup"
echo "=================================="
echo ""

# Check Python version
python_version=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
echo "Python version: $python_version"

# Create virtual environment
echo ""
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create config directory
echo ""
echo "Creating configuration directory..."
mkdir -p ~/.wp-deploy/logs

echo ""
echo "=================================="
echo "Setup complete!"
echo ""
echo "To start the application:"
echo "  1. Activate virtual environment: source venv/bin/activate"
echo "  2. Run the tool: python main.py"
echo ""
echo "Or simply run: ./run.sh"
echo ""
echo "For help, see QUICK_START.md"

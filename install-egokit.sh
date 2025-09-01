#!/bin/bash

# EgoKit Installation Script
# Simple installation that respects your Python environment choices

set -e  # Exit on error

echo "========================================="
echo "       EgoKit Installation Script        "
echo "========================================="
echo ""

# Determine script directory (EgoKit location)
EGOKIT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Check Python version
echo "📌 Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.10 or later."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
REQUIRED_VERSION="3.10"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "❌ Python $PYTHON_VERSION found, but Python $REQUIRED_VERSION or later is required."
    exit 1
fi

echo "✅ Python $PYTHON_VERSION found"
echo ""

# Detect current Python environment
if [ -n "$VIRTUAL_ENV" ]; then
    echo "🔍 Installing into active virtual environment: $(basename $VIRTUAL_ENV)"
    PIP_CMD="pip"
elif [ -n "$CONDA_DEFAULT_ENV" ]; then
    echo "🔍 Installing into active conda environment: $CONDA_DEFAULT_ENV"
    PIP_CMD="pip"
else
    echo "🔍 No virtual environment detected"
    echo "   Installing with pip3 (will use your default pip configuration)"
    PIP_CMD="pip3"
fi

echo "📁 Installing EgoKit from: $EGOKIT_DIR"
echo ""

# Install EgoKit in editable mode with dependencies
echo "📦 Installing EgoKit..."
cd "$EGOKIT_DIR"
$PIP_CMD install -e ".[dev]"

echo ""
echo "🔍 Verifying installation..."

# Verify installation
if command -v ego &> /dev/null; then
    echo "✅ EgoKit installed successfully!"
    echo ""
    echo "Test the installation:"
    echo "   ego --help"
else
    echo "✅ EgoKit installed!"
    echo ""
    echo "Note: 'ego' command may not be in your PATH."
    echo "Try: python3 -m egokit.cli --help"
fi

echo ""
echo "📝 Next steps:"
echo "   ego init --org \"Your Organization\"  # Initialize a policy registry"
echo "   ego apply --repo /path/to/project   # Apply policies to a project"
echo ""
echo "For more information, see: $EGOKIT_DIR/docs/getting-started.md"
echo ""
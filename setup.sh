#!/bin/bash

# 1. Enforce Python 3.12
if ! command -v python3.12 &> /dev/null
then
    echo "❌ ERROR: Python 3.12 is not installed!"
    echo "Please install it first (e.g., run: brew install python@3.12)"
    exit 1
fi

echo "✅ Python 3.12 found! Setting up the environment..."

# 2. Delete any old/broken environments just in case
rm -rf .venv

# 3. Create the strictly-3.12 environment
python3.12 -m venv .venv

# 4. Activate it
source .venv/bin/activate

# 5. Install the exact required packages
pip install --upgrade pip
echo ""
echo "📦 Installing dependencies from requirements.txt..."
echo ""

# 6. Install requirements AND check for errors
if pip install -r requirements.txt; then
    # This block ONLY runs if the pip install succeeds (exit code 0)
    echo ""
    echo ""
    echo "🎉 Setup complete!"
    echo "👉 To activate your environment in the terminal, type: source .venv/bin/activate"
    echo ""
    echo "===================================================="
    echo "🤖 WEBOTS CONFIGURATION PATH:"
    echo "Copy and paste this exact absolute path into Webots:"
    echo ""
    echo "$(pwd)/.venv/bin/python3.12"
    echo ""
    echo "===================================================="
else
    # This block runs if pip crashes
    echo ""
    echo ""
    echo "❌ ERROR: Failed to install packages!"
    echo "Please check the red text above to see which dependencies are fighting."
    echo "The environment setup was aborted."
    exit 1
fi
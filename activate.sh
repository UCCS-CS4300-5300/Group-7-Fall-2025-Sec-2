#!/bin/bash
# Helper script to activate the virtual environment
# Usage: source activate.sh

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV_PATH="$SCRIPT_DIR/venv"

if [ ! -d "$VENV_PATH" ]; then
    echo "Error: Virtual environment not found at $VENV_PATH"
    echo "Please create it first with: python3 -m venv venv"
    return 1
fi

source "$VENV_PATH/bin/activate"
echo "✓ Virtual environment activated!"
echo "  Python: $(which python)"
echo "  You can now run: python manage.py runserver"



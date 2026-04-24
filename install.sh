#!/bin/bash
set -e

echo ""
echo "  ┌─────────────────────────────────────┐"
echo "  │         Memra 1.0 — Install          │"
echo "  │  Your AI just got a memory.          │"
echo "  └─────────────────────────────────────┘"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3.9+ is required. Install it and try again."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "  Python: $PYTHON_VERSION"

# Create venv
if [ ! -d "venv" ]; then
    echo "  Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate
echo "  Virtual environment: activated"

# Install dependencies
echo "  Installing dependencies..."
pip install -q -e engine/

# API key
ENV_FILE=".env"
if [ ! -f "$ENV_FILE" ]; then
    echo ""
    echo "  Memra needs an API key to connect to a frontier model."
    echo "  (Anthropic recommended — get one at console.anthropic.com)"
    echo ""
    read -p "  Anthropic API key (sk-ant-...): " API_KEY

    if [ -n "$API_KEY" ]; then
        echo "ANTHROPIC_API_KEY=$API_KEY" > "$ENV_FILE"
        echo "  API key saved to .env"
    else
        echo "  Skipped. Set ANTHROPIC_API_KEY later in .env"
        echo "# ANTHROPIC_API_KEY=sk-ant-your-key-here" > "$ENV_FILE"
    fi
else
    echo "  .env file already exists — skipping API key setup"
fi

echo ""
echo "  ✓ Memra 1.0 installed."
echo ""
echo "  Next: run ./start.sh"
echo ""

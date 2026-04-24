#!/bin/bash
set -e

# Load environment
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Activate venv
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Check API key
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo ""
    echo "  Warning: ANTHROPIC_API_KEY not set."
    echo "  Run ./install.sh or add it to .env"
    echo ""
fi

echo ""
echo "  ┌─────────────────────────────────────┐"
echo "  │       Memra 1.0 — Starting           │"
echo "  │  Point your AI tool at:              │"
echo "  │  http://localhost:8000               │"
echo "  └─────────────────────────────────────┘"
echo ""

cd engine
uvicorn src.server:app --host 127.0.0.1 --port 8000

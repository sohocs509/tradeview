#!/usr/bin/env bash
# Start the Trading Platform backend
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/backend"

echo "=== Trading Platform Backend ==="
echo "Installing dependencies..."
pip install -r requirements.txt --break-system-packages -q 2>/dev/null || \
pip install -r requirements.txt -q

echo ""
echo "Starting FastAPI server on ws://0.0.0.0:8765"
echo "  REST API:    http://localhost:8765"
echo "  WebSocket:   ws://localhost:8765/ws/market/{symbol}"
echo "  Symbols:     http://localhost:8765/api/symbols"
echo "  Train ML:    http://localhost:8765/api/train/{symbol}"
echo ""
echo "Press Ctrl+C to stop."
echo ""

python main.py

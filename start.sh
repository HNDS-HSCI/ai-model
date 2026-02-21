#!/usr/bin/env bash
# Start script for Render deployment - v1.0.2
set -e

# Use the PORT environment variable provided by Render, or default to 8000
PORT=${PORT:-8000}

echo "[HSCI] Initializing Cognitive Engine v2.0.0..."
echo "[HSCI] Port: $PORT"

# Run the application
python run_app.py --host 0.0.0.0 --port $PORT --no-browser

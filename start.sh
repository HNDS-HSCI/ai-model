#!/bin/bash
# Start script for Render deployment

# Use the PORT environment variable provided by Render, or default to 8000
PORT=${PORT:-8000}

echo "Starting HSCI Cognitive Engine on port $PORT..."

# Run the application
python run_app.py --host 0.0.0.0 --port $PORT --no-browser

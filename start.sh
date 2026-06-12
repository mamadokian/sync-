#!/bin/sh
PORT=${PORT:-10000}

# Start dummy HTTP server so Render sees an open port immediately
python3 -m http.server "$PORT" &

# Run the sync
python3 /app/sync.py

# Keep container alive until Render puts it to sleep
wait

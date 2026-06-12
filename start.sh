#!/bin/sh
set -e

PORT=${PORT:-10000}

# Run sync FIRST in foreground so we see all logs
python3 /app/sync.py

# Start HTTP server to keep Render happy after sync
echo "Starting health server on port $PORT..."
exec python3 -m http.server "$PORT"

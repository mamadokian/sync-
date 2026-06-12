#!/bin/bash
set -e

# Replace with your actual repos
SOURCE_REPO="https://github.com/dvahana2424-web/sojogamesdatabase1.git"
PRIVATE_REPO="https://${GITHUB_TOKEN}@github.com/RafeShahraki/sojogamesdatabase1-backup.git"

# Setup: clone on first run
if [ ! -d "/app/repo-mirror.git" ]; then
    echo "First run: cloning mirror..."
    git clone --mirror "$SOURCE_REPO" /app/repo-mirror.git
    cd /app/repo-mirror.git
    git remote add private "$PRIVATE_REPO"
else
    cd /app/repo-mirror.git
fi

# Sync function
do_sync() {
    echo "=== Sync started at $(date) ==="
    git fetch origin --prune
    git push --mirror private
    echo "=== Sync completed at $(date) ==="
    echo ""
}

# Run immediately on start
do_sync

# Loop every 2 hours (7200 seconds)
while true; do
    echo "Sleeping for 2 hours..."
    sleep 7200
    do_sync
done

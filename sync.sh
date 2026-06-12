#!/bin/bash
set -e

# Config
SOURCE_REPO="https://github.com/source-org/source-repo.git"
PRIVATE_REPO="https://YOUR_GITHUB_TOKEN@github.com/your-username/your-private-repo.git"

# Clone if not exists, otherwise fetch
if [ ! -d "/app/repo-mirror.git" ]; then
    echo "First run: cloning mirror..."
    git clone --mirror "$SOURCE_REPO" /app/repo-mirror.git
    cd /app/repo-mirror.git
    git remote add private "$PRIVATE_REPO"
else
    cd /app/repo-mirror.git
    echo "Fetching updates from source..."
    git fetch origin --prune
fi

echo "Pushing to private repo..."
git push --mirror private

echo "Sync completed at $(date)"

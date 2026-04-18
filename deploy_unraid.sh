#!/bin/bash

# Optimized deployment script for etl-stats-server to Unraid
# Simplified version for compatibility with standard SSH settings.

SOURCE_DIR="/home/kostya/dev/personal/etl-stats-server/"
DESTINATION_PATH="/mnt/user/appdata/dockge/stacks/etl-stats-server/"
USER_HOST="root@unraid"

echo "🛑 Shutting down containers on Unraid..."
ssh "$USER_HOST" "
  docker stop etl-stats-frontend etl-stats-backend 2>/dev/null || true
  docker rm etl-stats-frontend etl-stats-backend 2>/dev/null || true
  docker rmi etl-stats-server-frontend etl-stats-server-backend 2>/dev/null || true
"

echo "🚀 Starting optimized sync to Unraid..."
# --include='.env' is placed BEFORE the gitignore filter so it bypasses the ignore rule.
rsync -avz --delete \
  --include='.env' \
  --filter=':- .gitignore' \
  --exclude '.git/' \
  --exclude '.env.example' \
  --exclude 'backend/.env.example' \
  --exclude 'backend/data/' \
  --exclude 'scripts/' \
  --exclude 'tests/' \
  --exclude '*.log' \
  --exclude '*.db' \
  "$SOURCE_DIR" "$USER_HOST:$DESTINATION_PATH"

echo "🚀 Restarting stack via Dockge..."
# This will trigger a fresh build because we deleted the old images in step 1
# We exec into the dockge container itself since the host is missing the compose binary
ssh "$USER_HOST" "docker exec dockge docker compose -f $DESTINATION_PATH/compose.yaml up -d"

echo "✅ Deployment complete! The stack is now running."

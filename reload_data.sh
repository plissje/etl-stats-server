#!/bin/bash

# Simple script to clear the database and reload all matches from the refs folder.

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Stopping services to free up database file..."
"$BASE_DIR/manage_services.sh" stop

echo "Resetting database and ingesting matches from refs/..."
cd "$BASE_DIR/backend"
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Run the ingestion script
python reset_and_ingest.py

echo "Restarting services..."
cd "$BASE_DIR"
"$BASE_DIR/manage_services.sh" start

echo "Data reload complete!"

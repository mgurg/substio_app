#!/usr/bin/env bash
set -euo pipefail

CONTAINER="substio_app_db"
DB_NAME="pg_db"

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <dump-file>"
  exit 1
fi

DUMP_FILE="$1"
TMP_PATH="/tmp/backup.dmp"

echo "=== PostgreSQL Restore Script ==="

# Check dump file exists
if [[ ! -f "$DUMP_FILE" ]]; then
  echo "❌ Error: Dump file '$DUMP_FILE' not found."
  exit 1
fi

# Copy dump file into container
echo "📥 Copying '$DUMP_FILE' into container..."
docker cp "$DUMP_FILE" "$CONTAINER:$TMP_PATH"

# Restore database
echo "🔄 Restoring database '$DB_NAME'..."
docker exec -i "$CONTAINER" bash -c \
  "pg_restore --clean --if-exists -U postgres -d $DB_NAME $TMP_PATH"

# Cleanup
echo "🧹 Cleaning up dump file from container..."
docker exec -i "$CONTAINER" rm "$TMP_PATH"

echo "✅ Restore completed successfully!"

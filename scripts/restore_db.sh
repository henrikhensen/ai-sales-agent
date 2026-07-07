#!/usr/bin/env bash
# Restore a PostgreSQL backup (created by backup_db.sh) into the running
# sales_agent_postgres Docker container.
#
# DESTRUCTIVE: overwrites all data currently in the target database. Asks
# for explicit confirmation before doing anything.
#
# Usage:  scripts/restore_db.sh ./backups/sales_agent_20260101_120000.sql

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

POSTGRES_USER="${POSTGRES_USER:-sales_agent}"
POSTGRES_DB="${POSTGRES_DB:-sales_agent}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-}"
CONTAINER_NAME="sales_agent_postgres"

BACKUP_FILE="${1:-}"
if [ -z "$BACKUP_FILE" ]; then
  echo "Usage: $0 <path-to-backup.sql>" >&2
  exit 1
fi
if [ ! -f "$BACKUP_FILE" ]; then
  echo "Backup file not found: $BACKUP_FILE" >&2
  exit 1
fi

if ! docker ps --format '{{.Names}}' | grep -qx "$CONTAINER_NAME"; then
  echo "Container '$CONTAINER_NAME' is not running. Start it with 'docker compose up -d postgres' first." >&2
  exit 1
fi

echo "WARNING: This will overwrite ALL data in database '$POSTGRES_DB' with the contents of $BACKUP_FILE."
echo "This cannot be undone unless you have another backup of the current data."
read -r -p "Type 'yes' to continue: " CONFIRMATION
if [ "$CONFIRMATION" != "yes" ]; then
  echo "Aborted. No changes were made."
  exit 1
fi

echo "Restoring $BACKUP_FILE into database '$POSTGRES_DB' ..."
docker exec -i -e PGPASSWORD="$POSTGRES_PASSWORD" "$CONTAINER_NAME" \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" < "$BACKUP_FILE"

echo "Restore complete."

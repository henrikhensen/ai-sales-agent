#!/usr/bin/env bash
# Create a timestamped PostgreSQL backup from the running
# sales_agent_postgres Docker container (plain-SQL pg_dump), and prune
# backups older than BACKUP_RETENTION_DAYS. Reads POSTGRES_USER,
# POSTGRES_DB, POSTGRES_PASSWORD, BACKUP_DIR, and BACKUP_RETENTION_DAYS
# from .env — never prints the password.
#
# Usage:  scripts/backup_db.sh

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
BACKUP_DIR="${BACKUP_DIR:-./backups}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-7}"
CONTAINER_NAME="sales_agent_postgres"

if ! docker ps --format '{{.Names}}' | grep -qx "$CONTAINER_NAME"; then
  echo "Container '$CONTAINER_NAME' is not running. Start it with 'docker compose up -d postgres' first." >&2
  exit 1
fi

mkdir -p "$BACKUP_DIR"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_FILE="$BACKUP_DIR/${POSTGRES_DB}_${TIMESTAMP}.sql"

echo "Backing up database '$POSTGRES_DB' to $BACKUP_FILE ..."
docker exec -e PGPASSWORD="$POSTGRES_PASSWORD" "$CONTAINER_NAME" \
  pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists > "$BACKUP_FILE"

echo "Backup complete: $BACKUP_FILE ($(du -h "$BACKUP_FILE" | cut -f1))"

if [ "$BACKUP_RETENTION_DAYS" -gt 0 ]; then
  echo "Removing backups older than $BACKUP_RETENTION_DAYS day(s) in $BACKUP_DIR ..."
  find "$BACKUP_DIR" -maxdepth 1 -name "${POSTGRES_DB}_*.sql" -mtime "+$BACKUP_RETENTION_DAYS" -print -delete
fi

echo "Done."

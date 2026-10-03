#!/usr/bin/env sh
# Daily PostgreSQL logical backup helper for production.
# Requires: pg_dump, gzip, and DATABASE_URL (libpq form) or PG* env vars.
set -eu

BACKUP_DIR="${BACKUP_DIR:-/var/backups/monitoring-agent}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "${BACKUP_DIR}"

OUT="${BACKUP_DIR}/monitoring_agent_${STAMP}.sql.gz"
echo "Writing backup to ${OUT}"

if [ -n "${DATABASE_URL:-}" ]; then
  # Convert SQLAlchemy async URL if needed.
  PG_URL="$(printf '%s' "${DATABASE_URL}" | sed 's|+asyncpg||')"
  pg_dump "${PG_URL}" | gzip -c > "${OUT}"
else
  pg_dump | gzip -c > "${OUT}"
fi

find "${BACKUP_DIR}" -type f -name 'monitoring_agent_*.sql.gz' -mtime +"${RETENTION_DAYS}" -delete
echo "Backup complete"

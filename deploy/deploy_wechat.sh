#!/usr/bin/env bash
set -euo pipefail

# Build & deploy web UI to remote server.
# - Builds `web/` (Vite) into `web/dist`
# - Uploads an archive to the server
# - Creates a timestamped backup of `/srv/html/wechat`
# - Deploys new files into `/srv/html/wechat`
#
# Usage examples:
#   bash deploy/deploy_wechat.sh
#   bash deploy/deploy_wechat.sh --user root --host 43.134.90.115
#   bash deploy/deploy_wechat.sh --build-script build:wechat:prod
#

HOST="43.134.90.115"
USER="root"
PORT="22"
REMOTE_DIR="/srv/html/wechat"
REMOTE_BACKUP_DIR="/srv/html/wechat_backups"
BUILD_SCRIPT="build:wechat"

usage() {
  cat <<EOF
Usage: $0 [options]

Options:
  --host <host>           Remote host (default: ${HOST})
  --user <user>           SSH user (default: ${USER})
  --port <port>           SSH port (default: ${PORT})
  --remote-dir <path>     Remote deploy dir (default: ${REMOTE_DIR})
  --backup-dir <path>     Remote backup dir (default: ${REMOTE_BACKUP_DIR})
  --build-script <name>   npm script to build (default: ${BUILD_SCRIPT})
  -h, --help              Show this help

Notes:
- Requires passwordless SSH (or an SSH agent) to ${USER}@${HOST}.
- Build runs locally in ./web (uses package-lock.json via `npm ci`).
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host) HOST="$2"; shift 2;;
    --user) USER="$2"; shift 2;;
    --port) PORT="$2"; shift 2;;
    --remote-dir) REMOTE_DIR="$2"; shift 2;;
    --backup-dir) REMOTE_BACKUP_DIR="$2"; shift 2;;
    --build-script) BUILD_SCRIPT="$2"; shift 2;;
    -h|--help) usage; exit 0;;
    *) echo "Unknown arg: $1"; echo; usage; exit 2;;
  esac
done

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WEB_DIR="${ROOT_DIR}/web"
DIST_DIR="${WEB_DIR}/dist"

if [[ ! -d "${WEB_DIR}" ]]; then
  echo "ERROR: web dir not found: ${WEB_DIR}" >&2
  exit 1
fi

TS="$(date +%Y%m%d_%H%M%S)"
ARCHIVE_NAME="wechat_dist_${TS}.tar.gz"
ARCHIVE_PATH="${ROOT_DIR}/.run/${ARCHIVE_NAME}"

mkdir -p "${ROOT_DIR}/.run"

echo "[1/5] Build web (${BUILD_SCRIPT})"
pushd "${WEB_DIR}" >/dev/null
npm ci
npm run "${BUILD_SCRIPT}"
popd >/dev/null

if [[ ! -d "${DIST_DIR}" ]]; then
  echo "ERROR: dist not found after build: ${DIST_DIR}" >&2
  exit 1
fi

# Create archive from dist contents.
rm -f "${ARCHIVE_PATH}"
(tar -C "${DIST_DIR}" -czf "${ARCHIVE_PATH}" .)

echo "[2/5] Upload archive to ${USER}@${HOST}"
REMOTE_TMP="/tmp/${ARCHIVE_NAME}"
scp -P "${PORT}" "${ARCHIVE_PATH}" "${USER}@${HOST}:${REMOTE_TMP}"

echo "[3/5] Backup remote dir (if exists)"
REMOTE_STAGE="${REMOTE_DIR}.staging_${TS}"
ssh -p "${PORT}" "${USER}@${HOST}" bash -lc "'
set -euo pipefail
mkdir -p "${REMOTE_BACKUP_DIR}"
if [[ -d "${REMOTE_DIR}" ]]; then
  tar -C "$(dirname "${REMOTE_DIR}")" -czf "${REMOTE_BACKUP_DIR}/wechat_${TS}.tar.gz" "$(basename "${REMOTE_DIR}")"
fi
rm -rf "${REMOTE_STAGE}"
mkdir -p "${REMOTE_STAGE}"
'
"

echo "[4/5] Extract & deploy to ${REMOTE_DIR}"
ssh -p "${PORT}" "${USER}@${HOST}" bash -lc "'
set -euo pipefail
# Extract uploaded archive into staging
 tar -xzf "${REMOTE_TMP}" -C "${REMOTE_STAGE}"

# Ensure target exists
mkdir -p "${REMOTE_DIR}"

# Prefer rsync for fast atomic-ish deploy
if command -v rsync >/dev/null 2>&1; then
  rsync -a --delete "${REMOTE_STAGE}/" "${REMOTE_DIR}/"
else
  # Fallback: replace contents
  rm -rf "${REMOTE_DIR}.old_${TS}" || true
  mv "${REMOTE_DIR}" "${REMOTE_DIR}.old_${TS}" || true
  mkdir -p "${REMOTE_DIR}"
  cp -a "${REMOTE_STAGE}/." "${REMOTE_DIR}/"
fi

rm -rf "${REMOTE_STAGE}"
rm -f "${REMOTE_TMP}"
'
"

echo "[5/5] Done"
echo "Deployed to: ${USER}@${HOST}:${REMOTE_DIR}"
echo "Backup (if existed): ${USER}@${HOST}:${REMOTE_BACKUP_DIR}/wechat_${TS}.tar.gz"

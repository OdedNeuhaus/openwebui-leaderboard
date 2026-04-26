#!/bin/sh
set -eu

WEB_DIR="/app/web"
SYNC_OUTPUT="${SYNC_OUTPUT:-$WEB_DIR/leaderboard-data.json}"
SYNC_INTERVAL_SECONDS="${SYNC_INTERVAL_SECONDS:-300}"

write_config() {
  cat > "$WEB_DIR/config.js" <<EOF
window.APP_CONFIG = {
  OPENWEBUI_URL: "${OPENWEBUI_URL:-https://your-openwebui-url.example.com}",
  BRAND_LOGO_URL: "${BRAND_LOGO_URL:-}",
};
EOF
}

sync_once() {
  if [ -z "${OPENWEBUI_DATABASE_URL:-}" ]; then
    return 1
  fi

  python3 /app/scripts/sync_openwebui.py \
    --database-url "${OPENWEBUI_DATABASE_URL}" \
    --output "${SYNC_OUTPUT}" \
    --top "${LEADERBOARD_TOP:-25}" \
    --active-window-hours "${ACTIVE_WINDOW_HOURS:-24}" \
    ${INCLUDE_ADMINS:+--include-admins}
}

ensure_data_file() {
  if [ -f "$SYNC_OUTPUT" ]; then
    return 0
  fi

  cp "$WEB_DIR/leaderboard-data.example.json" "$SYNC_OUTPUT"
}

write_config

if sync_once; then
  echo "Initial OpenWebUI sync completed."
else
  echo "OpenWebUI sync skipped or failed, using bundled example data."
  ensure_data_file
fi

if [ -n "${OPENWEBUI_DATABASE_URL:-}" ] && [ "${SYNC_INTERVAL_SECONDS}" -gt 0 ] 2>/dev/null; then
  (
    while true; do
      sleep "$SYNC_INTERVAL_SECONDS"
      sync_once || echo "Background sync failed; keeping previous leaderboard data."
    done
  ) &
fi

exec python3 -m http.server 8080 --directory "$WEB_DIR"

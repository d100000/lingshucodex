#!/usr/bin/env bash
# One-click Ubuntu deployment for Lingshu Codex.
#
# Usage:
#   bash scripts/deploy-ubuntu.sh
#
# What it does:
#   - Installs system dependencies, Python runtime, Node.js 20 if needed, and Nginx.
#   - Syncs the project into /opt/lingshu-codex by default.
#   - Creates a dedicated lingshu system user.
#   - Creates backend/.env with a generated JWT secret.
#   - Creates and initializes the SQLite database.
#   - Builds the Vue frontend.
#   - Installs a systemd service for the FastAPI backend.
#   - Installs an Nginx site serving frontend/dist and proxying /api + /ws.
#   - Leaves admin credentials unconfigured; first admin is created in the web admin setup page.

set -Eeuo pipefail

APP_NAME="lingshu-codex"
APP_USER="lingshu"
APP_GROUP="lingshu"
APP_HOME="/var/lib/${APP_NAME}"
DEFAULT_INSTALL_DIR="/opt/${APP_NAME}"
DEFAULT_BACKEND_PORT="8020"
DEFAULT_LLM_BASE_URL="https://bobdong.cn/v1"
DEFAULT_IMAGE_MODEL="gpt-image-2"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [[ -t 1 ]]; then
  C_RESET=$'\033[0m'
  C_GREEN=$'\033[0;32m'
  C_YELLOW=$'\033[1;33m'
  C_CYAN=$'\033[0;36m'
  C_RED=$'\033[0;31m'
else
  C_RESET=""
  C_GREEN=""
  C_YELLOW=""
  C_CYAN=""
  C_RED=""
fi

log() { echo "${C_CYAN}==>${C_RESET} $*"; }
ok() { echo "${C_GREEN}OK${C_RESET} $*"; }
warn() { echo "${C_YELLOW}WARN${C_RESET} $*"; }
die() { echo "${C_RED}ERROR${C_RESET} $*" >&2; exit 1; }

need_sudo() {
  if [[ "${EUID}" -ne 0 ]]; then
    sudo -v
  fi
}

as_root() {
  if [[ "${EUID}" -eq 0 ]]; then
    "$@"
  else
    sudo "$@"
  fi
}

as_app_user() {
  if [[ "${EUID}" -eq 0 ]]; then
    runuser -u "${APP_USER}" -- env HOME="${APP_HOME}" "$@"
  else
    sudo -u "${APP_USER}" env HOME="${APP_HOME}" "$@"
  fi
}

prompt() {
  local var_name="$1"
  local label="$2"
  local default_value="${3:-}"
  local answer
  if [[ -n "${!var_name:-}" ]]; then
    return
  fi
  if [[ -n "${default_value}" ]]; then
    read -r -p "${label} [${default_value}]: " answer
    printf -v "${var_name}" "%s" "${answer:-$default_value}"
  else
    read -r -p "${label}: " answer
    printf -v "${var_name}" "%s" "${answer}"
  fi
}

prompt_secret() {
  local var_name="$1"
  local label="$2"
  local answer
  if [[ -n "${!var_name:-}" ]]; then
    return
  fi
  read -r -s -p "${label} (optional, press Enter to skip): " answer
  echo
  printf -v "${var_name}" "%s" "${answer}"
}

yes_no() {
  local var_name="$1"
  local label="$2"
  local default_value="${3:-y}"
  local answer
  if [[ -n "${!var_name:-}" ]]; then
    return
  fi
  read -r -p "${label} [${default_value}]: " answer
  answer="${answer:-$default_value}"
  case "${answer,,}" in
    y|yes|1|true) printf -v "${var_name}" "true" ;;
    n|no|0|false) printf -v "${var_name}" "false" ;;
    *) die "Please answer y or n." ;;
  esac
}

detect_os() {
  if [[ ! -r /etc/os-release ]]; then
    die "This script supports Ubuntu/Debian-like servers with systemd."
  fi
  # shellcheck disable=SC1091
  . /etc/os-release
  case "${ID:-}" in
    ubuntu|debian) ;;
    *) warn "Detected ${PRETTY_NAME:-unknown OS}; continuing because it looks Debian-like." ;;
  esac
  command -v systemctl >/dev/null 2>&1 || die "systemd is required."
}

validate_source_tree() {
  [[ -f "${SOURCE_ROOT}/backend/requirements.txt" ]] || die "backend/requirements.txt not found. Run this script from the downloaded project."
  [[ -f "${SOURCE_ROOT}/frontend/package.json" ]] || die "frontend/package.json not found. Run this script from the downloaded project."
}

collect_config() {
  echo
  log "Deployment configuration"
  prompt INSTALL_DIR "Install directory" "${DEFAULT_INSTALL_DIR}"
  prompt SERVER_NAME "Domain or server IP for Nginx server_name" "_"
  prompt BACKEND_PORT "Backend local port" "${DEFAULT_BACKEND_PORT}"
  prompt LLM_BASE_URL "LLM base URL" "${DEFAULT_LLM_BASE_URL}"
  prompt_secret LLM_API_KEY "LLM API key"
  prompt_secret IMAGE_API_KEY "Image generation API key"
  yes_no ALLOW_REGISTER_YN "Allow public user registration after deployment?" "y"
  yes_no ENABLE_SSL_YN "Configure HTTPS with Certbot now? Requires a real domain pointing to this server" "n"

  [[ "${INSTALL_DIR}" != *[[:space:]]* && "${INSTALL_DIR}" != *"'"* ]] || die "Install directory must not contain whitespace or single quotes."
  [[ "${BACKEND_PORT}" =~ ^[0-9]+$ ]] || die "Backend port must be a number."
  if [[ "${SERVER_NAME}" == "_" && "${ENABLE_SSL_YN}" == "true" ]]; then
    warn "HTTPS is skipped because server_name is '_'."
    ENABLE_SSL_YN="false"
  fi
}

install_system_dependencies() {
  log "Installing system dependencies"
  as_root apt-get update
  as_root env DEBIAN_FRONTEND=noninteractive apt-get install -y \
    ca-certificates curl gnupg nginx python3 python3-venv python3-pip \
    build-essential openssl rsync

  local node_major=0
  if command -v node >/dev/null 2>&1; then
    node_major="$(node -p "Number(process.versions.node.split('.')[0])" 2>/dev/null || echo 0)"
  fi
  if [[ "${node_major}" -lt 18 ]]; then
    log "Installing Node.js 20"
    curl -fsSL https://deb.nodesource.com/setup_20.x | as_root bash -
    as_root env DEBIAN_FRONTEND=noninteractive apt-get install -y nodejs
  fi

  local final_node_major
  final_node_major="$(node -p "Number(process.versions.node.split('.')[0])" 2>/dev/null || echo 0)"
  [[ "${final_node_major}" -ge 18 ]] || die "Node.js 18+ is required, got $(node -v 2>/dev/null || echo missing)."
  ok "System dependencies ready"
}

create_app_user() {
  log "Preparing application user"
  if ! getent group "${APP_GROUP}" >/dev/null; then
    as_root groupadd --system "${APP_GROUP}"
  fi
  if ! id "${APP_USER}" >/dev/null 2>&1; then
    as_root useradd --system --gid "${APP_GROUP}" --home-dir "${APP_HOME}" --create-home --shell /usr/sbin/nologin "${APP_USER}"
  fi
  as_root mkdir -p "${APP_HOME}"
  as_root chown -R "${APP_USER}:${APP_GROUP}" "${APP_HOME}"
  ok "Application user ${APP_USER} ready"
}

sync_project() {
  log "Syncing project to ${INSTALL_DIR}"
  as_root mkdir -p "${INSTALL_DIR}"
  as_root rsync -a --delete \
    --exclude '.git' \
    --exclude '.DS_Store' \
    --exclude 'backend/.env' \
    --exclude 'backend/.venv' \
    --exclude 'backend/data' \
    --exclude 'frontend/node_modules' \
    --exclude 'frontend/dist' \
    "${SOURCE_ROOT}/" "${INSTALL_DIR}/"
  as_root mkdir -p "${INSTALL_DIR}/backend/data"
  as_root chown -R "${APP_USER}:${APP_GROUP}" "${INSTALL_DIR}"
  ok "Project synced"
}

write_env_file() {
  local env_file="${INSTALL_DIR}/backend/.env"
  local jwt_secret
  jwt_secret="$(openssl rand -hex 32)"

  if [[ -f "${env_file}" ]]; then
    warn "Existing backend/.env found; preserving it."
    as_root chown "${APP_USER}:${APP_GROUP}" "${env_file}"
    as_root chmod 640 "${env_file}"
    return
  fi

  log "Writing backend environment file"
  local cors_origins
  if [[ "${SERVER_NAME}" == "_" ]]; then
    cors_origins="http://localhost,http://127.0.0.1"
  else
    cors_origins="http://${SERVER_NAME},https://${SERVER_NAME}"
  fi

  as_root tee "${env_file}" >/dev/null <<EOF
LLM_BASE_URL=${LLM_BASE_URL}
LLM_API_KEY=${LLM_API_KEY}

IMAGE_BASE_URL=${LLM_BASE_URL}
IMAGE_API_KEY=${IMAGE_API_KEY}
IMAGE_MODEL=${DEFAULT_IMAGE_MODEL}
IMAGE_TIMEOUT=120
IMAGE_MAX_RETRIES=3
IMAGE_RETRY_BASE_DELAY=1.5
IMAGE_RETRY_MAX_DELAY=8.0

JWT_SECRET=${jwt_secret}
JWT_DAYS=30
ALLOW_REGISTER=${ALLOW_REGISTER_YN}

HOST=127.0.0.1
PORT=${BACKEND_PORT}
CORS_ORIGINS=${cors_origins}

DEFAULT_SECT=canglan
LLM_TIMEOUT=60
LLM_MAX_RETRIES=3
LLM_RETRY_BASE_DELAY=1.0
LLM_RETRY_MAX_DELAY=8.0
EOF
  as_root chown "${APP_USER}:${APP_GROUP}" "${env_file}"
  as_root chmod 640 "${env_file}"
  ok "backend/.env created"
}

install_app_dependencies() {
  log "Installing backend dependencies"
  as_app_user bash -lc "cd '${INSTALL_DIR}/backend' && python3 -m venv .venv && . .venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt"

  log "Initializing SQLite database"
  as_app_user bash -lc "cd '${INSTALL_DIR}/backend' && . .venv/bin/activate && python - <<'PY'
from app.store import _init_db
_init_db()
print('database initialized')
PY"

  log "Installing frontend dependencies and building"
  as_app_user bash -lc "cd '${INSTALL_DIR}/frontend' && rm -rf dist && if [ -f package-lock.json ]; then npm ci; else npm install; fi && npm run build"
  ok "Application dependencies ready"
}

write_systemd_service() {
  local service_file="/etc/systemd/system/${APP_NAME}.service"
  log "Writing systemd service ${service_file}"
  as_root tee "${service_file}" >/dev/null <<EOF
[Unit]
Description=Lingshu Codex Backend
After=network.target

[Service]
Type=simple
User=${APP_USER}
Group=${APP_GROUP}
WorkingDirectory=${INSTALL_DIR}/backend
EnvironmentFile=${INSTALL_DIR}/backend/.env
ExecStart=${INSTALL_DIR}/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port ${BACKEND_PORT}
Restart=always
RestartSec=3
TimeoutStopSec=20

[Install]
WantedBy=multi-user.target
EOF
  as_root systemctl daemon-reload
  as_root systemctl enable --now "${APP_NAME}.service"
  ok "systemd service started"
}

write_nginx_site() {
  local nginx_available="/etc/nginx/sites-available/${APP_NAME}"
  local nginx_enabled="/etc/nginx/sites-enabled/${APP_NAME}"
  local listen_directive="listen 80;"
  if [[ "${SERVER_NAME}" == "_" ]]; then
    listen_directive="listen 80 default_server;"
  fi
  log "Writing Nginx site ${nginx_available}"
  as_root tee "${nginx_available}" >/dev/null <<EOF
server {
    ${listen_directive}
    server_name ${SERVER_NAME};

    root ${INSTALL_DIR}/frontend/dist;
    index index.html;

    client_max_body_size 10m;

    location /api/ {
        proxy_pass http://127.0.0.1:${BACKEND_PORT}/api/;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /ws/ {
        proxy_pass http://127.0.0.1:${BACKEND_PORT}/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 3600;
        proxy_send_timeout 3600;
    }

    location = /health {
        proxy_pass http://127.0.0.1:${BACKEND_PORT}/health;
        proxy_set_header Host \$host;
    }

    location / {
        try_files \$uri \$uri/ /index.html;
    }
}
EOF
  as_root ln -sfn "${nginx_available}" "${nginx_enabled}"
  if [[ "${SERVER_NAME}" == "_" && -e /etc/nginx/sites-enabled/default ]]; then
    warn "Disabling the default Nginx site so this app can own the default server."
    as_root rm -f /etc/nginx/sites-enabled/default
  fi
  as_root nginx -t
  as_root systemctl enable --now nginx
  as_root systemctl reload nginx
  ok "Nginx site enabled"
}

configure_firewall() {
  if command -v ufw >/dev/null 2>&1 && as_root ufw status | grep -qi "Status: active"; then
    log "Configuring UFW for Nginx"
    as_root ufw allow "Nginx Full" >/dev/null || true
  fi
}

configure_ssl() {
  if [[ "${ENABLE_SSL_YN}" != "true" ]]; then
    return
  fi
  log "Installing Certbot and requesting certificate"
  as_root env DEBIAN_FRONTEND=noninteractive apt-get install -y certbot python3-certbot-nginx
  as_root certbot --nginx -d "${SERVER_NAME}" --non-interactive --agree-tos --redirect --register-unsafely-without-email
  ok "HTTPS configured"
}

verify_deployment() {
  log "Verifying deployment"
  as_root systemctl restart "${APP_NAME}.service"
  sleep 2
  as_root systemctl --no-pager --full status "${APP_NAME}.service" >/dev/null
  curl -fsS "http://127.0.0.1:${BACKEND_PORT}/health" >/dev/null
  as_root nginx -t >/dev/null
  ok "Backend health check passed"
}

print_next_steps() {
  local scheme="http"
  if [[ "${ENABLE_SSL_YN}" == "true" ]]; then
    scheme="https"
  fi
  local base_url
  if [[ "${SERVER_NAME}" == "_" ]]; then
    base_url="http://SERVER_IP"
  else
    base_url="${scheme}://${SERVER_NAME}"
  fi

  echo
  echo "${C_GREEN}Deployment complete.${C_RESET}"
  echo
  echo "Site:        ${base_url}/"
  echo "Admin setup: ${base_url}/#/admin-console/login"
  echo
  echo "First admin account:"
  echo "  Open the admin setup URL above and create the administrator username/password in the browser."
  echo "  No default admin credentials were created by this script."
  echo
  echo "Useful commands:"
  echo "  sudo systemctl status ${APP_NAME}"
  echo "  sudo journalctl -u ${APP_NAME} -f"
  echo "  sudo nginx -t && sudo systemctl reload nginx"
  echo
  echo "SQLite database:"
  echo "  ${INSTALL_DIR}/backend/data/lingshu.db"
}

main() {
  detect_os
  validate_source_tree
  need_sudo
  collect_config
  install_system_dependencies
  create_app_user
  sync_project
  write_env_file
  install_app_dependencies
  write_systemd_service
  write_nginx_site
  configure_firewall
  configure_ssl
  verify_deployment
  print_next_steps
}

main "$@"

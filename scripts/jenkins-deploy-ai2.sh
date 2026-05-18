#!/usr/bin/env bash
# Déploiement TikTak AI v2 (branche dev) → https://ai2.tiktakpro.com
#
# Jenkins sur le MÊME serveur (checkout SCM dans WORKSPACE) :
#   export LOCAL_DEPLOY=1
#   export SKIP_GIT=1
#   export APP_DIR="${WORKSPACE}"
#   export ENV_SOURCE="/home/tiktakpro/projects/tiktak-ai-v2/.env"
#   bash "${WORKSPACE}/scripts/jenkins-deploy-ai2.sh"
#
# Jenkins sur une autre machine (SSH vers le web) :
#   export WEB_HOST=197.5.150.216 WEB_USER=tiktakpro
#   bash scripts/jenkins-deploy-ai2.sh
set -Eeuo pipefail

WEB_HOST="${WEB_HOST:-197.5.150.216}"
WEB_USER="${WEB_USER:-tiktakpro}"
WEB_PORT="${WEB_PORT:-22}"
APP_DIR="${APP_DIR:-/home/tiktakpro/projects/tiktak-ai-v2}"
BRANCH="${BRANCH:-dev}"
COMPOSE_PROJECT="${COMPOSE_PROJECT:-tiktak-ai-v2}"
HEALTH_URL="${HEALTH_URL:-https://ai2.tiktakpro.com/}"
LOCAL_DEPLOY="${LOCAL_DEPLOY:-0}"
SKIP_GIT="${SKIP_GIT:-0}"
ENV_SOURCE="${ENV_SOURCE:-/home/tiktakpro/projects/tiktak-ai-v2/.env}"

_run_deploy() {
  local app_dir="$1" branch="$2" compose_project="$3" skip_git="$4" env_source="$5"
  bash -s -- "$app_dir" "$branch" "$compose_project" "$skip_git" "$env_source" <<'DEPLOY'
set -Eeuo pipefail

APP_DIR="$1"
BRANCH="$2"
COMPOSE_PROJECT="$3"
SKIP_GIT="$4"
ENV_SOURCE="$5"
LOCK_FILE="/tmp/ai2-deploy.lock"

exec 9>"$LOCK_FILE"
flock -n 9 || { echo "Another ai2 deploy is running, exit."; exit 1; }

[ -d "$APP_DIR" ] || { echo "APP_DIR not found: $APP_DIR"; exit 1; }
cd "$APP_DIR"

if [ "$SKIP_GIT" = "1" ]; then
  echo "[1/9] git skipped (Jenkins SCM already checked out)"
else
  echo "[1/9] git fetch/checkout/pull"
  git fetch origin
  git checkout "$BRANCH"
  git pull --ff-only origin "$BRANCH"
fi

echo "[2/9] verify files"
if [ ! -f ".env" ] && [ -n "$ENV_SOURCE" ] && [ -f "$ENV_SOURCE" ]; then
  ln -sf "$ENV_SOURCE" .env
  echo "linked .env ← $ENV_SOURCE"
fi
[ -f ".env" ] || { echo ".env missing (set ENV_SOURCE or create .env in $APP_DIR)"; exit 1; }
[ -f "docker-compose.yml" ] || { echo "docker-compose.yml missing"; exit 1; }
[ -f "docker-compose.override.devops.yml" ] || { echo "docker-compose.override.devops.yml missing"; exit 1; }

echo "[3/9] generate effective compose"
python3 - <<'PY'
from pathlib import Path

src = Path("docker-compose.yml").read_text().splitlines()
out = []
current = None
skip_ports = False
no_host_ports = {
    "backend-orchestrator",
    "frontend",
    "vision-service",
    "db",
    "redis",
}

for line in src:
    is_service = line.startswith("  ") and not line.startswith("    ") and line.rstrip().endswith(":")
    if is_service:
        current = line.strip()[:-1]
        skip_ports = False
    if current in no_host_ports and line.startswith("    ports:"):
        skip_ports = True
        continue
    if skip_ports:
        indent = len(line) - len(line.lstrip(" "))
        if indent <= 4:
            skip_ports = False
        else:
            continue
    out.append(line)

Path("docker-compose.effective.yml").write_text("\n".join(out) + "\n")
PY

echo "[4/9] compose config check"
docker compose \
  -f docker-compose.effective.yml \
  -f docker-compose.override.devops.yml \
  -p "$COMPOSE_PROJECT" \
  config >/dev/null

echo "[5/9] build & up"
docker compose \
  -f docker-compose.effective.yml \
  -f docker-compose.override.devops.yml \
  -p "$COMPOSE_PROJECT" \
  up -d --build

echo "[6/9] status"
docker compose \
  -f docker-compose.effective.yml \
  -f docker-compose.override.devops.yml \
  -p "$COMPOSE_PROJECT" \
  ps

echo "[7/9] wait for backend health"
for i in $(seq 1 30); do
  if curl -fsS http://127.0.0.1:8010/admin/login/ >/dev/null 2>&1; then
    echo "backend OK"
    break
  fi
  sleep 2
  if [ "$i" -eq 30 ]; then
    echo "backend health timeout on :8010"
    exit 1
  fi
done

echo "[8/9] local frontend health"
curl -fsS http://127.0.0.1:3011/ >/dev/null

echo "[9/9] done"
DEPLOY
}

echo "== AI2 (${BRANCH}) AUTODEPLOY START =="

if [ "$LOCAL_DEPLOY" = "1" ]; then
  echo "[mode] local (Jenkins on same server — no SSH)"
  _run_deploy "$APP_DIR" "$BRANCH" "$COMPOSE_PROJECT" "$SKIP_GIT" "$ENV_SOURCE"
else
  echo "[mode] remote SSH → ${WEB_USER}@${WEB_HOST}"
  ssh -p "$WEB_PORT" -o StrictHostKeyChecking=accept-new "${WEB_USER}@${WEB_HOST}" \
    "LOCAL_DEPLOY=1 APP_DIR=$(printf '%q' "$APP_DIR") BRANCH=$(printf '%q' "$BRANCH") COMPOSE_PROJECT=$(printf '%q' "$COMPOSE_PROJECT") bash -s" <<'WRAPPER'
set -Eeuo pipefail
SCRIPT="${APP_DIR}/scripts/jenkins-deploy-ai2.sh"
[ -f "$SCRIPT" ] || { echo "Missing $SCRIPT"; exit 1; }
export LOCAL_DEPLOY=1
exec bash "$SCRIPT"
WRAPPER
fi

echo "[jenkins] public health check"
curl -fsS "$HEALTH_URL" >/dev/null

echo "== AI2 AUTODEPLOY SUCCESS =="

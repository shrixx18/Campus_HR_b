#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${1:-/home/azureuser/Campus_HR_b}"
BRANCH="${2:-main}"

cd "$REPO_DIR"

git fetch origin "$BRANCH"
git checkout "$BRANCH"
git pull --ff-only origin "$BRANCH"

docker compose up -d --build --remove-orphans

docker compose ps
curl --fail --silent http://localhost:8080/health >/dev/null

echo "Deployment finished successfully."

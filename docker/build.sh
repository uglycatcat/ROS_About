#!/bin/bash
# ─────────────────────────────────────────────────────────
# 仅构建镜像（不启动）。日常请用 ./start.sh
# ─────────────────────────────────────────────────────────
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

export USER_UID="$(id -u)"
export USER_GID="$(id -g)"

echo ">>> 构建镜像 ros2-mujoco-dev:latest (UID=${USER_UID} GID=${USER_GID})"
DOCKER_BUILDKIT=1 docker compose build

echo ""
echo "构建完成。进入开发环境请运行: ./start.sh"

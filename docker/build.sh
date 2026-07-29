#!/bin/bash
# 仅构建镜像。日常用 ./container_init.sh
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

export USER_UID="$(id -u)"
export USER_GID="$(id -g)"

echo ">>> 构建镜像 ros2-mujoco-dev:latest"
DOCKER_BUILDKIT=1 docker compose build
echo "完成。进入环境: ./container_init.sh"

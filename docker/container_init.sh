#!/bin/bash
# ─────────────────────────────────────────────────────────
# 构建 → 启动容器 → 初始化工作区 → 进入 /workspace/ros2_ws
# 前置：Docker 已配置；基础镜像可本地已有（走国内源，无需代理）
# MuJoCo 源码请稍后在容器内自行运行: ./docker/mujoco_setup.sh
# ─────────────────────────────────────────────────────────
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

WS_DIR="/workspace/ros2_ws"
CONTAINER_NAME="petbot_ws"

export USER_UID="$(id -u)"
export USER_GID="$(id -g)"
export DISPLAY="${DISPLAY:-:1}"

# Xauthority
if [ -n "${XAUTHORITY:-}" ] && [ -f "$XAUTHORITY" ]; then
    export XAUTH_PATH="$XAUTHORITY"
elif [ -f "$HOME/.Xauthority" ]; then
    export XAUTH_PATH="$HOME/.Xauthority"
elif [ -f "/run/user/${USER_UID}/gdm/Xauthority" ]; then
    export XAUTH_PATH="/run/user/${USER_UID}/gdm/Xauthority"
else
    export XAUTH_PATH="/tmp/ros2-docker-xauth-empty"
    touch "$XAUTH_PATH"
    echo ">>> 警告: 未找到 Xauthority，GUI 可能无法显示"
fi

if command -v xhost >/dev/null 2>&1; then
    xhost +local: >/dev/null 2>&1 || true
fi

echo ">>> 构建并启动 (UID=${USER_UID} DISPLAY=${DISPLAY})"
DOCKER_BUILDKIT=1 docker compose up -d --build

echo ">>> 初始化工作区"
docker exec "$CONTAINER_NAME" bash "$WS_DIR/docker/scripts/init-workspace.sh"

echo ">>> 进入 ${CONTAINER_NAME}:${WS_DIR}"
echo ">>> 日常可直接: docker exec -it -w ${WS_DIR} ${CONTAINER_NAME} bash"
echo ">>> 需要 MuJoCo 源码时，在容器内执行: ./docker/mujoco_setup.sh"
exec docker exec -it -w "$WS_DIR" "$CONTAINER_NAME" bash

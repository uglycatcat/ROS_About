#!/bin/bash
# ─────────────────────────────────────────────────────────
# 一键：构建 → 启动 → 初始化工作区 → 进入 /workspace/ros2_ws
# 用法：./start.sh
# ─────────────────────────────────────────────────────────
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

WS_DIR="/workspace/ros2_ws"
CONTAINER_NAME="petbot_ws"

export USER_UID="$(id -u)"
export USER_GID="$(id -g)"
export DISPLAY="${DISPLAY:-:1}"

# 解析 Xauthority（避免挂载路径不存在导致启动失败）
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

# 允许本地容器连接 X11
if command -v xhost >/dev/null 2>&1; then
    xhost +local: >/dev/null 2>&1 || true
fi

echo ">>> 构建并启动容器 (UID=${USER_UID} GID=${USER_GID} DISPLAY=${DISPLAY})"
DOCKER_BUILDKIT=1 docker compose up -d --build

echo ">>> 初始化工作区"
docker exec "$CONTAINER_NAME" bash "$WS_DIR/docker/scripts/init-workspace.sh"

echo ">>> 进入容器 ${CONTAINER_NAME}:${WS_DIR}"
exec docker exec -it -w "$WS_DIR" "$CONTAINER_NAME" bash

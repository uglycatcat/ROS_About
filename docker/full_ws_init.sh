#!/bin/bash
# ─────────────────────────────────────────────────────────
# full_ws_init.sh — 全流程（全新 Linux：仅 Docker + 本机 VPN/代理）
# 1. 交互输入代理端口
# 2. 拉取基础镜像
# 3. 构建并启动容器、初始化工作区
# 4. 容器内下载最新 MuJoCo release 到 ~/mujoco
# 5. 进入 /workspace/ros2_ws
# ─────────────────────────────────────────────────────────
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

WS_DIR="/workspace/ros2_ws"
CONTAINER_NAME="petbot_ws"
BASE_IMAGE="osrf/ros:humble-desktop"

export USER_UID="$(id -u)"
export USER_GID="$(id -g)"
export DISPLAY="${DISPLAY:-:1}"

# ─── 代理端口（交互）────────────────────────────────────
DEFAULT_PORT="${PROXY_PORT:-7897}"
read -r -p "请输入本机 VPN/代理端口 [${DEFAULT_PORT}]: " INPUT_PORT
PROXY_PORT="${INPUT_PORT:-$DEFAULT_PORT}"
if ! [[ "$PROXY_PORT" =~ ^[0-9]+$ ]] || [ "$PROXY_PORT" -lt 1 ] || [ "$PROXY_PORT" -gt 65535 ]; then
    echo ">>> 无效端口: ${PROXY_PORT}"
    exit 1
fi

DOCKER_GW="$(ip -4 addr show docker0 2>/dev/null | awk '/inet /{print $2}' | cut -d/ -f1)"
DOCKER_GW="${DOCKER_GW:-172.17.0.1}"

HOST_PROXY="http://127.0.0.1:${PROXY_PORT}"
BUILD_PROXY="http://${DOCKER_GW}:${PROXY_PORT}"

export GODEBUG=http2client=0
export ALL_PROXY="$HOST_PROXY"
export all_proxy="$HOST_PROXY"
export HTTP_PROXY="$HOST_PROXY"
export HTTPS_PROXY="$HOST_PROXY"
export http_proxy="$HOST_PROXY"
export https_proxy="$HOST_PROXY"
export NO_PROXY="localhost,127.0.0.1,::1,.aliyun.com,mirrors.aliyun.com,.tuna.tsinghua.edu.cn,mirrors.tuna.tsinghua.edu.cn,pypi.tuna.tsinghua.edu.cn"
export no_proxy="$NO_PROXY"

echo ">>> 宿主机代理: ${HOST_PROXY}"
echo ">>> 构建期代理: ${BUILD_PROXY}  (GODEBUG=http2client=0)"

# ─── X11 ────────────────────────────────────────────────
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

# ─── 1. 拉取基础镜像 ────────────────────────────────────
echo ">>> 拉取基础镜像: ${BASE_IMAGE}"
if ! docker pull "$BASE_IMAGE"; then
    echo ">>> docker pull 失败。若 daemon 未配代理，请在 Docker 服务中配置 HTTP/HTTPS 代理后重试。"
    exit 1
fi

# ─── 2. 构建并启动（构建层走 docker0 代理）──────────────
export HTTP_PROXY="$BUILD_PROXY"
export HTTPS_PROXY="$BUILD_PROXY"
export http_proxy="$BUILD_PROXY"
export https_proxy="$BUILD_PROXY"
export ALL_PROXY="$BUILD_PROXY"
export all_proxy="$BUILD_PROXY"

echo ">>> 构建并启动容器 (UID=${USER_UID} DISPLAY=${DISPLAY})"
DOCKER_BUILDKIT=1 docker compose up -d --build

# 还原宿主机代理（host 网络下容器内 127.0.0.1 即本机代理）
export HTTP_PROXY="$HOST_PROXY"
export HTTPS_PROXY="$HOST_PROXY"
export http_proxy="$HOST_PROXY"
export https_proxy="$HOST_PROXY"
export ALL_PROXY="$HOST_PROXY"
export all_proxy="$HOST_PROXY"

echo ">>> 初始化工作区"
docker exec "$CONTAINER_NAME" bash "$WS_DIR/docker/scripts/init-workspace.sh"

# ─── 3. 容器内安装最新 MuJoCo release ───────────────────
echo ">>> 安装 MuJoCo release → ~/mujoco"
docker exec \
    -e http_proxy="$HOST_PROXY" \
    -e https_proxy="$HOST_PROXY" \
    -e HTTP_PROXY="$HOST_PROXY" \
    -e HTTPS_PROXY="$HOST_PROXY" \
    -u ros \
    "$CONTAINER_NAME" \
    bash "$WS_DIR/docker/mujoco_setup.sh"

echo ">>> 进入 ${CONTAINER_NAME}:${WS_DIR}"
echo ">>> 日常可直接: docker exec -it -w ${WS_DIR} ${CONTAINER_NAME} bash"
exec docker exec -it -w "$WS_DIR" "$CONTAINER_NAME" bash

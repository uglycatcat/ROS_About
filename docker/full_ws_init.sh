#!/bin/bash
# ─────────────────────────────────────────────────────────
# full_ws_init.sh — 全流程（全新 Linux：仅 Docker + 本机 VPN/代理）
# 1. 交互输入代理端口
# 2. 拉取基础镜像
# 3. 构建并启动容器、初始化工作区
# 4. 容器内下载最新 MuJoCo release 到 ~/mujoco
# 5. 进入 /workspace/petbot2_ws/perception_demo_ws
# ─────────────────────────────────────────────────────────
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

WS_DIR="/workspace/petbot2_ws/perception_demo_ws"
CONTAINER_NAME="petbot_ws"
BASE_IMAGE="osrf/ros:humble-desktop"

export USER_UID="$(id -u)"
export USER_GID="$(id -g)"
export DISPLAY="${DISPLAY:-:1}"

# ─── 代理（只用于容器内访问 GitHub）─────────────────────
DEFAULT_PORT="${PROXY_PORT:-7897}"
read -r -p "请输入本机 VPN/代理端口 [${DEFAULT_PORT}]: " INPUT_PORT
PROXY_PORT="${INPUT_PORT:-$DEFAULT_PORT}"
if ! [[ "$PROXY_PORT" =~ ^[0-9]+$ ]] || [ "$PROXY_PORT" -lt 1 ] || [ "$PROXY_PORT" -gt 65535 ]; then
    echo ">>> 无效端口: ${PROXY_PORT}"
    exit 1
fi

# 容器是 host 网络，容器内 127.0.0.1 就是宿主机
HOST_PROXY="http://127.0.0.1:${PROXY_PORT}"

# 构建不走代理：apt/pip 走国内镜像（见 Dockerfile）。
# 只把镜像域名放进 NO_PROXY，避免宿主机已有的代理变量把构建拖慢。
export NO_PROXY="localhost,127.0.0.1,::1,repo.huaweicloud.com,mirrors.huaweicloud.com"
export no_proxy="$NO_PROXY"

echo ">>> 容器内下载代理: ${HOST_PROXY}（构建不走代理）"

# ─── X11 ────────────────────────────────────────────────
# cookie 由 /run/user/<uid> 目录挂载提供（见 docker-compose.yml），此处只放行同 uid 的本地连接。
if command -v xhost >/dev/null 2>&1; then
    xhost +SI:localuser:"$(id -un)" >/dev/null 2>&1 || true
fi

# ─── 1. 拉取基础镜像 ────────────────────────────────────
echo ">>> 拉取基础镜像: ${BASE_IMAGE}"
if ! docker pull "$BASE_IMAGE"; then
    echo ">>> docker pull 失败。若 daemon 未配代理，请在 Docker 服务中配置 HTTP/HTTPS 代理后重试。"
    exit 1
fi

# ─── 2. 构建并启动 ──────────────────────────────────────
echo ">>> 构建并启动容器 (UID=${USER_UID} DISPLAY=${DISPLAY})"
DOCKER_BUILDKIT=1 docker compose up -d --build

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

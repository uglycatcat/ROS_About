#!/bin/bash
# ─────────────────────────────────────────────────────────
# 构建 ROS2 + MuJoCo 开发容器
# 从本目录运行：./build.sh
# ─────────────────────────────────────────────────────────
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
IMAGE_NAME="ros2-mujoco-dev:latest"

echo ">>> 构建镜像: $IMAGE_NAME"
echo ">>> Dockerfile: $SCRIPT_DIR/Dockerfile"
echo ""

cd "$SCRIPT_DIR"

# 使用 BuildKit 加速
DOCKER_BUILDKIT=1 docker build \
    --build-arg USER_UID=$(id -u) \
    --build-arg USER_GID=$(id -g) \
    -t "$IMAGE_NAME" .

echo ""
echo "==========================================="
echo " 构建完成!"
echo " 镜像: $IMAGE_NAME"
echo ""
echo " 启动容器:"
echo "   docker compose up -d"
echo "   docker exec -it ros2-humble bash"
echo "==========================================="

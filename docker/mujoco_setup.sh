#!/bin/bash
# 下载最新 MuJoCo 官方 release 到 ~/mujoco（幂等，含 bin/simulate）。
# 容器内执行: bash /workspace/ros2_ws/docker/mujoco_setup.sh
set -e

MUJOCO_PATH="${MUJOCO_PATH:-$HOME/mujoco}"
API_URL="https://api.github.com/repos/google-deepmind/mujoco/releases/latest"

case "$(uname -m)" in
    x86_64|amd64) ARCH_TAG="linux-x86_64" ;;
    aarch64|arm64) ARCH_TAG="linux-aarch64" ;;
    *) echo ">>> 不支持的架构: $(uname -m)"; exit 1 ;;
esac

if [ -x "$MUJOCO_PATH/bin/simulate" ]; then
    echo ">>> 已存在: $MUJOCO_PATH (bin/simulate)"
    exit 0
fi

echo ">>> 查询最新 release..."
TAG="$(curl -fsSL "$API_URL" | sed -n 's/.*"tag_name": *"\([^"]*\)".*/\1/p' | head -1)"
if [ -z "$TAG" ]; then
    echo ">>> 无法获取最新版本号（检查网络/代理）"
    exit 1
fi

ASSET="mujoco-${TAG}-${ARCH_TAG}.tar.gz"
URL="https://github.com/google-deepmind/mujoco/releases/download/${TAG}/${ASSET}"
echo ">>> 下载 ${URL}"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
curl -fL "$URL" -o "$TMP/$ASSET"

rm -rf "$MUJOCO_PATH"
mkdir -p "$MUJOCO_PATH"
tar -xzf "$TMP/$ASSET" -C "$MUJOCO_PATH" --strip-components=1

MARKER="# petbot-mujoco-bin"
if [ -f "$HOME/.bashrc" ] && ! grep -qF "$MARKER" "$HOME/.bashrc"; then
    {
        echo ""
        echo "$MARKER"
        echo 'export MUJOCO_PATH="${MUJOCO_PATH:-$HOME/mujoco}"'
        echo 'export PATH="$MUJOCO_PATH/bin:$PATH"'
    } >> "$HOME/.bashrc"
fi

echo ">>> 完成: $MUJOCO_PATH ($TAG)"
ls "$MUJOCO_PATH/bin" | head -10

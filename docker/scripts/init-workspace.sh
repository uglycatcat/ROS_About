#!/bin/bash
# ─────────────────────────────────────────────────────────
# 自动初始化挂载工作区 /workspace/ros2_ws（幂等）
# 由 start.sh 在进入交互 shell 前调用，无需手动执行
# ─────────────────────────────────────────────────────────
set -e

WS_DIR="/workspace/ros2_ws"

mkdir -p "$WS_DIR/src"
cd "$WS_DIR"

if [ ! -f "$WS_DIR/install/setup.bash" ]; then
    echo ">>> 首次初始化工作区: $WS_DIR"
    colcon build --symlink-install
else
    echo ">>> 工作区已就绪: $WS_DIR"
fi

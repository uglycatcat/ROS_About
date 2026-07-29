#!/bin/bash
# 初始化 ROS 工作区（幂等），由 container_init.sh 调用
# MuJoCo release 请另行运行 docker/mujoco_setup.sh
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

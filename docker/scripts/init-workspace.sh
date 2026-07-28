#!/bin/bash
# ─────────────────────────────────────────────────────────
# 容器内首次运行：初始化 ROS2 工作区
# 用法：在容器内执行
#   bash ~/host_home/ros2_ws/docker/scripts/init-workspace.sh
# ─────────────────────────────────────────────────────────
set -e

WS_DIR="$HOME/ros2_ws"

echo ">>> 创建 ROS2 工作区: $WS_DIR"
mkdir -p "$WS_DIR/src"
cd "$WS_DIR"

# 安装依赖工具
sudo apt-get update -qq
sudo apt-get install -y -qq python3-colcon-common-extensions 2>/dev/null || true

# 初始化工作区
cd "$WS_DIR"
colcon build --symlink-install

# 写入环境加载
echo "source $WS_DIR/install/setup.bash" >> ~/.bashrc

echo ""
echo "==========================================="
echo " ROS2 工作区已就绪: $WS_DIR"
echo " 下次进入容器自动 source"
echo " 手动编译: cd $WS_DIR && colcon build"
echo "==========================================="

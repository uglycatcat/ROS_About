#!/bin/bash
# ─────────────────────────────────────────────────────────
# ROS2 + MuJoCo 容器入口脚本
# 动态调整容器用户 UID/GID 匹配宿主机
# ─────────────────────────────────────────────────────────
set -e

USERNAME=ros
USER_UID=${USER_UID:-1000}
USER_GID=${USER_GID:-1000}

# 匹配宿主机 UID/GID
if [ "$(id -u $USERNAME)" != "$USER_UID" ]; then
    sudo usermod -u $USER_UID $USERNAME 2>/dev/null || true
    sudo groupmod -g $USER_GID $USERNAME 2>/dev/null || true
fi

# 确保挂载的宿主机 home 目录可写
sudo mkdir -p /home/ros/host_home
sudo chown -R $USER_UID:$USER_GID /home/ros/host_home

exec "$@"

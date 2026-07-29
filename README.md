# PetBot 开发环境（ROS2 Humble + MuJoCo）

基于 `osrf/ros:humble-desktop` 的 Docker 开发容器，含 Gazebo、MoveIt2、MuJoCo、OpenCV 与 NVIDIA GPU 支持。

**前置：** Docker、NVIDIA 驱动 + Container Toolkit。

## 使用

```bash
cd ~/ros2_ws/docker
./start.sh
```

自动完成：构建镜像 → 启动容器 `petbot_ws` → 初始化工作区 → 进入 bash。  
终端落在 `/workspace/ros2_ws`（宿主机 `~/ros2_ws`），ROS2 环境已 source。

| 项目 | 说明 |
|------|------|
| 挂载 | 宿主机 `~/` → `/workspace` |
| 网络 | host（便于 ROS2 发现） |
| 外设 | privileged，可访问串口/摄像头 |
| GUI | 窗口无法显示时，宿主机执行 `xhost +local:` |

首次构建约 15–30 分钟；之后再跑 `./start.sh` 会直接进入已有环境。

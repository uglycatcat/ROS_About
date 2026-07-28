# ROS2 Humble + MuJoCo 开发容器

基于 `osrf/ros:humble-desktop` 构建的一站式机器人开发环境。

## 目录结构

```
ros2_ws/
├── docker/
│   ├── Dockerfile           # 容器镜像定义
│   ├── docker-compose.yml   # 容器运行时配置
│   ├── build.sh             # 一键构建脚本
│   ├── .dockerignore
│   ├── scripts/
│   │   ├── entrypoint.sh    # 容器入口（自动匹配 UID）
│   │   └── init-workspace.sh # 首次运行：初始化 ROS2 工作区
│   └── configs/             # 额外配置文件
└── README.md
```

## 容器中包含

### 系统工具
build-essential, cmake, ninja, gdb, git, vim, tmux, htop, ncdu, curl, ssh

### ROS2 Humble
rviz2, rqt*, urdf/xacro, joint-state-publisher, tf2, control-toolbox, plotjuggler, ros2bag

### 仿真与规划
Ignition Gazebo (Fortress), Gazebo ROS2 bridge, SLAM Toolbox, MoveIt2

### 物理引擎
MuJoCo (`pip install mujoco dm_control`), Pinocchio

### 计算机视觉
vision-opencv, cv-bridge, image-proc, camera-calibration, opencv-python, scikit-image

### Python 科学计算
numpy, scipy, matplotlib, sympy, pandas, scikit-learn, jupyter, rich, tqdm

### 外设与通信
pyserial, python-can, requests, websockets

### NVIDIA GPU
NVIDIA container runtime, 默认 GPU 渲染（`__GLX_VENDOR_LIBRARY_NAME=nvidia`）

## 宿主机前置条件

- Docker （已配代理 `:7897` 和镜像源）
- NVIDIA 驱动 + NVIDIA Container Toolkit（已配）
- Clash Verge 代理（HTTP/1.1，端口 `7897`）

## 构建镜像

```bash
cd ~/ros2_ws/docker
./build.sh
```

构建时自动传入当前用户的 UID/GID，确保容器内文件权限匹配宿主机。

> 首次构建预计 15-30 分钟，取决于网络。

## 初始化容器

### 第一步：启动容器

```bash
cd ~/ros2_ws/docker

# 如果宿主 X11 拒绝连接，先执行：
xhost +local:

# 后台启动
docker compose up -d

# 进入容器
docker exec -it ros2-humble bash
```

### 第二步：初始化 ROS2 工作区

进容器后执行：

```bash
bash ~/host_home/ros2_ws/docker/scripts/init-workspace.sh
```

这会在容器内 `/home/ros/ros2_ws/` 创建一个 ROS2 工作区并首次编译。

或者你更想把 workspace 放在共享目录（宿主机也能访问）：

```bash
mkdir -p ~/host_home/my_robot_ws/src
cd ~/host_home/my_robot_ws
colcon build --symlink-install
```

### 第三步：验证环境

```bash
# ROS2
ros2 run rviz2 rviz2          # 应弹出窗口
ros2 topic list               # 应有 /rosout

# MuJoCo
python3 -c "import mujoco; print(mujoco.__version__)"

# GPU
nvidia-smi

# 外设
ls /dev/ttyUSB* /dev/ttyACM*  # 应看到接的串口设备
```

## 宿主机 ↔ 容器 关系

| 资源 | 映射方式 |
|------|----------|
| **Home 目录** | `~/` → `/home/ros/host_home/`（读写） |
| **X11 显示** | `/tmp/.X11-unix` + `~/.Xauthority` 挂载 |
| **NVIDIA GPU** | `--gpus all` + `runtime: nvidia` |
| **USB/串口** | `/dev/ttyUSB0`、`/dev/ttyACM0` 等直通 |
| **摄像头** | `/dev/video0` 直通 |
| **输入设备** | `/dev/input` 直通 |
| **网络** | host 模式（容器和宿主机网络同栈） |
| **ROS2** | `ROS_DOMAIN_ID=0`，host 网络下可发现外部节点 |

## 常见问题

### rviz2/Gazebo 无法显示
```bash
# 宿主机执行
xhost +local:
```

### 串口设备找不到
检查设备名是否正确，可以临时改为挂载整个 `/dev`：
```yaml
# docker-compose.yml
devices:
  - /dev:/dev
```

### 代理问题
Docker daemon 已配 Clash 代理 + HTTP/1.1 强制。详见 `~/桌面/docker-http2-proxy-issue.md`。

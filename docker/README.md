# ROS 2 / MuJoCo 开发容器

镜像：`ros2-mujoco-dev:latest`；日常容器：`petbot_ws`。用于本地 ROS 2 感知示例与 MuJoCo 演示。GPU 服务器上的 Isaac Lab 训练环境后续独立配置。

## 启动与进入

以下管理命令在宿主机的本地图形终端执行：

```bash
cd ~/ros2_ws/docker
./container_init.sh
```

脚本构建镜像、放行本机 X11 连接、启动容器，并初始化 `perception_demo_ws`。`full_ws_init.sh` 适用于需要交互设置代理并额外下载 MuJoCo 官方 release 的全新环境；`build.sh` 只构建镜像。

容器不依赖任何环境变量即可启动，直接执行 `docker compose up -d` 同样安全。

已有容器正常运行时：

```bash
docker exec -it -w /workspace/ros2_ws petbot_ws bash
```

当前 Compose 将宿主机家目录挂载到 `/workspace`，所以 `~/ros2_ws` 对应 `/workspace/ros2_ws`。项目操作在容器内完成。

## 工作区入口

MuJoCo：

```bash
cd /workspace/ros2_ws/RL_ws/robot_controller_demo
python3 main.py
```

ROS 2：

```bash
cd /workspace/ros2_ws/perception_demo_ws
source /opt/ros/humble/setup.bash
colcon build --base-paths src --symlink-install
source install/setup.bash
```

镜像的 shell 初始化只加载 `perception_demo_ws/install/setup.bash`；RL 工作区由 `COLCON_IGNORE` 排除，不参与 colcon 构建。已创建的旧容器不会自动获得 Dockerfile 修改，应按上述命令显式加载正确工作区。

Python MuJoCo 绑定由镜像提供。`docker/mujoco_setup.sh` 额外下载 MuJoCo 官方 release 到容器内 `~/mujoco`，并把 `$MUJOCO_PATH/bin` 加入 `PATH`（含 `simulate`）。

## X11 图形认证

容器访问宿主机 X 服务器有两条通路：

| 通路 | 实现 |
|---|---|
| cookie | `/run/user/<uid>` 整个目录只读挂进容器为 `/host-run`，容器内 `XAUTHORITY=/host-run/gdm/Xauthority` |
| 同 uid 放行 | `container_init.sh` 执行 `xhost +SI:localuser:<当前用户>` |

挂载**目录**而非单个 `Xauthority` 文件是有意为之：

- 挂载源不存在时，Docker 会静默把它创建成空目录，容器随后启动失败并报 `not a directory: Are you trying to mount a directory onto a file (or vice-versa)?`
- 单文件挂载会把宿主机的 inode 钉死，桌面重新登录后容器读到的仍是旧 cookie

`/run/user/<uid>` 是 tmpfs 目录，只要有图形会话就必然存在，因此容器启动不再依赖外部环境变量，也不会制造空目录。

### GUI 打不开时的排查顺序

```bash
echo $XDG_SESSION_TYPE                # 必须是 x11；wayland 下容器内 GUI 无法工作
nvidia-smi -L                         # 无输出 = NVIDIA 内核模块未加载
ls -l /run/user/1000/gdm/Xauthority   # 存在即正常
```

**掉到 Wayland 的常见根因是 NVIDIA 内核模块与当前内核脱钩**：内核升级后若 `linux-modules-nvidia-595-open-<内核版本>` 未同步安装，GDM 会从 Xorg 退回 Wayland，`/run/user/<uid>/gdm/Xauthority` 就不再生成，容器也拿不到 cookie。确认并修复：

```bash
dpkg -l "linux-modules-nvidia-595-open-$(uname -r)"    # 无输出即未安装
sudo apt-get install -y "linux-modules-nvidia-595-open-$(uname -r)" && sudo reboot
```

## 镜像内容

基础镜像 `osrf/ros:humble-desktop`，另含：

| 类别 | 内容 |
|---|---|
| ROS 2 | MoveIt2、Gazebo Classic、Ignition Fortress、SLAM Toolbox、PlotJuggler、rqt、rosbag2、pinocchio、vision-opencv、camera-calibration |
| 系统工具 | build-essential、gdb、ninja-build、vim、nano、tmux、htop、ncdu、can-utils、usbutils |
| X11 / GPU | x11-apps、mesa-utils、xauth、xterm、xvfb、libglvnd/EGL、NVIDIA 容器运行时 |
| Python | mujoco、dm_control、numpy、scipy、matplotlib、opencv-python-headless、pandas、scikit-learn、jupyter、pyserial、python-can |

> 修改 Dockerfile 时注意层序：apt 与 pip 层不带版本钉住，重跑会拉入最新版本，造成依赖漂移。新增依赖请追加在尾部单独成层，避免让这些层失效。

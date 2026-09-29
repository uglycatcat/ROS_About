# ROS 2 / MuJoCo 开发容器

镜像：`ros2-mujoco-dev:latest`；日常容器：`petbot_ws`。用于本地 ROS 2 感知示例与 MuJoCo 演示。GPU 服务器上的 Isaac Lab 训练环境后续独立配置。

## 启动与进入

以下管理命令在宿主机的本地图形终端执行：

```bash
cd ~/ros2_ws/docker
./container_init.sh
```

脚本构建镜像、配置当前图形会话的 Xauthority、启动容器，并初始化 `perception_demo_ws`。`full_ws_init.sh` 适用于需要交互设置代理并额外下载 MuJoCo 官方 release 的全新环境；`build.sh` 只构建镜像。

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

Python MuJoCo 绑定由镜像提供；可选的 `docker/mujoco_setup.sh` 下载独立 MuJoCo release 到容器用户目录。

## 图形认证挂载失效

重新登录桌面后，旧容器保存的 `/run/user/.../gdm/Xauthority` 等路径可能失效，启动时会出现文件/目录类型不匹配。应在当前桌面终端通过初始化脚本重新解析认证路径；如需重建容器，先保存旧容器可写层里需要保留的内容。

2026-09-29 的目录整理使用同一镜像的无图形临时容器完成。原 `petbot_ws` 的图形认证挂载仍待恢复，不影响本次文件整理和仓库克隆，但运行交互式 MuJoCo 演示前需要处理。

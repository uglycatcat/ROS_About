# PetBot 感知演示工作区

本目录是独立的 ROS 2 Humble / Gazebo Classic 工作区，包含低矮差速底盘上的 ToF 感知、目标跟随和二维建图示例。

## 软件包

| 包 | 作用 |
|---|---|
| [petbot_description](src/petbot_description/README.md) | 模型、场景、Gazebo/RViz 预览和遥控 |
| [petbot_ground_seg](src/petbot_ground_seg/README.md) | 地面分割、背景剔除、前景聚类 |
| [petbot_follow](src/petbot_follow/README.md) | 基于目标簇的跟踪与跟随 |
| [petbot_slam](src/petbot_slam/README.md) | ToF 点云转 LaserScan 和二维建图 |

## 编译与运行

以下命令在 Docker 开发容器内执行：

```bash
cd /workspace/ros2_ws/perception_demo_ws
source /opt/ros/humble/setup.bash
colcon build --base-paths src --symlink-install
source install/setup.bash
```

按需求选择一个入口：

```bash
ros2 launch petbot_description preview.launch.py
ros2 launch petbot_ground_seg ground_seg.launch.py
ros2 launch petbot_follow follow.launch.py
ros2 launch petbot_slam mapping.launch.py
```

每个入口可能包含自己的场景启动逻辑，具体参数见对应包 README。

`build/`、`install/`、`log/` 是本地生成文件，不纳入 Git。迁移前生成的产物可能仍引用旧路径，不能视为新目录下已完成构建；必要时备份后重新生成。

## 资料

- [感知文档索引](docs/README.md)
- [整体工作空间说明](../docs/workspace_layout.md)
- [Docker 环境](../docker/README.md)

该示例的机器人描述独立于 `RL_ws/robot_description`，不会作为当前自恢复训练的模型来源。

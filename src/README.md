# PetBot SLAM Demo

ROS 2 Humble 二轮差速 + Gazebo + slam_toolbox 简单 demo。

## 包

- `petbot_description` — 机器人 URDF
- `petbot_gazebo` — Gazebo 世界与仿真启动
- `petbot_slam` — SLAM 建图 + RViz 目标点跟随

## 编译

```bash
cd /workspace/ros2_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash
```

## 运行

```bash
ros2 launch petbot_slam slam.launch.py
```

会同时打开 Gazebo 和 RViz（第三人称跟随 `base_link`）。

在 RViz 工具栏点 **2D Goal Pose**，在地图上点一下并拖出朝向，机器人会驶向该目标。

也可键盘遥控：

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

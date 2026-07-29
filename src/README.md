# PetBot SLAM Demo

基于 ROS 2 Humble 的二轮差速 SLAM 仿真 demo。工程均在 `src/` 下。

## 包结构

| 包名 | 作用 |
|------|------|
| `petbot_description` | 差速机器人 URDF/xacro、RViz 查看模型 |
| `petbot_gazebo` | Gazebo 房间世界、spawn、仿真启动 |
| `petbot_slam` | slam_toolbox 在线建图 demo |

机器人：差速底盘 + 前万向轮 + 顶部 360° 激光雷达。控制话题：`/cmd_vel`。

## 编译

```bash
cd /workspace/ros2_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select petbot_description petbot_gazebo petbot_slam
source install/setup.bash
```

## 启动方式

### 1. 仅查看机器人模型（RViz）

```bash
ros2 launch petbot_description display.launch.py
```

### 2. Gazebo 仿真 + RViz（无 SLAM）

```bash
ros2 launch petbot_gazebo gazebo.launch.py
```

另开终端键盘遥控：

```bash
source /workspace/ros2_ws/install/setup.bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

### 3. 完整 SLAM Demo（推荐）

```bash
ros2 launch petbot_slam slam.launch.py
```

再开键盘遥控，在房间里转一圈，RViz 中 Fixed Frame 为 `map`，可看到实时建图。

## 主要话题 / TF

- `/cmd_vel` — 速度控制
- `/odom` — 里程计
- `/scan` — 激光扫描
- `/map` — 占据栅格地图
- TF：`map → odom → base_footprint → base_link → laser_link`

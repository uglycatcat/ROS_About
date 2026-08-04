# petbot_description

双轮差速机器人描述 + 预览（无算法）。

- 机器人：差速底盘，仅挂载 **Nebula280MIPI**
- 预览：Gazebo + RViz2，方向键遥控

## 编译

```bash
cd /workspace/ros2_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select petbot_description --symlink-install
source install/setup.bash
```

## 预览

默认使用本包内置的 **TurtleBot3 House** 家庭场景（模型在 `models/`，世界在 `worlds/turtlebot3_house.world`）：

```bash
ros2 launch petbot_description preview.launch.py
```

| `world_name` | 场景 |
|--------------|------|
| `house`（默认） | TurtleBot3 House 室内户型（已 vendored） |
| `house_human` | 同上 + 大人/小孩沿固定矩形轨迹行走 |
| `simple` | 本包简易盒子房 `petbot_world` |

```bash
# 带行人的家庭场景
ros2 launch petbot_description preview.launch.py world_name:=house_human

# 换回简易场景
ros2 launch petbot_description preview.launch.py world_name:=simple

# 或直接指定任意 .world
ros2 launch petbot_description preview.launch.py \
  world:=/path/to/custom.world x:=0.0 y:=0.0
```

行人使用 Gazebo Classic 自带的 **actor**（`walk.dae` 皮肤/动画），不是独立 ROS「人形模型包」：`adult` 比例 1.0，`child` 比例 0.65，脚本轨迹循环行走。世界文件：`worlds/turtlebot3_house_with_human.world`。

### 如何指定行人走哪些坐标

路径写在 `config/human_waypoints.yaml`（世界坐标，单位米）。改完后生成世界再启动：

```bash
cd /workspace/ros2_ws/src/petbot_description
python3 scripts/generate_house_human_world.py
# 若用 install 空间，再 colcon build --packages-select petbot_description
ros2 launch petbot_description preview.launch.py world_name:=house_human
```

在 Gazebo 里量点：开 `world_name:=house` → 俯视 → Insert 一个 Box → 拖到目标位置 → 右侧面板读 Pose 的 **X/Y** → 填进 YAML 的 `waypoints` 列表。House 大致范围约 x∈[-7.5, 7.5]，y∈[-5.3, 5.3]；机器人默认出生约 `(-2.0, -0.5)`。

也可以直接把坐标点发给我，例如：`adult: (-3,-1)->(0,-1)->(0,1)`，我帮你改 YAML。

内置模型目录：`models/turtlebot3_house`、`mailbox`、`cafe_table`、`first_2015_trash_can`、`table_marble`、`ground_plane`、`sun`（源自 ROBOTIS turtlebot3_gazebo / Gazebo 模型库，仅作仿真）。

**注意**：正常应在数秒内出现 `Spawn status: True`。若长时间卡在 `Waiting for service /spawn_entity`，先 `pkill -9 gzserver gzclient` 再重启。

| 按键 | Twist 分量 | 峰值 |
|------|------------|------|
| ↑ / ↓ | `linear.x` ± | **1.2 m/s** |
| ← / → | `angular.z` ± | 1.0 rad/s |
| 空格 | 急停 | |
| F | 手动 ⇄ 跟随 | 需 `teleop_mode_toggle:=true` |
| 空格 | 全零急停 | — |

控制链路：键盘 → `twist_teleop` 发布 `geometry_msgs/Twist` 到 **`/cmd_vel`** → `gazebo_ros_diff_drive` 执行。参数见 `config/teleop.yaml`（可改 `max_linear_x` / `max_angular_z`）。

方向键为 **全局抓取**：鼠标在 Gazebo / RViz 窗口内也可遥控。也可手动发速度：

```bash
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 1.0}, angular: {z: 0.0}}"
```

RViz 中可看机器人模型、里程计、Nebula 点云与彩色图。

## 话题（Nebula280）

命名空间：`/nebula280`。模组仿真含 RGB / IR / sToF / mToF；**后续实验只用 ToF 相关数据**（表中「ToF」列为 ✓ 的行）。

| Topic | 消息类型 | 来源 | ToF | 说明 |
|-------|----------|------|:---:|------|
| `/nebula280/color/image_raw` | `sensor_msgs/Image` | RGB | | 彩色图 |
| `/nebula280/color/camera_info` | `sensor_msgs/CameraInfo` | RGB | | 彩色相机内参 |
| `/nebula280/ir/image_raw` | `sensor_msgs/Image` | IR | | 红外强度图（非测距） |
| `/nebula280/ir/camera_info` | `sensor_msgs/CameraInfo` | IR | | 红外相机内参 |
| `/nebula280/stof/amplitude/image_raw` | `sensor_msgs/Image` | sToF | ✓ | 近距幅度/强度近似 |
| `/nebula280/stof/amplitude/camera_info` | `sensor_msgs/CameraInfo` | sToF | ✓ | sToF 幅度通道内参 |
| `/nebula280/stof/depth/image_raw` | `sensor_msgs/Image`（32FC1） | sToF | ✓ | 近距深度（约 0.1～1.2 m） |
| `/nebula280/stof/depth/camera_info` | `sensor_msgs/CameraInfo` | sToF | ✓ | sToF 深度内参 |
| `/nebula280/stof/points` | `sensor_msgs/PointCloud2` | sToF | ✓ | 近距点云 |
| `/nebula280/mtof/amplitude/image_raw` | `sensor_msgs/Image` | mToF | ✓ | 中远距幅度/强度近似 |
| `/nebula280/mtof/amplitude/camera_info` | `sensor_msgs/CameraInfo` | mToF | ✓ | mToF 幅度通道内参 |
| `/nebula280/mtof/depth/image_raw` | `sensor_msgs/Image`（32FC1） | mToF | ✓ | 中远距深度（约至 8 m） |
| `/nebula280/mtof/depth/camera_info` | `sensor_msgs/CameraInfo` | mToF | ✓ | mToF 深度内参 |
| `/nebula280/mtof/points` | `sensor_msgs/PointCloud2` | mToF | ✓ | 中远距点云 |

预览用派生话题（非传感器原生，由 mToF 深度转成 `mono8` 供 RViz 显示）：

| Topic | 消息类型 | ToF 相关 | 说明 |
|-------|----------|:--------:|------|
| `/nebula280/mtof/depth/image_viz` | `sensor_msgs/Image`（mono8） | ✓（源自 mToF 深度） | 仅可视化 |

底盘 / IMU：

| Topic | 消息类型 | 说明 |
|-------|----------|------|
| `/cmd_vel` | `geometry_msgs/Twist` | 速度指令 |
| `/odom` | `nav_msgs/Odometry` | 里程计 |
| `/imu/data` | `sensor_msgs/Imu` | 六轴 IMU（accel + gyro，100 Hz，`imu_link`） |
| `/joint_states`、`/tf` | — | 关节与坐标变换 |

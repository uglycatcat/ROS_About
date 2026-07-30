# petbot_slam

PetBot **二维平面建图**：只用 Nebula **ToF** 数据（默认 mToF 点云），不用 RGB / IR。

## 依赖

- 工作空间内：`petbot_description`
- 系统包：`ros-humble-slam-toolbox`（已用于本环境）

```bash
sudo apt install ros-humble-slam-toolbox
```

## 编译

```bash
cd /workspace/ros2_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select petbot_description petbot_slam --symlink-install
source install/setup.bash
```

## 启动（场景 + 实时二维地图）

```bash
ros2 launch petbot_slam mapping.launch.py
```

默认 `world_name:=house_human`。其它场景：

```bash
ros2 launch petbot_slam mapping.launch.py world_name:=house
ros2 launch petbot_slam mapping.launch.py world_name:=simple
```

键盘遥控（与 description 相同，峰值 `linear.x=2 m/s`）开着时，开车即可扩展地图。RViz Fixed Frame 为 `map`，显示 `/map` 与 `/scan`。

## 数据流（ToF only）

```
/nebula280/mtof/points   (ToF PointCloud2)
        │
        ▼
tof_points_to_laserscan  →  /scan  (LaserScan, base_link 高度切片)
        │
        ▼
slam_toolbox (async)     →  /map  + map→odom TF
```

**允许使用的 Nebula 输入（ToF）：**

| Topic | 用途 |
|-------|------|
| `/nebula280/mtof/points` | 默认建图输入 |
| `/nebula280/mtof/depth/image_raw` 等 | 可扩展，当前未订 |
| `/nebula280/stof/points` 等 | 可改 `config/tof_to_scan.yaml` 的 `cloud_topic` |

**明确不使用：** `/nebula280/color/*`、`/nebula280/ir/*`。

底盘仍用 `/odom`、`/tf`（非视觉）。

## 参数

| 文件 | 说明 |
|------|------|
| `config/tof_to_scan.yaml` | 点云高度带、距离、视场 → `/scan` |
| `config/mapper_params_online_async.yaml` | slam_toolbox 建图参数 |
| `rviz/mapping.rviz` | 地图 / 扫描 / 机器人 |

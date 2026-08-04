# petbot_ground_seg

PetBot **地面分割 → 背景剔除 → 欧式聚类**：只用 Nebula **ToF** 点云（默认 mToF），不用 RGB / IR。

## 依赖

- 工作空间内：`petbot_description`
- Python：`numpy`（`python3-numpy`）

## 编译

```bash
cd /workspace/ros2_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select petbot_description petbot_ground_seg --symlink-install
source install/setup.bash
```

## 启动

```bash
ros2 launch petbot_ground_seg ground_seg.launch.py
```

默认 `world_name:=house_human`。其它：`world_name:=house` / `simple`。

RViz Fixed Frame=`odom`：灰背景、彩色 `/cluster_points` + `/cluster_markers`。

## 数据流（ToF only）

```
/nebula280/mtof/points
        │
        ▼
ground_segmentation     →  /ground_points
                        →  /obstacle_points
                                │
                                ▼
background_subtraction  →  /background_points
                        →  /foreground_points
                                │
                                ▼
euclidean_clustering    →  /cluster_points      (着色点云)
                        →  /cluster_centroids   (PoseArray)
                        →  /cluster_markers     (球+编号)
```

1. **地面分割**：`base_link` RANSAC 平面  
2. **背景剔除**：`odom` 体素占用 EMA  
3. **聚类**：前景欧式聚类（体素哈希邻域 + BFS）

**明确不使用：** `/nebula280/color/*`、`/nebula280/ir/*`。

## 参数

| 文件 | 说明 |
|------|------|
| `config/ground_seg.yaml` | RANSAC 地面分割 |
| `config/background_sub.yaml` | 体素背景剔除 |
| `config/cluster.yaml` | 邻域半径、簇大小/跨度、最大簇数 |

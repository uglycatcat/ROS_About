# petbot_follow

PetBot **自动跟随**：消费簇质心，KF 跟踪 + **保持距离**追控。默认手动遥控，按 **F** 切换跟随。

`ament_python` 包：节点入口 `target_follower`（`setup.py` console_scripts）。

## 编译

```bash
cd /workspace/ros2_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select petbot_description petbot_ground_seg petbot_follow --symlink-install
source install/setup.bash
```

## 启动

```bash
ros2 launch petbot_follow follow.launch.py
# 或单独跑节点：
# ros2 run petbot_follow target_follower
```


### 操作

| 键 | 作用 |
|----|------|
| ↑↓←→ | **手动模式**下遥控 |
| 空格 | 急停 |
| **F** | `manual` ⇄ `follow`（默认手动） |

跟随模式：锁定前方簇，绕目标保持约 `standoff_distance`（默认 0.20 m 水平距离）——过远前进、过近后退、带宽内只转向，不冲撞。

## 数据流

```
遥控(F) → /control_mode = manual|follow
                │
ToF → … → /cluster_centroids → target_follower
                                    │ follow 才发
                                    ▼
                                 /cmd_vel
```

## 参数

`config/follow.yaml`：`standoff_distance`、`require_follow_mode`、速度上限等。

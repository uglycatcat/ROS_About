# PetBot 开发环境（ROS2 Humble + MuJoCo）

在 `docker/` 下二选一：

| 脚本 | 适用 |
|------|------|
| `./container_init.sh` | 已有镜像 / 国内源可直连。需要 MuJoCo 时容器内再跑 `./docker/mujoco_setup.sh`（下最新 release） |
| `./full_ws_init.sh` | 全新环境 + 本机 VPN；交互代理端口 → 拉镜像 → 起容器 → 装最新 MuJoCo release |

结束后均在容器 `/workspace/ros2_ws`（宿主机 `~/ros2_ws`）。

日常进入：

```bash
docker exec -it -w /workspace/ros2_ws petbot_ws bash
```

挂载：`~/` → `/workspace`。源：阿里云 / 清华。`ROS_DOMAIN_ID=42`。

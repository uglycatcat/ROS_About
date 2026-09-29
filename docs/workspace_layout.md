# 工作空间结构与路径

整理日期：2026-09-29。

## 两个工作区

| 目录 | 职责 | 运行入口 |
|---|---|---|
| `RL_ws` | PetBot 当前模型、MuJoCo 控制演示、自恢复 RL 准备 | `robot_controller_demo/main.py` |
| `perception_demo_ws` | ROS 2 感知、跟随、建图示例 | 各包的 ROS 2 launch |
| `docker` | 本地 ROS 2 / MuJoCo 开发环境 | 宿主机运行容器管理脚本 |
| `docs` | 跨工作区说明 | 本文件与文档索引 |

`RL_ws/robot_description` 是自恢复模型来源；`perception_demo_ws/src/petbot_description` 是感知示例使用的另一套描述，二者用途不同。

当前宿主机目录为 `/home/anna/ros2_ws`，开发容器路径为 `/workspace/ros2_ws`。所有项目操作在容器内进行。

## 旧路径映射

| 旧位置 | 新位置 |
|---|---|
| `robot_controller/` | `RL_ws/robot_controller_demo/` |
| `robot_description/` | `RL_ws/robot_description/` |
| `src/` | `perception_demo_ws/src/` |
| `build/`、`install/`、`log/` | `perception_demo_ws/` 下对应目录 |
| `docs/survey.md`、`docs/what_is_tof.md` | `perception_demo_ws/docs/` |
| `docs/reports/petbot_self_righting_20260924/` | `RL_ws/docs/reports/petbot_self_righting_20260924/` |

历史报告和模型快照里的旧路径表示当时的状态，不是当前启动命令。

## ROS 构建边界

从 `/workspace/ros2_ws/perception_demo_ws` 构建，并指定 `--base-paths src`。`RL_ws/COLCON_IGNORE` 防止从仓库根目录递归发现 RL 与参考项目中的软件包。

目录移动前生成的 `build/`、`install/` 可能含旧绝对路径或失效符号链接；它们不是可移植的构建产物。重新运行 ROS 示例前应检查，必要时先备份旧产物再重新构建。这次整理不删除这些已有文件。

## Git 管理

- 保留：自有源码、模型、文档、容器配置、参考仓库 README 和 `manifest.json`。
- 忽略：ROS 构建产物、Python 缓存、虚拟环境、训练日志和策略权重。
- `RL_ws/reference_project/.gitignore` 忽略该目录的所有子目录，参考仓库保留自己的 Git 历史，不作为本仓库的嵌套源码或 submodule 提交。
- 上游许可证和说明保留在各参考仓库中；克隆不会安装依赖或修改环境。
- 历史个人讨论笔记继续遵循已有忽略规则。
- 如未来需要发布演示权重，应单独决定产物存储位置与版本。

上游仓库的实际来源、分支、提交及浅克隆状态见 [参考清单](../RL_ws/reference_project/manifest.json)。

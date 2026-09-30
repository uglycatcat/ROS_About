# 工作空间结构与路径

整理日期：2026-09-29；2026-09-30 重组为当前结构。

## 顶层结构

```text
petbot2_ws/                     顶层工作空间（自身不受版本管理）
├── README.md                   工作区导航与容器入口
├── perception_demo_ws/         ROS 2 感知演示工作区（独立 Git 仓库，仓库根 = colcon 工作区根）
│   ├── README.md
│   ├── docker/                 本地 ROS 2 / MuJoCo 开发容器配置
│   ├── docs/                   工作空间说明、感知资料、ROS 2 概念整理
│   └── src/                    4 个 ROS 2 软件包
└── RL_ws/                      强化学习工作区（独立 Git 仓库）
    ├── README.md
    ├── docs/                   需求基线、实施说明、历史报告
    ├── reference_project/      上游参考仓库快照（被忽略，不纳入版本管理）
    ├── robot_controller_demo/  MuJoCo 键盘控制演示
    └── robot_description/      MJCF 模型与 STL 网格
```

## 两个工作区

| 目录 | 职责 | 运行入口 | 版本管理 |
|---|---|---|---|
| `perception_demo_ws` | ROS 2 感知、跟随、建图示例 | 各包的 ROS 2 launch | 独立仓库 |
| `RL_ws` | 模型、MuJoCo 控制演示、自恢复 RL 准备 | `robot_controller_demo/main.py` | 独立仓库 |

`RL_ws/robot_description` 是自恢复模型来源；`perception_demo_ws/src/petbot_description` 是感知示例使用的另一套描述，二者用途不同。

宿主机工作区为 `/home/anna/petbot2_ws`，容器内对应 `/workspace/petbot2_ws`。Compose 将宿主机家目录挂载为 `/workspace`，所以 `~/petbot2_ws` 即容器内的 `/workspace/petbot2_ws`。模型运行、仿真、训练和测试在容器内进行；纯文档检查可直接在工作区进行。

## 旧路径映射

2026-09-30 重组之前，两个工作区同属一个仓库，仓库根为 `~/ros2_ws`：

| 旧位置 | 新位置 |
|---|---|
| `~/ros2_ws/`（仓库根） | `~/petbot2_ws/perception_demo_ws/`（仓库随之改名，历史保留） |
| `~/ros2_ws/perception_demo_ws/src/`、`docs/` | `~/petbot2_ws/perception_demo_ws/src/`、`docs/`（上提一层，内容不变） |
| `~/ros2_ws/docker/` | `~/petbot2_ws/perception_demo_ws/docker/` |
| `~/ros2_ws/docs/`（跨工作区文档） | 并入 `~/petbot2_ws/perception_demo_ws/docs/` |
| `~/ros2_ws/README.md` | 拆为 `~/petbot2_ws/README.md` 与 `perception_demo_ws/README.md` |
| `~/ros2_ws/RL_ws/` | `~/petbot2_ws/RL_ws/`（内容不变，转为独立仓库） |
| `~/ros2_ws/perception_demo_ws/build`、`install`、`log` | 已删除；在仓库根重新构建生成 |

更早一次调整（仍在 `ros2_ws` 目录名之下）记录如下，供追溯历史文档中的写法：

| 旧位置 | 当时的新位置 |
|---|---|
| `robot_controller/` | `RL_ws/robot_controller_demo/` |
| `robot_description/` | `RL_ws/robot_description/` |
| `src/` | `perception_demo_ws/src/` |
| `docs/survey.md`、`docs/what_is_tof.md` | `perception_demo_ws/docs/` |
| `docs/reports/petbot_self_righting_20260924/` | `RL_ws/docs/reports/petbot_self_righting_20260924/` |

历史报告、模型快照和参考仓库 README 中的旧路径表示当时的状态，不是当前启动命令。

## ROS 构建边界

从 `perception_demo_ws` 构建，并指定 `--base-paths src`；构建产物 `build/`、`install/`、`log/` 生成在仓库根，已被忽略规则排除。

`RL_ws/COLCON_IGNORE` 保证即使在 `~/petbot2_ws` 下递归调用 colcon，也不会发现 RL 工作区与参考项目中的软件包。

跨机器搬移前生成的构建产物可能含旧绝对路径和失效符号链接，不能视为可移植的构建产物。2026-09-30 重组时已删除 `perception_demo_ws/build`、`install`、`log`；重新运行 ROS 示例前应重新构建。

## Git 管理

- 保留：自有源码、模型、文档、容器配置。
- 忽略：ROS 构建产物、Python 缓存、虚拟环境、训练日志和策略权重。
- `RL_ws` 已从感知仓库移出并改为独立仓库，`perception_demo_ws` 此后只管理感知演示工作区；`RL_ws` 的忽略规则见其自身 `.gitignore`。
- `RL_ws/reference_project/` 下的上游 checkout 保留各自的 Git 历史，由 `RL_ws/reference_project/.gitignore` 排除，不作为嵌套仓库或 submodule 提交。
- 上游许可证和说明保留在各参考仓库中；克隆不会安装依赖或修改环境。
- 如未来需要发布演示权重，应单独决定产物存储位置与版本。

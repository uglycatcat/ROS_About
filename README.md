# PetBot 工作空间

本仓库包含两个独立工作区：`RL_ws` 用于机器人模型、MuJoCo 演示与自恢复强化学习准备；`perception_demo_ws` 用于 ROS 2 感知、跟随与建图示例。

项目命令在 Docker 容器内执行。宿主机负责启动、进入容器和查看文件。当前开发容器用于 ROS 2 / MuJoCo；Isaac Lab 训练将在 GPU 服务器的独立环境中运行。

## 文件结构

```text
ros2_ws/
├── RL_ws/
│   ├── robot_description/       # 当前 MJCF、STL；urdf/ 为预留目录
│   ├── robot_controller_demo/   # 键盘驾驶与车架控制演示
│   ├── reference_project/       # 本地参考仓库、来源及版本清单
│   └── docs/                    # 当前需求与历史自恢复报告
├── perception_demo_ws/
│   ├── src/                     # 四个 ROS 2 包
│   └── docs/                    # ToF 与感知方案资料
├── docker/                      # ROS 2 / MuJoCo 容器配置
└── docs/                        # 工作空间说明与文档索引
```

## 进入环境

在宿主机的图形终端执行：

```bash
docker exec -it -w /workspace/ros2_ws petbot_ws bash
```

容器尚未创建或需要重建时，见 [Docker 环境说明](docker/README.md)。

进入容器后运行现有 MuJoCo 演示：

```bash
cd /workspace/ros2_ws/RL_ws/robot_controller_demo
python3 main.py
```

ROS 2 编译从独立工作区运行：

```bash
cd /workspace/ros2_ws/perception_demo_ws
source /opt/ros/humble/setup.bash
colcon build --base-paths src --symlink-install
source install/setup.bash
```

## 文档入口

- [强化学习工作区](RL_ws/README.md)：环境要求、当前阶段、模型和演示入口。
- [自恢复需求基线](RL_ws/docs/current_scope.md)：服务器训练、5 路位置 + 2 路速度、MuJoCo 验收。
- [参考项目索引](RL_ws/reference_project/README.md)：用途、边界与克隆方式。
- [感知演示工作区](perception_demo_ws/README.md)：ROS 2 包及运行入口。
- [工作空间与忽略规则](docs/workspace_layout.md)。

当前尚未实现 PetBot 的 Isaac Lab 自恢复训练环境，也未产出恢复策略。现有键盘演示保留原控制方式；目标混合动作与仿真内部伺服将在训练环境实现阶段接入。

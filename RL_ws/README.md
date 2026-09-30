# PetBot 自恢复强化学习工作区

在 GPU 服务器用 **Isaac Lab + RSL-RL + PPO** 训练 PetBot 的完整翻倒自恢复策略，再在 **MuJoCo** 中演示。策略输出 **5 个位置目标 + 2 个后轮速度目标**，仿真内部闭环执行，前轮被动。头部、耳朵等模型允许的部位均可触地支撑。

后续训练相关代码、资产转换结果、环境配置、实验记录和文档统一放在本目录。当前处于环境准备阶段，尚无 PetBot 训练任务、恢复策略或 sim2sim 验证结果。

## 导航与目录

- [需求基线](docs/current_scope.md)：已经确认的目标和边界。
- [工程实施说明](docs/engineering_handoff.md)：模型、接口、训练设计、阶段验收与待定项。
- [参考项目](reference_project/README.md)：7 个本地上游仓库、复用入口及版本记录。
- [文档索引](docs/README.md)：当前文档和历史网页报告。

| 路径 | 用途 |
|---|---|
| [robot_description](robot_description/README.md) | 当前 MJCF、STL；`urdf/` 为预留目录 |
| [robot_controller_demo](robot_controller_demo/README.md) | 现有 MuJoCo 键盘演示 |
| `reference_project/` | 已克隆的调研快照，不作为安装目录 |
| `docs/` | 项目背景、设计依据与实施记录 |
| `.tools/`、`.uv/` | 计划使用的 uv 工具、Python 与下载缓存 |
| `.venv/`、`.venv-mujoco/` | 计划使用的独立训练 / MuJoCo 环境 |
| `third_party/` | 后续安装所用的固定版本 Isaac Lab、robot_lab 源码 |
| `artifacts/` | 本地环境记录、转换产物、实验输出 |

环境、依赖与产物目录尚未创建，生成内容已加入忽略规则。`COLCON_IGNORE` 将整个 RL 工作区排除在 ROS 2 包发现之外。后续 PetBot 源码应在本工作区受版本管理的目录中开发，不放入被忽略的上游 checkout。

## 环境现状与版本基线

2026-09-29 在 `ros2-mujoco-dev:latest` 镜像的临时容器内检查：

| 项目 | 检查结果 |
|---|---|
| 平台 | Linux x86_64，glibc 2.35 |
| 系统 Python | `/usr/bin/python3`，3.10.12；没有 `python` 命令 |
| 工具 | Git、curl、cmake、C/C++ 编译器已有；uv、git-lfs 未发现 |
| Python 包 | MuJoCo 3.11.0 已有；torch、isaacsim、isaaclab、rsl_rl 未发现 |
| GPU | 临时整理容器未挂 GPU，未验证服务器 GPU、驱动或 Isaac Sim 启动 |

这不是对训练服务器或旧 `petbot_ws` 可写层的检查。下面列出由使用者准备的环境要求；本次没有安装训练环境。

建议采用以下**复用优先、待服务器环境验证的版本基线**。这些版本是环境准备建议，尚未完成本项目的安装兼容性验证：

| 组件 | 基线 | 依据 |
|---|---|---|
| Python | uv 管理的 3.11.x | Isaac Sim 5.x 使用 Python 3.11 |
| Isaac Sim | 5.1.0 | 与 robot_lab v2.3.2 对齐 |
| Isaac Lab | Git tag `v2.3.2` | 与 robot_lab v2.3.2 对齐 |
| PyTorch / torchvision | 2.7.0+cu128 / 0.22.0+cu128 | Isaac Lab v2.3.2 的 x86_64 安装脚本 |
| RSL-RL | `rsl-rl-lib==3.1.2` | Isaac Lab v2.3.2 的 `rsl_rl` extra 固定版本 |
| robot_lab | Git tag `v2.3.2` | 后续接入框架时使用 |
| MuJoCo | 演示文件声明 3.14.0 | 独立环境使用现有 requirements；镜像 3.11.0 尚未统一 |

版本依据：[robot_lab v2.3.2](https://github.com/fan-ziqi/robot_lab/tree/v2.3.2)、[Isaac Lab 安装脚本](https://github.com/isaac-sim/IsaacLab/blob/v2.3.2/isaaclab.sh)、[RSL-RL 依赖声明](https://github.com/isaac-sim/IsaacLab/blob/v2.3.2/source/isaaclab_rl/setup.py)、[Python 环境说明](https://github.com/isaac-sim/IsaacLab/blob/v2.3.2/docs/source/setup/installation/include/pip_python_virtual_env.rst)。

该组合并非最新版；Isaac Sim 5.1 文档已标记停止支持。这里优先复用现有框架接口。如需要新版本支持，应整体迁移 Sim / Lab / Python / RSL-RL 并重新验证。`WBC-AGILE` 当前快照采用 Lab 3.0.0-beta2、Sim 6.0、Python 3.12、RSL-RL 5.4.1 加补丁，仅参考任务实现，不将其依赖安装进本环境。[Isaac Sim 5.1 状态](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/installation/install_python.html)、[AGILE 上游说明](https://github.com/nvidia-isaac/WBC-AGILE)。

### 需要准备的环境

下列事项由使用者在目标容器中配置；本仓库目前仅记录要求。

| 层次 | 应准备的内容 |
|---|---|
| 服务器 / 宿主机 | NVIDIA 驱动、Docker、NVIDIA Container Toolkit；GPU 符合所选 Isaac Sim 的支持范围 |
| 容器系统 | Linux x86_64，建议 Ubuntu 22.04 / 24.04，glibc ≥ 2.35；GPU 及 Vulkan / 图形驱动可用 |
| 基础工具 | Git、curl、CA 证书、cmake、build-essential；真正使用 LFS 资产时需要 git-lfs |
| Python 管理 | uv 管理独立 Python 3.11 和虚拟环境，提供上游安装脚本需要的 pip |
| 训练依赖 | 上表版本的 Isaac Sim（含运行所需扩展 / 缓存）、Isaac Lab、PyTorch / torchvision、RSL-RL |
| 框架源码 | 后续接入 robot_lab v2.3.2；参考快照与实际开发 / 安装目录分开 |
| MuJoCo 演示 | 独立 uv 环境，依赖以 [演示 requirements](robot_controller_demo/requirements.txt) 为准；图形运行需要显示连接 |
| 日志与导出 | 使用选定 RSL-RL / Isaac Lab 版本配套依赖；策略导出格式确定后再补推理端依赖 |

GPU 型号尚未核对。Isaac Sim 官方列明无 RT Core 的 A100 / H100 不支持此工作流；CUDA 算力强并不自动满足 Sim 要求。官方基础规格列出 32 GB RAM、50 GB SSD、16 GB VRAM，并行训练、扩展缓存和日志需要额外余量。驱动以目标版本的兼容要求为准，环境数量在服务器实测。[Isaac Sim 5.1 系统要求](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/installation/requirements.html)

robot_lab v2.3.2 的上游包还声明了 `cusrl[all]`、`pinocchio` 等依赖，完整安装会包含这些附加项；它们不是 PetBot 使用 PPO 的必要算法组成。接入时单独处理其兼容性，不将七个参考项目的依赖混装。[robot_lab 依赖声明](https://github.com/fan-ziqi/robot_lab/blob/v2.3.2/source/robot_lab/setup.py)

### uv 与 ROS 隔离约定

- 训练 Python 由 uv 管理，虚拟环境放在 `RL_ws/.venv`；MuJoCo 演示建议使用 `RL_ws/.venv-mujoco`。
- 不替换系统 `/usr/bin/python3`，不向 ROS 自带 Python 安装训练包，不使用系统 site-packages。
- 训练终端避免加载 ROS overlay，并清除继承的 `PYTHONPATH` / `PYTHONHOME`；不用 Conda 环境叠加 uv 训练环境。
- uv 工具、管理的 Python 和下载缓存可放在 `RL_ws/.tools` / `RL_ws/.uv`；框架源码放在 `RL_ws/third_party`。这些路径只做规划，当前未创建。
- 后续固定实际 Python 补丁版本和完整依赖版本。当前尚无 PetBot 训练工程自己的 `pyproject.toml`、`uv.lock` 或经过验证的安装锁文件；参考仓库中的同名文件属于各自上游项目。
- 训练项目源码、任务配置、文档受本仓库版本管理；虚拟环境、上游 checkout、缓存和训练输出由忽略规则排除。

参考：[uv 管理 Python](https://docs.astral.sh/uv/guides/install-python/)、[uv 虚拟环境](https://docs.astral.sh/uv/pip/environments/)、[Isaac Lab 对 uv 的说明](https://github.com/isaac-sim/IsaacLab/blob/v2.3.2/docs/source/setup/installation/include/pip_python_virtual_env.rst)。

### 网络与代理

已知本机 Clash 代理端口为 **7897**。使用 host 网络的本机容器可访问 `http://127.0.0.1:7897`，本次参考仓库已通过该地址克隆。桥接容器或远程服务器应使用各自可达的代理地址；远程服务器的 localhost 不会指向本地电脑。不需要将代理写入全局 Git / pip 配置。

### 环境配置完成后的交接信息

记录 GPU / 驱动、容器镜像、uv / Python 版本、Sim / Lab / RSL-RL / PyTorch / MuJoCo 实际版本及上游 commit。依次验证：

1. Python 解释器位于 RL 虚拟环境内，训练包不来自 ROS 路径。
2. PyTorch CUDA 可用，Isaac Sim / Isaac Lab 官方空场景可启动。
3. 官方已有任务能完成短程 PPO 训练、保存和重新加载检查点。
4. 独立 MuJoCo 环境能加载当前模型、运行键盘演示及已有测试。

这些是环境就绪条件，不代表 PetBot 已学会恢复。目标服务器配置和上述验证均尚未执行。

## 当前 MuJoCo 演示

配置好的容器图形终端内，激活相应 MuJoCo 环境后：

```bash
cd /workspace/ros2_ws/RL_ws/robot_controller_demo
python main.py
```

未使用 uv 的现有镜像只有 `python3` 命令，可以用 `python3 main.py` 运行已有演示。按键和模式见 [控制演示 README](robot_controller_demo/README.md)。

当前键盘演示以外部位置 PID 驱动五个力矩执行器，两个后轮为速度伺服；未来策略所需的原生位置伺服尚未接入。演示依赖文件声明 MuJoCo 3.14.0，镜像当前为 3.11.0；本次未更改二者，后续 sim2sim 前需固定并验证实际版本。

已有控制逻辑测试，在选定 Python 环境运行：

```bash
cd /workspace/ros2_ws/RL_ws
python -m unittest discover -s robot_controller_demo -v
```

2026-09-29 检查原开发容器时发现图形认证挂载失效，见 [Docker 说明](../docker/README.md)。当时的目录整理使用同镜像临时容器完成；2026-09-30 的文档检查直接在工作区进行，未使用 Docker，也未复查或调整容器配置。

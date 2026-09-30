# PetBot 自恢复项目

本仓库研究 PetBot 在平地被推倒、滚翻或跌落后，如何通过强化学习策略流畅恢复到模型的默认站立构型，并保持稳定。

**当前主线：GPU 服务器上的 Isaac Lab + RSL-RL + PPO 训练 → 策略导出 → MuJoCo 中闭环演示。** 策略输出 **5 路位置目标 + 2 路后轮速度目标**，由仿真内部伺服闭环执行；前轮保持被动，头部和耳朵等身体部位允许触地支撑。

## 项目位置与边界

当前独立仓库根目录为 `/home/anna/petbot2_ws/RL_ws`。下文相对路径均以该目录为根；迁移仓库时，程序应继续使用文件相对路径，不依赖这一宿主机绝对路径。

本项目已与原 ROS 工作区及容器分离。后续需要运行参考项目时，为对应项目单独创建容器；本仓库不再规定共享镜像、Python 管理方式或统一依赖版本。本次文档整理不创建容器、不安装环境。

## 先读什么

- [AGENTS.md](AGENTS.md)：后续 agent 的快速接手入口、核心决策与工作约定。
- [当前需求基线](docs/current_scope.md)：已确认目标、范围和待定项。
- [工程实施说明](docs/engineering_handoff.md)：动作与观测接口、恢复任务设计、实施顺序和验收。
- [参考项目索引](reference_project/README.md)：7 个上游快照、复用入口和版本记录。
- [文档索引](docs/README.md)：当前文档和历史模型 / 文献报告。

## 目录与现状

| 路径 | 当前内容 |
|---|---|
| [robot_description](robot_description/README.md) | MJCF、10 个 STL 网格；当前物理参数的来源 |
| [robot_controller_demo](robot_controller_demo/README.md) | Linux / macOS 手动键盘演示与已有测试 |
| `reference_project/` | 上游调研源码快照，以及本仓库维护的索引与 manifest |
| `docs/` | 当前需求、工程规划和历史报告 |
| `AGENTS.md` | agent 接手说明 |

当前已有模型和手动演示，**尚无 PetBot 的 Isaac Lab 自恢复任务、训练好的恢复策略、策略导出或 MuJoCo 恢复推理入口**。现有 MJCF 是五个力矩执行器加两个后轮速度执行器，键盘程序对五关节做外部位置 PID；未来策略需要的原生位置伺服转换尚未实现。

当前重点是算法与 sim2sim 验证。实机 PWM 建模、电机辨识和 sim2real 标定不属于本阶段；控制增益、成功阈值、观测维度等尚需后续试验确定。

## 已有演示与测试入口

以下命令从**仓库根目录**执行，运行环境需已具备演示依赖和图形显示。进入专用容器时，以实际挂载的仓库路径为准。

```bash
python3 robot_controller_demo/main.py
python3 -m unittest discover -s robot_controller_demo -v
```

也可进入 `robot_controller_demo/` 后运行 `python main.py`。入口按 `__file__` 定位相邻的模型目录，模型加载不依赖终端当前目录。依赖声明见 [requirements.txt](robot_controller_demo/requirements.txt)，键盘操作和图形限制见 [演示说明](robot_controller_demo/README.md)。

## 后续实施顺序

1. 选定要复用的上游工程并在专用容器中验证其已有任务，记录实际版本。
2. 导入 PetBot 资产，核对关节轴、质量惯量、碰撞和被动前轮；建立 7 维混合动作与内部伺服。
3. 实现物理有效的倒地初始化、观测、奖励、课程、终止条件与固定评估集。
4. 训练 PPO 基线，先验证恢复能力，再改善平滑性和未见状态泛化。
5. 导出同一策略及观测 / 动作契约，在 MuJoCo 中验证恢复、稳定保持和策略接管 / 退出。

阶段完成标准见 [工程实施说明](docs/engineering_handoff.md)。历史网页报告只作为模型和文献资料，不能替代当前需求。

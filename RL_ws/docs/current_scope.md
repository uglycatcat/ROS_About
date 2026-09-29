# PetBot 自恢复：当前需求基线

更新日期：2026-09-29。本文记录已确认的需求与选型，区别于历史调研中的假设。

## 目标与验收

在 GPU 服务器训练完整翻倒自恢复策略，再将同一策略迁移到 MuJoCo 做闭环演示。场景为平地上被推倒、坠落后的侧躺、仰躺、趴倒等状态。所有当前模型允许的身体接触均可利用，头部、耳朵可以支撑地面。

目标是恢复默认站立构型并持续稳定，同时验证未见翻倒状态下的成功率、耗时、平滑性和失败类型。水平位置与航向暂作为自由量，具体成功阈值与测试分布在环境设计时确定。

## 动作与执行器

策略输出 7 维连续动作，经各通道独立缩放和限幅形成：

| 通道 | 控制对象 | 目标 |
|---|---|---|
| 5 路位置 | 头部、左耳、右耳、左轮架、右轮架 | 关节角度，rad |
| 2 路速度 | 左后轮、右后轮 | 角速度，rad/s |

该表为逻辑分组，最终索引顺序需在训练与推理配置中一致定义。前轮无动作通道，保持被动。

Isaac Lab 计划采用位置/速度 action term 与 `ImplicitActuatorCfg`，由仿真内部闭环执行。MuJoCo 对应原生位置/速度伺服。闭环仍具有有限增益、力矩上限和动力学约束；本阶段不做真实 PWM、电机辨识或 sim2real 标定。

**当前实现状态**：现有 MJCF 为五个力矩执行器加两个速度执行器，键盘演示在外部做五路位置 PID。本次整理保留此行为；新的策略接口与原生位置伺服尚未实现。

## 技术路线

- 平台：GPU 服务器上的 Isaac Lab + RSL-RL + PPO。
- 训练工程首选参考：`robot_lab` 的 Go2W 混合动作与执行器配置。
- 自恢复任务参考：`WBC-AGILE` 的倒地状态采集、辅助探索、奖励与课程。
- 方法补充：`getup_gym` 的轮足恢复、`HumanUP` 的动作发现与平滑优化。
- 验证环境：现有 MuJoCo 模型和演示工程。
- 原先的 `tron2_rl_lab`、`b2w-rl`、`Wheel-Legged-Lab` 保留用于模块对照。

框架支持混合动作不等于已经学会 PetBot 的完整翻倒恢复。训练底座复用训练循环、日志、检查点和导出；恢复状态分布、奖励、终止条件及模型接触仍需按 PetBot 设计。

克隆版本是调研快照，不是已经验证兼容的训练依赖锁。[工作区 README](../README.md) 记录建议的兼容版本基线、缺失组件与 uv 隔离要求。环境由使用者配置，本阶段仅整理文档，不安装训练栈。后续训练相关工作统一在 `RL_ws` 中进行，不混用不同上游项目的环境。

## 下一阶段的实现边界

实现要点和阶段验收见 [工程实施说明](engineering_handoff.md)。

1. 机器人资产转换与检查：几何、关节轴、被动前轮、质量惯量和接触。
2. 7 维混合动作与仿真内部伺服。
3. 倒地初始化、观测、恢复奖励、课程、成功判据及评估集。
4. 基线训练与策略导出。
5. MuJoCo 推理适配及 sim2sim 验证。

当前没有新增训练代码、安装训练框架或启动训练。

## 资料

- [本地参考项目与版本](../reference_project/README.md)
- [Isaac Lab 隐式执行器](https://isaac-sim.github.io/IsaacLab/main/source/api/lab/isaaclab.actuators.html#implicit-actuator)
- [MuJoCo 位置伺服](https://mujoco.readthedocs.io/en/stable/XMLreference.html#actuator-position)
- [Learning to Recover: Dynamic Reward Shaping with Wheel-Leg Coordination for Fallen Robots](https://arxiv.org/abs/2506.05516)
- [FTSR / getup_gym](https://github.com/2350575870/getup_gym)
- [HumanUP](https://github.com/RunpeiDong/HumanUP)

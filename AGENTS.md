# PetBot 项目接手说明

## 先读与定位

本文件适用于当前独立仓库。当前宿主机根目录为 `/home/anna/petbot2_ws/RL_ws`；文件引用优先相对仓库根目录，容器中的挂载路径由具体任务确定。

依次阅读 [README.md](README.md)、[docs/current_scope.md](docs/current_scope.md)、[docs/engineering_handoff.md](docs/engineering_handoff.md)，再按需查看 [参考索引](reference_project/README.md)。当前需求文档优先于历史报告和上游示例；用户后续明确要求优先于本文。

## 不应重新误解的核心决策

- 用户有 Isaac Gym + PPO 双轮足训练经验，需要工程路线和复用判断，不需要 RL 入门讲解。
- 训练在独立 GPU 服务器进行，主线是 Isaac Lab + RSL-RL + PPO，最终在 MuJoCo 做 sim2sim 演示。
- 目标是完整翻倒后的自恢复，覆盖侧躺、仰躺、趴倒及推倒 / 跌落后的状态，并持续保持默认站姿。
- 策略动作必须是 **5 个关节位置目标 + 2 个后轮速度目标**；目标由仿真内部闭环执行，不是直接输出力矩。
- 五个位置通道对应 `head`、`left_ear`、`right_ear`、`left_frame`、`right_frame`；两个速度通道对应 `left_rear_wheel`、`right_rear_wheel`。索引顺序将在实现时统一固定。
- 左右前轮被动。头、耳、车架与身体均可触地支撑，不沿用普通运动任务的“非足端触地即失败”逻辑。
- 恢复到默认站立构型；水平位置和 yaw 暂不约束，成功容差和保持时间尚未确定。
- 本阶段聚焦训练思路、环境和仿真演示，不要求 PWM 建模、真实电机辨识或 sim2real 标定。

## 当前实际实现

- `robot_description/mjcf/scene.xml` 是场景入口，包含 `robot_description.xml`；STL 在相邻 `meshes/`。
- 当前 MJCF：五个 motor 力矩执行器 + 两个 velocity 后轮执行器，另有两个被动前轮。
- `robot_controller_demo/` 是手动键盘演示，外部 PID 控制五个位置关节，尚未连接恢复策略。
- 尚无 PetBot 的 Isaac Lab 任务、恢复检查点、策略导出和 MuJoCo 恢复推理实现。
- 模型、摩擦和力矩上限以当前 MJCF 为准；历史快照不自动更新。不要把框架复用建议写成已验证结果。

## 复用与实施

首选参考 `robot_lab/Go2W` 的任务结构和混合动作；`WBC-AGILE/stand_up` 用于倒地采样、奖励与课程；`getup_gym`、`HumanUP` 补充探索辅助与平滑优化思路。其他轮足项目用于局部实现对照。

最小路径为：上游任务验证 → PetBot 资产与伺服 → 倒地任务最小闭环 → PPO 基线 → 泛化与平滑 → MuJoCo 同策略验证。先复用训练 / 日志 / 导出链路，针对 PetBot 替换任务逻辑。辅助力或教师仅在探索瓶颈有证据时引入，最终评估必须关闭辅助。

动作 / 观测映射、归一化、坐标系、频率、滤波和伺服限制必须在训练与 MuJoCo 端一致定义；两个引擎的接触与驱动行为还需实测对照。详细设计和未决参数见工程实施说明。

## 仓库与运行边界

- 本项目已独立，不依赖其他 ROS 工作区、旧容器或它们的 Python。不要恢复旧工作区路径、共享容器假设或旧 Python 管理约定。
- 运行参考项目时为相应项目单独创建容器；文档检查无需启动容器。当前没有统一镜像、容器名称、挂载路径或依赖版本锁。
- `reference_project/*/` 是上游源码快照，默认保持原样；它们不随主仓库提交。`reference_project/README.md` 和 `manifest.json` 是本仓库维护的来源记录。
- PetBot 自有代码与配置保存在本仓库受版本管理的位置，不把唯一改动留在被忽略的参考 checkout 中。
- 用户明确禁止修改 `robot_description/`，包括 MJCF、STL、README 及该目录内其他文件。只允许读取和检查，不修改模型文件或物理参数。
- 使用文件相对路径加载模型，避免硬编码宿主机 / 容器绝对路径。遵循用户已有修改，目录整理不顺带修改物理参数和控制行为。
- 新任务依据用户当前授权推进；不要因本文件重复请求用户确认已定事项。

## 检查与交接

从仓库根目录运行已有测试：`python3 -m unittest discover -s robot_controller_demo -v`。若运行环境缺少 MuJoCo / NumPy，明确区分静态路径检查与完整运行测试，不把未执行的仿真写成已通过。

2026-09-30 迁移检查：文档 / 资源链接、3 处程序模型路径、MJCF include 与 10 个网格引用均有效，13 项 Linux 键盘逻辑测试通过。检查环境缺少 MuJoCo / NumPy，因此未执行完整仿真测试或图形演示；旧位置的测试结果不能替代新运行环境验证。

实现后同步需求 / 工程文档的当前状态，记录实际验证、未解决问题和下一步。当前历史报告位于 `docs/reports/`，只用于模型与文献追溯。

# 本地参考项目

此处保留迁移前已克隆的 7 个公开仓库快照。这里只保存调研源码，不安装各仓库依赖，也不代表这些项目能直接解决 PetBot 的完整翻倒恢复。

## 选用关系

训练框架优先参考 **robot_lab / Go2W**，完整恢复任务重点参考 **WBC-AGILE / stand_up**，方法上补充 **getup_gym、HumanUP**。其余三项用于局部实现对照。项目需求见 [当前需求基线](../docs/current_scope.md)，独立仓库边界见 [项目 README](../README.md)。

| 项目 | 用途 | 复用边界 |
|---|---|---|
| [robot_lab](robot_lab/README.md) | 首选训练框架 | 复用 Isaac Lab 扩展、Go2W 混合 action、RSL-RL 训练 / 导出；恢复任务需要新增。 |
| [WBC-AGILE](WBC-AGILE/README.md) | 恢复任务参考 | 倒地状态数据集、stand_up 奖励与课程；当前 Lab 3 beta API 需适配。 |
| [getup_gym](getup_gym/README.md) | 轮足恢复方法 | FTSR 力辅助探索、教师学生与分阶段奖励；基于 Isaac Gym。 |
| [HumanUP](HumanUP/README.md) | 恢复与平滑方法 | 先发现恢复动作再优化平滑性；G1 / Isaac Gym 代码需按 PetBot 适配。 |
| [tron2_rl_lab](tron2_rl_lab/README.md) | 轮足工程对照 | 轮足配置、动作 / 观测组织及训练与部署工程；不是 PetBot 恢复成品。 |
| [b2w-rl](b2w-rl/README.md) | 混合 action 示例 | B2-W 关节位置 + 轮速示例，结构较简洁；上游基线为较旧的 Lab 1.2 / Sim 4.2。 |
| [Wheel-Legged-Lab](Wheel-Legged-Lab/README.md) | 阶段训练对照 | 恢复与移动切换、评估记录；使用 VMC，Recovery 明确不覆盖完全侧躺起立。 |

## 建议优先阅读的源码

- [robot_lab：Go2W 配置](robot_lab/source/robot_lab/robot_lab/tasks/manager_based/locomotion/velocity/config/wheeled/unitree_go2w/rough_env_cfg.py)：位置 / 速度 action 分组与关节名映射。
- [WBC-AGILE：T1 stand_up](WBC-AGILE/agile/rl_env/tasks/stand_up/t1/stand_up_env_cfg.py) 与 [倒地数据预采集](WBC-AGILE/agile/rl_env/tasks/stand_up/t1/pre_learn.py)：重置、奖励、课程及倒地库。
- [getup_gym：轮足配置](getup_gym/getup_gym/envs/bipedal_wheeled/config.py) 与 [环境](getup_gym/getup_gym/envs/bipedal_wheeled/env.py)：轮足恢复实现。
- [HumanUP：训练说明](HumanUP/simulation/README.md) 与 [环境目录](HumanUP/simulation/legged_gym/legged_gym/envs/)：动作发现及后续 refinement。
- [TRON2：轮足配置](tron2_rl_lab/exts/bipedal_locomotion/bipedal_locomotion/tasks/locomotion/cfg/WF_TRON2A/limx_base_env_cfg.py)：轮足环境组织。
- [b2w-rl：混合动作环境](b2w-rl/b2w_hybrid_env.py)：位置与轮速协同的简化示例。
- [Wheel-Legged-Lab：阶段训练](Wheel-Legged-Lab/STAGED_TRAINING.md)：课程与评估组织。其 VMC action 与本项目的五位置 + 两速度并不等价。

上游 README 中的效果和训练指标属于对应机器人与任务，不作为 PetBot 的性能预期。完整恢复不能直接复用普通 locomotion 的触地终止或速度跟踪奖励。

## 克隆快照

日期：2026-09-29。完整来源、分支和 commit 保存在 [manifest.json](manifest.json)。上游分支会变化，以这里的 commit 为本次调研依据。

| 项目 | 上游 | 分支 | 本地 commit |
|---|---|---|---|
| robot_lab | [robot_lab](https://github.com/fan-ziqi/robot_lab) | `main` | `500399ed75f510aeaff28705a8ce736c514dbec3` |
| WBC-AGILE | [WBC-AGILE](https://github.com/nvidia-isaac/WBC-AGILE) | `main` | `6830cf995714e81c91ce63247e8e016d36e28f14` |
| getup_gym | [getup_gym](https://github.com/2350575870/getup_gym) | `master` | `238d2962a0fee8e3da4da914cadcea2be00ce402` |
| HumanUP | [HumanUP](https://github.com/RunpeiDong/HumanUP) | `master` | `7516e0f27e6f4d1e7365cf64ea577a78247bd8cb` |
| tron2_rl_lab | [tron2_rl_lab](https://github.com/limxdynamics/tron2_rl_lab) | `main` | `db021b4016648a6ddc97fb0acbe5df882cd53fc5` |
| b2w-rl | [b2w-rl](https://github.com/LauraMQuiros/b2w-rl) | `master` | `ad82b971bf69a84170f027035c1e2e3bf97e4ef9` |
| Wheel-Legged-Lab | [Wheel-Legged-Lab](https://github.com/zyicome/Wheel-Legged-Lab) | `main` | `e61bfe1fb05aac638ba33e41f91b4eddf3c3c1e7` |

## 本地使用与版本管理

- 当前使用浅克隆（depth 1、single branch）；未初始化 submodule，并跳过 Git LFS 对象下载。源码可阅读，部分大型资产或权重可能仍为 LFS 指针，不保证每个上游项目可直接启动。
- 子目录保留各自 `.git`，由本目录 [.gitignore](.gitignore) 排除，避免作为主仓库嵌套仓库提交。主仓库只管理本索引、manifest 和忽略规则。
- 同步主仓库到服务器不会带上这些 checkout。可按 manifest 的 URL、分支及 commit 重新克隆；如需严格恢复旧快照，应 fetch 对应 commit 后 checkout，并用 `git rev-parse HEAD` 对照。
- 本次未使用 submodule 管理参考项目。以后如要运行某个上游项目，先按其文档检查 LFS / submodule / license 及独立环境要求。
- 实际运行参考项目时分别创建专用容器，并记录所运行的 commit 和实际依赖。调研快照不是通用兼容基线；不再沿用旧共享容器或此前拟定的固定版本组合。
- 不在这些被忽略的参考目录中保存唯一的 PetBot 改动；需要迁移的代码和修改说明放进 RL_ws 受版本管理的工程，并保留来源及许可证。

Isaac Lab 与 RSL-RL 属于待配置的训练依赖，本次未为 PetBot 单独安装它们。部分参考项目自带旧版 RSL-RL 源码，不代表当前项目已配置该依赖；具体运行配置在后续对应参考项目的专用容器任务中确定。

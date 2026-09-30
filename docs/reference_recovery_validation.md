# 参考项目 Kitjesen/recovery 运行验证记录

记录 [Kitjesen/recovery](https://github.com/Kitjesen/recovery) 的克隆、容器内跑通与训练实测。**上游源码零改动**，本机不承担 PetBot 迁移。

## 结论摘要

| 问题 | 结论 | 依据 |
|---|---|---|
| 代码跑通了吗 | **是** | 容器内 `pip install -e .` 成功，`EXIT=0`，14 个奖励项全部产出，`model_0.pt` … `model_399.pt` 落盘，TensorBoard events 正常 |
| 能让机器人站起来吗 | **未证实** | 400 iteration 的 `recovery_success_rate` 全程 `0.0000`。这是训练量不足，不是代码缺陷，见[训练规模对照](#训练规模对照) |
| 能直接看到效果吗 | **本机不能** | 本机显卡低于 Isaac Sim 5.1 标称要求，开相机渲染必崩；该仓库无 MuJoCo 通路，所以在本机只能靠指标曲线判断 |

## 项目信息

| 项 | 值 |
|---|---|
| 上游 | https://github.com/Kitjesen/recovery |
| 本地路径 | `reference_project/recovery`（浅克隆，depth 1） |
| 本地 commit | `5b57477598963695be27474c0ba941a1ba4afd38`（2026-04-17，*refactor(layout): split mdp and config by method name*） |
| 克隆日期 | 2026-09-30 |
| 许可证 | Apache-2.0（Thunder URDF / 网格由 Qiongpei Technology 授权随包分发） |
| 论文 | Deng et al., *Learning to Recover: Dynamic Reward Shaping with Wheel-Leg Coordination for Fallen Robots*，[arXiv:2506.05516](https://arxiv.org/abs/2506.05516) |
| 机器人 | Thunder（12 腿关节 + 4 轮关节的轮足四足），URDF + STL 随仓库自带 |
| 任务注册名 | `RobotLab-Isaac-Velocity-Recovery-Thunder-v0`（method1_deng）、`RobotLab-Isaac-Velocity-Recovery-Thunder-Getup-v0`（method2_getup） |
| 依赖 | 仅 Isaac Lab + RSL-RL；`env_cfg` 直接继承 `isaaclab.envs.ManagerBasedRLEnvCfg`，**不依赖 robot_lab** |

选它的理由：在已调研的候选中，它是唯一同时满足「轮足 + Isaac Lab + 倒地起身 + SO(3) 全姿态随机 + 零参考动作」四项的项目。`reset_with_freefall` 用 SO(3) 均匀随机四元数 + 自由落体生成初始姿态，不需要预录的姿态池或标准恢复动作。

## 运行环境

| 项 | 值 |
|---|---|
| 容器 | `robot-lab-232`（复用 robot_lab 的容器，未新建） |
| 镜像 | `robot-lab-232:latest` ← `nvcr.m.daocloud.io/nvidia/isaac-lab:2.3.2@sha256:388dbc80…` |
| 组件版本 | Isaac Lab 2.3.2 / Isaac Sim 5.1 / Python 3.11 / `rsl-rl-lib` 3.1.2 / `isaaclab 0.54.2` |
| 宿主 | Ubuntu 24.04，i7-11700F 16 核，62 GB RAM，RTX 2080 Ti 11 GB（Turing） |
| 关键挂载 | `reference_project/recovery` → `/workspace/recovery`；`/tmp/rl232/robot_lab-2.3.2` → `/workspace/isaaclab_extension_template`；`reference_project/rl_sar` → `/workspace/rl_sar` |
| 运行时 | `--gpus all --network host`（host 网络是访问本机代理 127.0.0.1:7897 的前提） |

镜像由 robot_lab 仓库的 `docker/Dockerfile` 构建（基础镜像 + `pip install -e source/robot_lab`），构建上下文 `/tmp/rl232/robot_lab-2.3.2`。**构建必须 `--network host`**：bridge 网络下容器内访问不到 `127.0.0.1:7897`，pip 会静默挂起。

## 兼容性缺口：`dump_pickle`

容器内 `pip install -e .` 成功，但首次运行即报：

```
ImportError: cannot import name 'dump_pickle' from 'isaaclab.utils.io'
```

`scripts/train.py:79` 写作 `from isaaclab.utils.io import dump_pickle, dump_yaml`。**Isaac Lab 2.3.2 的 `isaaclab.utils.io` 只导出 `dump_yaml`**，`dump_pickle` 是更新版本的 API（同版本的 robot_lab `train.py` 只导入 `dump_yaml`）。上游 README 声明的 `isaaclab >= 5.0` 无法对应到具体版本，本仓库是在比 2.3.2 更新的 Isaac Lab 上开发的。

**处置方式：不修改上游源码，用仓库外的导入钩子补齐缺失函数。**

- 宿主 `/tmp/lab232_compat.py`，容器内 `/workspace/lab232_compat.py`
- 原理：包装 `builtins.__import__`，在 `from isaaclab.utils.io import dump_pickle, …` 触发导入时把缺失属性挂到模块上，随后的 `IMPORT_FROM` 即可成功
- 必须是**懒注入**：不能在 shim 加载时就 `import isaaclab` —— `pxr` 只在 Isaac Sim 应用启动后才可用，提前导入会 `ModuleNotFoundError: No module named 'pxr'`
- 在已含 `dump_pickle` 的 Isaac Lab 版本上自动退化为 no-op

`/tmp` 会被清理，shim 内容随本文档保存：

```python
"""Compatibility shim: inject `dump_pickle` for runs on Isaac Lab 2.3.2."""
import builtins, pickle, runpy, sys

def _dump_pickle(filename, data):
    with open(filename, "wb") as f:
        pickle.dump(data, f)

_orig_import = builtins.__import__

def _patched_import(name, globals=None, locals=None, fromlist=(), level=0):
    module = _orig_import(name, globals, locals, fromlist, level)
    if fromlist and "dump_pickle" in fromlist and not hasattr(module, "dump_pickle"):
        module.dump_pickle = _dump_pickle
        print(f"[shim] injected dump_pickle into {name} (Isaac Lab 2.3.2 fallback)")
    return module

builtins.__import__ = _patched_import

script = sys.argv[1]
sys.argv = sys.argv[1:]
runpy.run_path(script, run_name="__main__")
```

## 复现步骤

```bash
# 1. 安装（容器内，只需一次）
docker exec robot-lab-232 bash -lic 'cd /workspace/recovery && pip install -e .'
#    → 安装 thunder_recovery-0.1.0，并在 import 时注册两个 gym task

# 2. 冒烟测试（64 envs × 3 iter，约 2 分钟）
docker cp /tmp/lab232_compat.py robot-lab-232:/workspace/lab232_compat.py
docker exec robot-lab-232 bash -lic 'export ACCEPT_EULA=Y PYTHONDONTWRITEBYTECODE=1; \
  cd /workspace/recovery && python /workspace/lab232_compat.py scripts/train.py \
  --task RobotLab-Isaac-Velocity-Recovery-Thunder-v0 --num_envs 64 --headless \
  --max_iterations 3 --seed 42'

# 3. 训练（追加环境数 / iteration 数即可）
docker exec robot-lab-232 bash -lic 'export ACCEPT_EULA=Y PYTHONDONTWRITEBYTECODE=1; \
  cd /workspace/recovery && python /workspace/lab232_compat.py scripts/train.py \
  --task RobotLab-Isaac-Velocity-Recovery-Thunder-v0 --num_envs 512 --headless \
  --max_iterations 400 --seed 42'
```

日志落在 `reference_project/recovery/logs/rsl_rl/thunder_recovery/<时间戳>/`，被仓库 `.gitignore` 覆盖，`git status` 保持干净。上游 `scripts/train.py` 不经 shim 直接跑会失败，必须走 `/workspace/lab232_compat.py` 入口。

## 实测结果

### 冒烟测试（64 envs × 3 iter）

`EXIT=0`，输出与上游 README 的预告逐项吻合：14 行 `Episode_Reward/recovery_*`（13 项奖励 + 1 项副作用计数器 `recovery_step_counter`）、`recovery_support_state` 在 iteration 2 即非零（部分环境重置后已四脚触地）。Mean reward −0.02 → 0.15，episode length 27.5 → 68.0。

### 训练（512 envs × 400 iter，seed 42）

| 指标 | iteration 0 | iteration 400 |
|---|---|---|
| Mean reward | −0.02 | **65.90** |
| `recovery_base_height` | 0.0017 | **7.44** |
| `recovery_base_orientation` | 0.0003 | **3.88** |
| `recovery_support_state` | 0.0000 | **0.48** |
| `recovery_stand_joint_pos` | 0.0000 | **0.35** |
| `recovery_wheel_leg_coord` | — | **0.15** |
| `recovery_success_rate` | 0.0000 | **0.0000** |

- 耗时约 12 分钟，吞吐 14,000 steps/s，显存 3.1 GB / 11 GB
- 奖励项（`base_height`、`orientation`、`support_state`）单调上升、`success_rate` 不动，符合论文的 ED/CW 动态塑形设计：**先塑形、后收敛**
- `recovery_success_rate` 的判定是四项同时满足（`base_height > 0.30 m`、`|q − q_default| < 0.5 rad`、`max|q̇| < 0.1 rad/s`、`|g_b − [0,0,−1]| < 0.1`），且只取 episode 最后 1 秒。它是**严格指标**，塑形项涨到这个程度时它仍为 0 是预期行为

### 吞吐探测（2048 envs，被中断）

为定配置做的一次 2048 envs 探测，跑到 iteration 6 后被中止，只留下吞吐数据、**不是完整训练结果**：

| envs | steps/s | 每 iteration | 显存 |
|---|---|---|---|
| 512 | ~14,000 | ~1.75 s | 3.1 GB |
| 2048 | **~41,000** | ~2.4 s（collection 2.26 s + learning 0.11 s） | 4.0 GB |

吞吐随 envs 增长呈次线性（4 倍 envs 约 2.9 倍吞吐），符合 PhysX 侧先饱和的特征。

## 训练规模对照

PPO 配置：`num_steps_per_env = 48`、`max_iterations = 10000`、`num_learning_epochs = 5`、`num_mini_batches = 4`、`learning_rate = 1e-3`。`num_steps_per_env` 必须与 `mdp/_utils.py` 的 `RECOVERY_STEPS_PER_ITER = 48` 一致，否则 CW 衰减时序错位。

| | envs × 48 | × iterations | 总样本 | 相对论文 |
|---|---|---|---|---|
| 论文完整训练 | 4096 × 48 | 10000 | 19.7 亿 | 100% |
| 论文 `success_rate` 开始爬升（iter 6k–8k） | 4096 × 48 | 6000 | 11.8 亿 | 60% |
| **本次实测** | 512 × 48 | 400 | **0.098 亿** | **0.8%** |

本次跑到论文所称 `success_rate` 爬升起点的 **0.8%**，所以 `success_rate = 0` 与「代码是否跑通」无关，只反映训练量。

按实测吞吐外推本机跑论文原配置（4096 envs × 10000 iter）耗时：2048 envs 配置约 **6.7 小时**跑完 10000 iter；4096 envs 配置若吞吐继续按次线性外推则约 **8–10 小时**（4096 的显存占用与吞吐均**未实测**，仅按 2048 数据外推）。

`ED(t)` 按 episode 内步数计算（`t/T`，T 为 episode 长度），与总 iteration 数无关，因此改 `--max_iterations` 不会破坏塑形时序；`CW(i)` 在 iteration 100 附近已衰减到 0.01，行为惩罚项早期即退场。

## 本机限制

- **无法录制演示视频**：录制需 `--enable_cameras`，本机在该路径上稳定段错误，崩溃点在 `omni.kit.widget.viewport/_impl/texture.py:314` → `librtx.scenedb.plugin.so`。headless 训练不受影响。
- **无 MuJoCo 退路**：该仓库只提供 Isaac Lab 训练与 `scripts/play.py`，没有 MuJoCo / sim2sim 通路，因此本机无法像 rl_sar 那样绕开 RTX 看画面。要看策略实际动作需要换显卡达标的机器。
- 本机 GPU 低于 Isaac Sim 5.1 的最低标称要求（RTX 4080 / 16 GB），headless 训练可用属超出标称范围。

## 待办与线索

- **未验证的捷径**：上游 README 提到作者另有公开部署栈 [`boyuandeng/Recovery_go2w`](https://github.com/boyuandeng/Recovery_go2w)，其中含 `model_7999.pt` 权重，且本仓库的网络结构（Actor MLP [128,128,128] 78→16、Critic [128,128,128] ≈262→1、`init_noise_std=1.0`）就是按该检查点的 `state_dict` 对齐的。**若该权重可直接加载，用 `scripts/play.py` 加载即可绕开 10000 iteration 的训练**，是验证「能否站起」最快的路径 —— 尚未拉取核实，权重可用性、观测/动作维度一致性与许可证均未确认。
- 长跑尚未执行。按上表外推，跑论文原配置约需 8–10 小时，且本机看不到画面，只能以 TensorBoard 曲线判定。
- method2_getup（`...-Thunder-Getup-v0`，60/40 概率落体 + 地面放置）本次未运行。

## 相关文档

- [参考项目索引](../reference_project/README.md)：其余 8 个参考项目的用途与快照版本
- [当前需求基线](current_scope.md)、[工程实施说明](engineering_handoff.md)：PetBot 恢复任务的需求与设计

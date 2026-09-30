# PetBot 文档索引

当前独立仓库：`/home/anna/petbot2_ws/RL_ws`。本目录记录需求和工程规划，现阶段不提供共享环境或 Python 管理方案；后续运行参考项目时分别创建专用容器。

## 当前有效文档

1. [项目入口](../README.md)：目录、现状与已有演示。
2. [Agent 接手说明](../AGENTS.md)：快速理解已定决策和工作边界。
3. [当前需求基线](current_scope.md)：目标、动作接口、范围与待定项。
4. [工程实施说明](engineering_handoff.md)：训练设计、sim2sim 契约、阶段验收。
5. [参考项目索引](../reference_project/README.md)：上游用途、源码入口和快照版本。
6. [recovery 运行验证记录](reference_recovery_validation.md)：轮足倒地起身参考项目的克隆、容器内跑通与训练实测，含本机硬件限制。
7. [机器人模型](../robot_description/README.md) 与 [键盘演示](../robot_controller_demo/README.md)。

## 历史资料

[2026-09-24 网页报告](reports/petbot_self_righting_20260924/index.html) 保留模型观察、配图与论文资料；[模型快照](reports/petbot_self_righting_20260924/model_snapshot.json) 记录当时的物理参数和文件哈希。

旧报告里的本地训练算力约束、MuJoCo 训练主线、直接力矩 action 和当前阶段实机辨识建议均已被后续讨论取代。旧容器和 Python 环境配置也已撤销。阅读时以当前需求基线为准；配图不是已训练策略的演示，快照不会随当前模型自动更新。

## 维护约定

`current_scope.md` 记录已确认需求；`engineering_handoff.md` 记录候选实现与待定参数；实际完成状态同时更新项目 README 和 AGENTS。文档链接使用仓库内相对路径，运行命令默认从仓库根目录执行。

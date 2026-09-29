# 自恢复文档

- [当前需求基线](current_scope.md)：后续设计与实现的依据。
- [环境要求](../README.md)：建议版本、缺失组件、uv 与 ROS 隔离约定；由使用者配置。
- [工程实施说明](engineering_handoff.md)：项目背景、动作契约、任务设计、实施阶段与验收。
- [参考项目索引](../reference_project/README.md)：工程用途、版本与使用边界。
- [机器人模型说明](../robot_description/README.md)。
- [2026-09-24 自恢复网页报告](reports/petbot_self_righting_20260924/index.html)：历史调研，保留论文、模型快照与配图。

## 历史报告的适用边界

旧报告中的本地训练算力约束、以 MuJoCo 训练为主线、直接力矩 action、当前阶段实机辨识等建议已被 2026-09-29 的需求澄清取代。它不代表当前实施方案。

报告配图是模型观察图，不是已训练的自恢复演示。`model_snapshot.json` 对应当时的模型，不会随当前 MJCF 自动更新。

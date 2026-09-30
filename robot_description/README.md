# PetBot 机器人模型

本目录保存自恢复任务使用的当前机器人模型。

| 路径 | 用途 |
|---|---|
| [mjcf/scene.xml](mjcf/scene.xml) | MuJoCo 场景入口，包含地面、接触设置与机器人 |
| [mjcf/robot_description.xml](mjcf/robot_description.xml) | 本体、质量惯量、关节、执行器与传感器 |
| `meshes/` | STL 网格，缩放和坐标变换由 MJCF 指定 |
| `urdf/` | 当前为空的预留目录；尚无可用 URDF 资产 |

控制演示通过相对路径加载 `mjcf/scene.xml`，目录移动后仍与 `robot_controller_demo/` 相邻。

## 当前控制配置

- 头部、双耳、左右轮架：5 个受限旋转关节，当前 MJCF 使用力矩执行器。
- 左右后轮：2 个速度执行器。
- 左右前轮：被动旋转关节。
- 现有键盘演示使用外部位置 PID 驱动五个力矩执行器。
- 摩擦与接触参数以 MJCF 文件为准；控制演示不覆盖摩擦。

后续 RL 接口已确定为 **5 路位置目标 + 2 路轮速目标**，并使用仿真内部伺服；该转换尚未实施。见 [当前需求基线](../docs/current_scope.md)。

本模型与 `perception_demo_ws/src/petbot_description` 中用于 ToF/ROS 演示的机器人描述用途不同。修改资产时以当前文件为准，历史报告中的参数和快照仅作追溯。

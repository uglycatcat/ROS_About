# PetBot 终端驾驶控制演示

这是现有手动控制演示，尚未接入自恢复策略。未来 RL 的 5 路位置 + 2 路速度接口见 [需求基线](../docs/current_scope.md)。

支持 Linux Docker / X11 和 macOS。程序加载
`../robot_description/mjcf/scene.xml`，初始隐藏 MuJoCo 左右面板。

## Linux 容器运行

在宿主机的本地图形终端中进入已经运行的开发容器：

```bash
docker exec -it -w /workspace/ros2_ws/RL_ws/robot_controller_demo petbot_ws bash
python main.py
```

也可以在容器的 `/workspace/ros2_ws` 下执行：

```bash
cd RL_ws/robot_controller_demo
python main.py
```

容器需要连接启动终端所在的同一个 X11 桌面。项目 Compose 已挂载
`/tmp/.X11-unix`、Xauthority，并传入 `DISPLAY`、`XAUTHORITY`。
镜像安装 `python-is-python3` 提供 `python` 命令。
旧容器如果没有该命令，也可直接运行 `python3 main.py`。

窗口出现后，点击**启动程序的终端输入区**并按一次控制键，绑定控制终端。
之后支持方向键组合、即时松键检测和焦点丢失停车；点击 MuJoCo 窗口时可操作
视角，机器人会减速停车。返回原终端后继续驾驶。

Linux 使用系统 `libX11` 查询物理按键状态，不依赖终端自动重复，不需要
`sudo`、原始 `/dev/input` 读取权限或额外 Python 键盘库。终端标签页/分屏
之间的焦点识别需要终端支持 xterm focus reporting（例如 GNOME Terminal、
xterm）；不同 X11 窗口的焦点也会独立检查。

此入口面向本地 X11 终端。Wayland 桌面需通过 XWayland 启动 X11 终端
（例如 `GDK_BACKEND=x11 gnome-terminal`），并连接对应的 `DISPLAY`。
不支持无图形桌面的 SSH、任意 IDE 终端或不转发焦点报告的复用器；
终端不支持焦点报告时，无法区分同一窗口内的标签页/分屏。

## macOS 运行

保留原有 macOS 演示入口。在“终端.app”或 iTerm2 中，先激活已配置的独立 MuJoCo Python 环境，再运行：

```bash
cd <项目根目录>/RL_ws/robot_controller_demo
python main.py
```

macOS 需要 `mjpython` 承载图形主线程；入口会自动切换到当前 Python 环境的
`mjpython`，Linux 不进行此切换。macOS 保留原有的终端输入区域焦点识别。

精确按键检测需要“输入监控”，区分终端窗口/输入区域需要“辅助功能”。缺少
权限时程序会触发系统提示并退出。进入“系统设置 → 隐私与安全性”，允许
系统提示的终端或 `MuJoCo (mjpython)`，退出并重新打开终端后再运行。
macOS 支持终端.app 和 iTerm2，不支持 IDE 集成终端或 SSH。

## 按键与行为

- 上 / 下：前进 / 后退。
- 左 / 右：左转 / 右转，可与前后方向组合。
- 松开方向键：平滑减速；相反方向同时按住时，该方向输入抵消。
- 空格：减速停车，同时暂停车架角度调整。
- `c`：在普通模式和控腿模式之间切换，按住不会连续切换。
- `Esc` 或 `Ctrl+C`：退出，并恢复终端输入设置。`q` 不再用于退出。

启动时为普通模式：头、双耳和左右车架保持零位，Q/W/E/R 不调整角度。
控腿模式保留全部方向键驾驶功能，同时控制左右车架相对机身的两个旋转关节：

| 按键 | 作用 |
|------|------|
| Q / W | 减小 / 增大左车架 `left_frame` 的目标角度 |
| E / R | 减小 / 增大右车架 `right_frame` 的目标角度 |

按住按键时，目标角度以 `0.5 rad/s`（约 `28.6°/s`）连续变化，松开后保持。
同侧增减键同时按下相互抵消，左右侧可独立或同时控制，也可同时驾驶。
正负方向遵循 MJCF 的关节轴定义（两侧均绕 +Y 轴）；零位附近增大角度会使
车架前端相对机身下摆、后端上摆。目标角度限于模型的 `[-1.0, 1.2] rad`
（约 `[-57.3°, 68.8°]`），大角度时实际姿态会受接触、重力和力矩上限影响。

切回普通模式后，两侧目标角度以相同速率平滑回零。再次切入控腿模式会保持
当前目标，不会跳变。终端状态行显示当前模式及左右车架目标角度（度）。
控腿速率在 `control.py` 的 `RobotController.FRAME_SPEED` 中调整。

离开控制终端后减速停车；控腿模式冻结并保持当前车架目标，头和双耳保持零位。
普通模式的平滑回零仍会继续。
Ctrl / Alt / Super（macOS 的 Command）组合键不会触发驾驶命令。
只查询控制键和快捷键修饰键，不保存键盘记录。

## 控制参数与摩擦

默认最高目标线速度为 `0.35 m/s`，最高目标偏航角速度为 `1.5 rad/s`。
线加速度为 `0.35 m/s²`，减速度为 `0.65 m/s²`；转向加速度为
`2.5 rad/s²`，减速度为 `4.0 rad/s²`。反向操作先减速至零再反向加速。

```bash
python main.py --max-speed 0.25 --max-yaw-rate 1.0
```

其余参数在 `control.py` 的 `DriveConfig` 中调整。后轮半径 `0.030 m`、
后轮中心距 `0.100 m` 来自当前模型零位几何。差速轮速按模型驱动器范围限幅。
这些是目标速度上限，不是对实际机身速度的刚性约束。

头、双耳和左右车架采用独立 PID 力矩闭环（车架目标由模式决定、速度反馈为微分项），
含力矩限幅和积分抗饱和。前轮保持被动，不添加驱动器。

前轮滑动摩擦系数 **`0.1` 直接定义在 `../robot_description/mjcf/robot_description.xml`
的两个前轮 geom 中**，为此前控制程序实际使用的 `0.05` 的两倍。
前轮 `priority="1"` 高于地面的默认优先级，保证实际接触使用 `0.1`，不会被
地面的 `1.5` 覆盖。后轮与地面接触的滑动摩擦仍为 `1.5`。
控制程序不修改任何摩擦系数或接触优先级；直接加载 MJCF 也使用同样的摩擦。

控制程序仅在内存中将数值积分器切换为 `implicitfast`，减少轮速伺服的数值
抖动。运行时不修改模型文件。

## 检查

依赖清单见 [requirements.txt](requirements.txt)，环境要求与 uv 隔离约定见 [RL 工作区 README](../README.md)。现有镜像提供 MuJoCo 和 NumPy，但其 MuJoCo 版本与依赖清单存在差异，后续应在独立 uv 环境中固定并验证版本；不要向 ROS 自带 Python 安装训练或演示依赖。

在容器的项目根目录运行自动测试：

```bash
python -m unittest discover -s RL_ws/robot_controller_demo -v
```

测试覆盖加减速、反向刹车、模式切换、独立控腿、角度限位、平滑回零、
力矩抗饱和、实际接触摩擦，以及 Linux /
macOS 输入适配器的焦点和按键状态逻辑。真实桌面的焦点报告能力取决于所用终端。

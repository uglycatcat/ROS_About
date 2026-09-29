# ROS 2 概念与工程实践讨论总结

本文档整理自本仓库 Cursor 对话中关于 PetBot 工作空间结构、ament 构建、节点/进程/线程、Launch、以及 C++/Python 可执行文件生成的讨论。

---

## 1. 工作空间中的四个包

`src/` 下现有四个 ROS 2 包：

| 包名 | 职责 |
|------|------|
| `petbot_description` | 机器人 URDF/仿真预览（Gazebo + RViz + 遥控），无算法 |
| `petbot_ground_seg` | ToF 点云：地面分割 → 背景剔除 → 欧式聚类 |
| `petbot_slam` | ToF 点云切成 LaserScan，经 slam_toolbox 二维建图 |
| `petbot_follow` | 消费簇质心，KF 跟踪 + 保持距离，发布 `/cmd_vel` |

依赖关系：

```text
petbot_description
       ↑
       ├── petbot_ground_seg
       │         ↑
       │         └── petbot_follow
       └── petbot_slam
```

四个包的业务节点目前均为 **Python**；其中 `petbot_follow` 已改为 `ament_python`，其余多为 `ament_cmake` + `install(PROGRAMS …)`。

---

## 2. 构建系统：ament、CMake、Python 安装

### 2.1 ament 是什么

**ament** 是 ROS 2 的构建与包管理系统（相对 ROS 1 的 catkin）。

- 声明包：`package.xml`
- 编译/安装：`CMakeLists.txt` 或 `setup.py`
- 让系统发现包：`ament_index`、`share/`、`lib/`
- 工作空间构建：`colcon build`

常用词：

| 词 | 含义 |
|----|------|
| ament | 整套构建体系 |
| ament_cmake | 基于 CMake 的构建类型 |
| ament_python | 基于 setuptools 的纯 Python 构建类型 |
| ament_package() | CMake 收尾：生成索引、导出等 |

### 2.2 包是否「Python / CMake 二选一」

不是硬性二选一，但多数包选一个主构建类型：

- 纯 Python → `ament_python`
- C++ 或「资源 + 脚本」→ `ament_cmake`
- 混用 → 常以 `ament_cmake` 为主，辅以 `ament_cmake_python` 或 `install(PROGRAMS …)`

### 2.3 为何 Python 节点可以没有 setup.py

ROS 2 装 Python 节点常见两条路：

| 方式 | 构建类型 | 机制 |
|------|----------|------|
| A | ament_python | `setup.py` + `console_scripts` |
| B | ament_cmake | `install(PROGRAMS scripts/xxx.py DESTINATION lib/${PROJECT_NAME})` |

本仓库早期四个包用的是 **B**：把 `.py` 当可执行脚本拷到 `lib/<包名>/`，保留执行权限（需 shebang）。  
这是常见简化写法，尤其适合独立脚本节点、彼此不 `import` 的情况。

### 2.4 petbot_follow 改为 ament_python 后的结构

```text
petbot_follow/
├── package.xml          # build_type: ament_python
├── setup.py / setup.cfg
├── resource/petbot_follow
├── petbot_follow/
│   ├── __init__.py
│   └── target_follower.py
├── launch/ config/ rviz/
└── README.md
```

- 入口：`console_scripts` → `target_follower = petbot_follow.target_follower:main`
- Launch 中 `executable='target_follower'`（无 `.py`）
- 可 `ros2 run petbot_follow target_follower`，也可 `import petbot_follow.target_follower`

### 2.5 setup.py 与 setup.cfg

| 文件 | 作用 |
|------|------|
| setup.py | 装什么：包、data_files（launch/config/rviz）、entry_points |
| setup.cfg | 脚本装到哪：`lib/<包名>/`，对齐 `ros2 run` |

`setup.cfg` 对纯 setuptools 可省略；对 ROS 2 **建议保留**，否则入口可能进 `bin/`，`ros2 run` / launch 易找不到。

对 Python 包而言：**setup.py（+ setup.cfg）≈ CMakeLists.txt 的角色**；两边都还需要 `package.xml`。

---

## 3. 从源码到 Launch 能启动的可执行文件

### 3.1 总链路（以 C++ 为例，用户已确认的理解）

```text
CMakeLists.txt
  add_executable(my_node src/...)     # 哪些源文件 → 一个程序，叫什么名
  install(TARGETS my_node
          DESTINATION lib/${PROJECT_NAME})

colcon build → 编译并装进 install/

source install/setup.bash → 进入 ROS / ament 视野

Launch Node(package=..., executable='my_node')
  → 在 install/<包>/lib/<包>/ 找到可执行文件并启动进程
```

### 3.2 CMake 如何指定「编在一起、叫什么」

```cmake
add_executable(my_node    # 产物名 / 目标名
  src/main.cpp            # 参与编译的源文件
  src/helper.cpp
)
```

- CMake 生成构建规则，再由 Make/Ninja 调编译器。
- **每个 `add_executable` 对应一个程序**，链接后必须恰好有一个 `main`：
  - 没有 `main` → 链接失败
  - 多个 `main` → 链接失败
- 一个包多个节点：多次 `add_executable`，再一并 `install(TARGETS ...)`。
- 共享代码：`add_library` + `target_link_libraries`（库本身无 `main`）。

### 3.3 Python 如何对应

| C++ | Python (ament_python) |
|-----|------------------------|
| `add_executable` + `install(TARGETS)` | `console_scripts` |
| `install(DIRECTORY launch …)` | `data_files` |

`executable=` 填的是 **安装后的名字**（entry point 左边或 `install(PROGRAMS)` 的文件名），不是源码路径。

确认方法：

```bash
source install/setup.bash
ros2 pkg executables <包名>
```

### 3.4 可执行文件名 vs 节点名

- **可执行文件名**：CMake target / console_scripts 名 → 磁盘与 `ros2 run` / launch `executable=`
- **节点名**：代码里 `Node("…")` 或 launch `name=` → 计算图

两者同名是**约定**，不是强制。

### 3.5 Launch 是否检查可执行文件里有 init / 节点？

**不检查。** Launch 只解析路径并启动进程，不静态分析是否调用了 `init`、是否创建了 Node。  
「能成为 ROS 节点进程」靠程序自身约定，不是 Launch 强制校验。

---

## 4. 包、节点、进程、线程

### 4.1 包是基本组织单位

- 编译单位：`colcon build --packages-select …`
- 依赖单位：`package.xml`
- 安装与发现：`ros2 pkg list`、`get_package_share_directory`
- 运行定位：`ros2 run <包> <可执行文件>`

节点是通信图上的参与单位；进程是 OS 调度单位。

### 4.2 节点是什么

节点是计算图中的**命名载体/身份**，用于挂载：

- 话题（pub/sub）
- 服务 / Action
- 参数
- 日志、时钟、命名空间等

业务逻辑在回调与用户代码中；节点本身不实现算法，只提供归属与发现所需的身份。

要在图上发/收话题、提供服务，**至少需要一个节点**作为主人。  
顺序：`init`（进程级上下文）→ 创建 `Node` → 再挂端点。

### 4.3 `rclcpp::init()` / `rclpy.init()` 的意义

- 初始化**进程级** ROS Client Library 上下文（解析 ROS 参数、建立 RMW/DDS 上下文等）。
- **不是**创建节点。
- 可理解为：告诉本进程「准备使用 ROS 相关 API」。
- 之后 `Node(...)` 才在图中登记参与者；对应收尾是 `shutdown()`。

### 4.4 节点、进程、线程的关系

```text
进程
 └─ 可装 1 个或多个 Node
      └─ 回调由 Executor 调度
           └─ 单线程或多线程执行回调
```

常见组合：

1. 一进程一节点 + `spin`（单线程执行器）— 最常见  
2. 一进程一节点 + `MultiThreadedExecutor`  
3. 一进程多节点（同进程多个 `Node`，或 composable container）  
4. Launch 拉起多进程多节点  

**节点与进程不是一一对应。**

---

## 5. Launch 如何工作

### 5.1 多进程如何产生

`LaunchDescription` 中的每个普通 `launch_ros.actions.Node` → 通常 **fork/exec 一个进程**。  
`IncludeLaunchDescription` 展开子 launch，其中的 `Node` 同样各自起进程。

例外：`ComposableNode` + Container → 多节点可进**同一进程**。

### 5.2 Launch 的 `Node` vs ROS 节点

| | Launch 的 `Node` | ROS 节点 |
|--|------------------|----------|
| 是什么 | Launch Action（启动指令） | 图中的通信实体 |
| 时机 | 描述/启动阶段 | 进程运行后 |
| 作用 | 指定包、可执行文件、参数等并起进程 | pub/sub/service 等 |

Launch `Node` 启动进程；进程内 `main` 创建多少个 ROS `Node`，由代码决定。

### 5.3 用户理解的修正版

> Launch 起多个进程；各进程里有一个或多个 Node；Node 挂 topic/service/param；进程间经 DDS 通信；进程内用 Executor 调度这些 Node 的回调。

补充：

- Param 跨进程访问底层常走 parameter 相关 service，概念上是节点配置，不完全等同于业务 topic 流。
- Executor 一般在 `main` 中创建并 `add_node`，不是「节点创建 Executor 来决定整个可执行文件有几个线程」。

---

## 6. Executor、spin、回调

### 6.1 节点与 Executor（形式关系）

- **Node**：拥有通信端点与用户回调；不负责决定何时、在哪个线程调用回调。
- **Executor**：等待就绪事件 → 取出工作项 → 调用回调；单线程串行或多线程并行。
- 绑定：`executor.add_node(node)`；仅当节点加入正在 `spin` 的 Executor 时，入站/timer 等回调才会被调用。
- `rclpy.spin(node)` ≈ 临时使用 **SingleThreadedExecutor**，加入该节点后阻塞 `spin`。

### 6.2 一个 Executor 上多个 Node 的回调与时序

- **SingleThreadedExecutor**：可管理多节点；任意时刻只执行一个回调；串行，无并行竞态；**不保证**跨节点业务时序。
- **MultiThreadedExecutor**：回调可并行；库不自动保证业务时序；共享状态需用户同步；可用 `callback_group` 约束互斥。

时序依赖：时间戳、QoS、用户同步逻辑等，而非全局因果调度器。

### 6.3 spin 是否「启动」节点

- `Node()` 构造后节点已存在，可创建端点，甚至可 `publish`。
- `spin` 启动的是**回调处理循环**，不是创建节点。
- 不做 `spin` / `spin_once` 等，订阅与 timer 回调通常不会执行。

### 6.4 spin 是循环吗？频率？

- 是阻塞循环：等事件 → 调回调 → 再等。
- **spin 本身无固定 Hz**；节奏由消息到达频率、timer 周期、服务请求等决定。
- 空闲时阻塞在 wait 上。

### 6.5 publish 需要 spin 吗？

- **不需要。** `publish` 可主动发送。
- 若 `publish` 写在订阅/timer 回调里，则需要 spin 才能进入那些回调。

### 6.6 如何注册回调

通过 Node 的 `create_*` API，把函数对象注册上去：

| 类型 | API | 回调时机 |
|------|-----|----------|
| 订阅 | `create_subscription(Msg, topic, cb, qos)` | 消息到达 |
| 定时器 | `create_timer(period, cb)` | 周期到期 |
| 服务 | `create_service(Srv, name, cb)` | 请求到达 |

`create_publisher` **不**注册回调。

本仓库示例（`target_follower`）：订阅 `/cluster_centroids`、`/control_mode`；`create_timer` 做控制环。

### 6.7 如何固定频率 publish

在 **timer 回调**里 `publish`，周期 = `1.0 / hz`。  
不要依赖订阅回调来定频（那跟随输入频率）。

### 6.8 Executor 与线程对应

| Executor | 回调执行线程 |
|----------|----------------|
| SingleThreadedExecutor | 1 个线程，回调串行 |
| MultiThreadedExecutor | N 个工作线程，回调可并发 |

进程内还可能有 DDS 等内部线程，不由 Executor 类型唯一决定。

### 6.9 main 中创建多个节点（示例逻辑）

```text
init()
创建 node_a, node_b
executor = SingleThreadedExecutor()
executor.add_node(node_a)
executor.add_node(node_b)
executor.spin()
shutdown()
```

一个 Launch `Node` 仍只起**一个进程**；多 ROS 节点来自该进程 `main` 里多个 `Node` 实例。

---

## 7. 概念对照速查

| 概念 | 一句话 |
|------|--------|
| 包 | 代码/资源的组织、编译、依赖、安装单位 |
| 可执行文件 | 安装到 `lib/<包>/` 的程序；launch/`ros2 run` 启动它 |
| main | 可执行文件进程入口；通常 init → Node → spin |
| init | 进程级 ROS 运行时初始化 |
| 节点 | 图上的身份与端点载体 |
| Launch Node | 启动某可执行文件的 Action |
| Executor | 调度节点回调的组件 |
| spin | 执行器的事件循环，处理回调 |
| DDS | 进程间中间件，承载 topic/service 等通信 |

---

## 8. 本对话中的工程改动备忘

- 将 `petbot_follow` 从 `ament_cmake` + `scripts/target_follower.py` 改为 `ament_python` 标准布局。
- 若本地从 cmake 迁 python 后构建报 `File exists` 一类冲突，可清理后重编：

```bash
rm -rf build/petbot_follow install/petbot_follow
colcon build --packages-select petbot_follow --symlink-install
```

---

*文档生成自对话总结，便于回顾 ROS 2 包结构、构建与运行时模型。*

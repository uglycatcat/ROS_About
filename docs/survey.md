# 低矮底盘 + ToF + IMU：跟踪滚动目标（如皮球）

## 需求简述

- 平台：类似扫地机的矮车，ToF 深度相机 + 六轴 IMU，具备 SLAM 能力
- 目标：跟踪任意可动目标（先做滚动皮球）
- 约束：视角低、目标小且快、可能短暂出视野

---

## 推荐技术路线（务实）

```
ToF 点云/深度图
  → 地面分割（矮视角必做）
  → 目标检测/分割（球：圆形/球体假设；通用：运动前景）
  → 目标状态估计（位置+速度，卡尔曼/IMM）
  → 跟踪控制（追球：预测拦截点 + 速度控制）
  ↔ SLAM/定位（给机器人自身位姿，把目标投到地图系）
```

分两层，别混：

1. **感知跟踪**：在机器人坐标系里持续给出目标相对位姿/速度
2. **运动跟踪**：根据自身定位 + 目标预测，输出线/角速度去追

皮球 MVP 建议顺序：先做「运动前景 + 球体拟合」；通用目标再上检测模型。

---

## 技术思路

### 1. 感知

| 方案 | 适用 | 备注 |
|------|------|------|
| 帧差 / 光流 + 地面滤除 | 任意动目标 MVP | 静止目标无效；依赖短时运动 |
| RANSAC 地面平面 + 离群簇 | 矮视角 ToF | 必做；去掉地板噪声 |
| 球：Hough / 最小二乘球体拟合 | 皮球 | 深度点云上拟合中心与半径 |
| 通用：YOLO/检测器 + 深度取中心 | 任意物体 | 需光照/纹理；ToF  alone 常不够 |
| 多假设跟踪 (MHT) / SORT / ByteTrack | 短暂遮挡、多目标 | 先单目标够用 |

状态估计建议：`[x, y, vx, vy]` 常速卡尔曼；球弹跳可加竖直维或切换模型（IMM）。

### 2. 定位与坐标系

- SLAM（或里程计+IMU）提供机器人在 `map` 的位姿
- 目标检测在 `camera`/`base`，变换到 `map`
- 目标丢失时：用最后速度外推短时间，同时原地搜索/回扫

### 3. 控制

- **简单**：相对目标方向 P 控制角速度，距离过大则前进
- **更好**：常速预测未来位置，规划拦截点（pure pursuit / DWA 到预测点）
- **约束**：矮车动力学简单，但视野窄 → 控制上要「先对准再加速」，避免目标从侧前方溜走

---

## 参考项目 / 论文方向

### 工程 / 开源

- **ROS2 Nav2 + custom tracker**：定位导航骨架；跟踪层自写节点
- **vision_opencv / image_pipeline**：深度处理基础
- **PCL**：平面分割、欧式聚类、球体拟合（`SampleConsensusModelSphere`）
- **SORT / ByteTrack / Norfair**：2D 多目标跟踪可借鉴关联逻辑
- **realsense / OAK / ToF 厂商 SDK 例程**：深度滤波、对齐（按实际相机换）

### 科研相关关键词

- Visual / RGB-D object tracking on mobile robots
- Ball tracking / interception for mobile robots（大量足球机器人、RoboCup）
- Ground plane removal + cluster tracking (RGB-D)
- Constant velocity / coordinated turn Kalman for rolling objects
- Active vision / gaze control for narrow FOV tracking
- Short-term target prediction under occlusion

可搜：RoboCup SSL/MSL ball tracking、RGB-D people/object following、ToF obstacle clustering。

---

## 风险与坑

| 风险 | 影响 | 缓解 |
|------|------|------|
| ToF 近距噪声、飞点、阳光/反光 | 球边缘乱跳 | 时域滤波、置信度阈值、多帧融合 |
| 视角极低 | 远距球只占几像素；近距易出视野 | 俯仰安装折中；主动转向对准目标 |
| 球速 > 车速 / 侧向切出 FOV | 跟丢 | 预测拦截；丢失后扇形搜索 |
| 球与障碍物相似簇 | 误跟 | 半径先验、颜色（若有 RGB）、运动一致性门控 |
| SLAM 漂移 / 地图更新滞后 | 地图系目标位置偏 | 近距用相对坐标追；远距才依赖 map |
| 仅 IMU+里程计无视觉闭环 | 长时位姿漂 | 跟踪闭环尽量在 `base_link` 相对做 |
| 「任意目标」范围过大 | 做不完 | 先球（强几何先验），再开放类别检测 |
| 实时性 | 点云全处理延迟大 | 先 2D 深度图 ROI，再稀疏点云拟合 |

---

## 建议落地步骤

1. 标定 ToF→base，验证地面平面分割稳定
2. 静止车：滚动球 → 检测中心 + 卡尔曼，可视化轨迹
3. 开环：车缓慢跟随相对方位（不依赖 SLAM）
4. 接入定位，目标投到 map，做短距预测追击
5. 加丢失重搜索；再考虑通用检测器替换「球假设」

最小系统：`地面分割 → 运动簇/球体拟合 → KF → 相对追控`；SLAM 作为增强，不是 Day1 阻塞项。

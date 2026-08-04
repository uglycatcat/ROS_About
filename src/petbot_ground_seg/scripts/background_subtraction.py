#!/usr/bin/env python3
"""静态背景剔除：在 odom 系用体素占用历史分离运动前景。

订阅地面分割后的障碍点云（默认 /obstacle_points），不使用 RGB/IR。
墙/家具等稳定占据体素 → 背景；新出现或移动的点 → 前景。
"""

from __future__ import annotations

import numpy as np
import rclpy
from geometry_msgs.msg import TransformStamped
from rclpy.duration import Duration
from rclpy.node import Node
from rclpy.time import Time
from sensor_msgs.msg import PointCloud2, PointField
from std_msgs.msg import Header
from tf2_ros import Buffer, TransformException, TransformListener


def _cloud_xyz(msg: PointCloud2) -> np.ndarray:
    offsets = {f.name: f.offset for f in msg.fields}
    if not all(k in offsets for k in ('x', 'y', 'z')):
        return np.zeros((0, 3), dtype=np.float32)

    n = msg.width * msg.height
    if n == 0:
        return np.zeros((0, 3), dtype=np.float32)

    names, formats, offs = [], [], []
    for name in ('x', 'y', 'z'):
        names.append(name)
        formats.append('<f4')
        offs.append(offsets[name])
    dtype = np.dtype({
        'names': names,
        'formats': formats,
        'offsets': offs,
        'itemsize': msg.point_step,
    })
    arr = np.frombuffer(msg.data, dtype=dtype, count=n)
    pts = np.stack((arr['x'], arr['y'], arr['z']), axis=1).astype(np.float32)
    mask = np.isfinite(pts).all(axis=1)
    return pts[mask]


def _transform_points(pts: np.ndarray, tf: TransformStamped) -> np.ndarray:
    t = tf.transform.translation
    q = tf.transform.rotation
    x, y, z, w = q.x, q.y, q.z, q.w
    R = np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ], dtype=np.float64)
    out = (R @ pts.T).T
    out[:, 0] += t.x
    out[:, 1] += t.y
    out[:, 2] += t.z
    return out.astype(np.float32)


def _xyz_cloud(header: Header, pts: np.ndarray) -> PointCloud2:
    msg = PointCloud2()
    msg.header = header
    msg.height = 1
    msg.width = int(pts.shape[0])
    msg.fields = [
        PointField(name='x', offset=0, datatype=PointField.FLOAT32, count=1),
        PointField(name='y', offset=4, datatype=PointField.FLOAT32, count=1),
        PointField(name='z', offset=8, datatype=PointField.FLOAT32, count=1),
    ]
    msg.is_bigendian = False
    msg.point_step = 12
    msg.row_step = msg.point_step * msg.width
    msg.is_dense = True
    msg.data = b'' if pts.size == 0 else np.asarray(pts, dtype=np.float32).tobytes()
    return msg


class VoxelOccupancyMap:
    """稀疏体素占用 EMA（世界/odom 系）。"""

    def __init__(
        self,
        voxel_size: float,
        hit_alpha: float,
        miss_decay: float,
        prune_score: float,
        max_voxels: int,
    ):
        self.vs = float(voxel_size)
        self.hit_alpha = float(hit_alpha)
        self.miss_decay = float(miss_decay)
        self.prune_score = float(prune_score)
        self.max_voxels = int(max_voxels)
        self._scores: dict[tuple[int, int, int], float] = {}

    def _keys(self, pts: np.ndarray) -> np.ndarray:
        """点 → 体素整数索引 (N,3)。"""
        return np.floor(pts / self.vs).astype(np.int32)

    def _decay_and_prune(self, hit: set[tuple[int, int, int]]):
        dead = []
        for k, score in self._scores.items():
            if k in hit:
                continue
            score *= self.miss_decay
            if score < self.prune_score:
                dead.append(k)
            else:
                self._scores[k] = score
        for k in dead:
            del self._scores[k]

        if len(self._scores) > self.max_voxels:
            ordered = sorted(self._scores.items(), key=lambda kv: kv[1])
            drop = len(self._scores) - self.max_voxels
            for k, _ in ordered[:drop]:
                del self._scores[k]

    def seed(self, pts: np.ndarray):
        """预热：命中体素直接拉高占用，快速形成静态背景。"""
        if pts.shape[0] == 0:
            return
        keys = self._keys(pts)
        hit: set[tuple[int, int, int]] = set()
        for i in range(pts.shape[0]):
            k = (int(keys[i, 0]), int(keys[i, 1]), int(keys[i, 2]))
            hit.add(k)
            prev = self._scores.get(k, 0.0)
            self._scores[k] = max(prev, (1.0 - self.hit_alpha) * prev + self.hit_alpha)
            # 连续命中加速：再抬一档，预热结束时墙面更稳
            self._scores[k] = min(1.0, self._scores[k] + 0.15)
        self._decay_and_prune(hit)

    def classify_and_update(
        self,
        pts: np.ndarray,
        static_threshold: float,
        motion_mask: np.ndarray | None = None,
    ):
        """返回 (foreground_mask, background_mask)。

        motion_mask[i]=True 的点强制前景，且不强化静态占用（避免行人轨迹烙进地图）。
        """
        n = pts.shape[0]
        if n == 0:
            return (
                np.zeros(0, dtype=bool),
                np.zeros(0, dtype=bool),
            )

        keys = self._keys(pts)
        fg = np.zeros(n, dtype=bool)
        bg = np.zeros(n, dtype=bool)
        hit: set[tuple[int, int, int]] = set()
        if motion_mask is None:
            motion_mask = np.zeros(n, dtype=bool)

        for i in range(n):
            k = (int(keys[i, 0]), int(keys[i, 1]), int(keys[i, 2]))
            hit.add(k)
            score = self._scores.get(k, 0.0)
            moving = bool(motion_mask[i])
            if moving or score < static_threshold:
                fg[i] = True
            else:
                bg[i] = True
            if moving:
                # 运动点：轻微衰减或不动分，防止走位路径变成“墙”
                self._scores[k] = score * 0.98
            else:
                self._scores[k] = (1.0 - self.hit_alpha) * score + self.hit_alpha

        self._decay_and_prune(hit)
        return fg, bg


class BackgroundSubtraction(Node):
    def __init__(self):
        super().__init__('background_subtraction')
        self.declare_parameter('input_topic', '/obstacle_points')
        self.declare_parameter('foreground_topic', '/foreground_points')
        self.declare_parameter('background_topic', '/background_points')
        self.declare_parameter('cloud_frame', 'base_link')
        self.declare_parameter('map_frame', 'odom')
        self.declare_parameter('voxel_size', 0.05)
        self.declare_parameter('hit_alpha', 0.35)
        self.declare_parameter('miss_decay', 0.92)
        self.declare_parameter('static_threshold', 0.55)
        self.declare_parameter('warmup_frames', 15)
        self.declare_parameter('prune_score', 0.05)
        self.declare_parameter('max_voxels', 80000)
        # 与上一帧点云距离大于此值 → 运动前景（米）
        self.declare_parameter('motion_distance', 0.12)

        self._input = str(self.get_parameter('input_topic').value)
        self._cloud_frame = str(self.get_parameter('cloud_frame').value)
        self._map_frame = str(self.get_parameter('map_frame').value)
        self._static_th = float(self.get_parameter('static_threshold').value)
        self._warmup = int(self.get_parameter('warmup_frames').value)
        self._motion_dist = float(self.get_parameter('motion_distance').value)
        self._frame_i = 0
        self._prev_pts: np.ndarray | None = None

        self._map = VoxelOccupancyMap(
            voxel_size=float(self.get_parameter('voxel_size').value),
            hit_alpha=float(self.get_parameter('hit_alpha').value),
            miss_decay=float(self.get_parameter('miss_decay').value),
            prune_score=float(self.get_parameter('prune_score').value),
            max_voxels=int(self.get_parameter('max_voxels').value),
        )

        self._tf_buffer = Buffer(cache_time=Duration(seconds=10.0))
        self._tf_listener = TransformListener(self._tf_buffer, self)

        fg_topic = str(self.get_parameter('foreground_topic').value)
        bg_topic = str(self.get_parameter('background_topic').value)
        self._pub_fg = self.create_publisher(PointCloud2, fg_topic, 10)
        self._pub_bg = self.create_publisher(PointCloud2, bg_topic, 10)
        self._sub = self.create_subscription(
            PointCloud2, self._input, self._on_cloud, 10)

        self.get_logger().info(
            f'BgSub: {self._input} → {fg_topic} / {bg_topic} '
            f'(map={self._map_frame}, voxel={self._map.vs} m, '
            f'warmup={self._warmup})')

    def _on_cloud(self, msg: PointCloud2):
        pts = _cloud_xyz(msg)
        src = msg.header.frame_id or self._cloud_frame
        stamp = Time.from_msg(msg.header.stamp)

        header = Header()
        header.stamp = msg.header.stamp
        header.frame_id = self._map_frame

        if pts.size == 0:
            empty = np.zeros((0, 3), np.float32)
            self._pub_fg.publish(_xyz_cloud(header, empty))
            self._pub_bg.publish(_xyz_cloud(header, empty))
            return

        try:
            tf = self._tf_buffer.lookup_transform(
                self._map_frame, src, stamp, timeout=Duration(seconds=0.05))
        except TransformException:
            try:
                tf = self._tf_buffer.lookup_transform(
                    self._map_frame, src, Time(), timeout=Duration(seconds=0.05))
            except TransformException as exc:
                self.get_logger().warn(
                    f'TF {src}→{self._map_frame} 失败: {exc}',
                    throttle_duration_sec=2.0)
                return

        pts_m = _transform_points(pts, tf)
        self._frame_i += 1

        if self._frame_i <= self._warmup:
            # 预热：只建静态占用图，输出全部当背景
            self._map.seed(pts_m)
            self._prev_pts = pts_m.copy()
            empty = np.zeros((0, 3), np.float32)
            self._pub_fg.publish(_xyz_cloud(header, empty))
            self._pub_bg.publish(_xyz_cloud(header, pts_m))
            if self._frame_i == self._warmup:
                self.get_logger().info(
                    f'背景地图预热完成（{self._warmup} 帧，'
                    f'体素数={len(self._map._scores)}）')
            return

        motion = self._motion_mask(pts_m)
        fg_mask, bg_mask = self._map.classify_and_update(
            pts_m, static_threshold=self._static_th, motion_mask=motion)
        self._prev_pts = pts_m.copy()
        fg = pts_m[fg_mask]
        bg = pts_m[bg_mask]
        self._pub_fg.publish(_xyz_cloud(header, fg))
        self._pub_bg.publish(_xyz_cloud(header, bg))
        self.get_logger().info(
            f'fg={fg.shape[0]} bg={bg.shape[0]} motion={int(motion.sum())} '
            f'voxels={len(self._map._scores)}',
            throttle_duration_sec=2.0)

    def _motion_mask(self, pts: np.ndarray) -> np.ndarray:
        """相对上一帧无近邻的点视为运动。"""
        n = pts.shape[0]
        if self._prev_pts is None or self._prev_pts.shape[0] == 0 or n == 0:
            return np.zeros(n, dtype=bool)
        # 体素粗匹配：当前点所在及邻域体素在上一帧是否有点
        vs = max(self._motion_dist, self._map.vs)
        prev_keys = np.floor(self._prev_pts / vs).astype(np.int32)
        prev_set = {
            (int(prev_keys[i, 0]), int(prev_keys[i, 1]), int(prev_keys[i, 2]))
            for i in range(prev_keys.shape[0])
        }
        cur_keys = np.floor(pts / vs).astype(np.int32)
        moving = np.zeros(n, dtype=bool)
        offs = [(dx, dy, dz)
                for dx in (-1, 0, 1)
                for dy in (-1, 0, 1)
                for dz in (-1, 0, 1)]
        for i in range(n):
            base = (int(cur_keys[i, 0]), int(cur_keys[i, 1]), int(cur_keys[i, 2]))
            found = False
            for o in offs:
                if (base[0] + o[0], base[1] + o[1], base[2] + o[2]) in prev_set:
                    found = True
                    break
            moving[i] = not found
        return moving


def main():
    rclpy.init()
    node = BackgroundSubtraction()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            node.destroy_node()
        except Exception:
            pass
        try:
            if rclpy.ok():
                rclpy.shutdown()
        except Exception:
            pass


if __name__ == '__main__':
    main()

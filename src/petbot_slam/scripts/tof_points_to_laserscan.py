#!/usr/bin/env python3
"""将 Nebula ToF 点云切成水平 LaserScan，供 slam_toolbox 二维建图。

只订阅 ToF 点云（默认 /nebula280/mtof/points），不使用 RGB/IR。
点云变换到 base_link 后按高度带滤波，再按方位角投影为 /scan。
"""

from __future__ import annotations

import math

import numpy as np
import rclpy
from geometry_msgs.msg import TransformStamped
from rclpy.duration import Duration
from rclpy.node import Node
from rclpy.time import Time
from sensor_msgs.msg import LaserScan, PointCloud2
from tf2_ros import Buffer, TransformException, TransformListener


def _cloud_xyz(msg: PointCloud2) -> np.ndarray:
    """提取 PointCloud2 中 xyz（跳过 NaN）。"""
    offsets = {f.name: f.offset for f in msg.fields}
    if not all(k in offsets for k in ('x', 'y', 'z')):
        return np.zeros((0, 3), dtype=np.float32)

    n = msg.width * msg.height
    if n == 0:
        return np.zeros((0, 3), dtype=np.float32)

    # 构造结构化 dtype，按 point_step 对齐读取
    names = []
    formats = []
    offs = []
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
    # quaternion (x,y,z,w) → rotation matrix
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


class TofPointsToLaserScan(Node):
    def __init__(self):
        super().__init__('tof_points_to_laserscan')
        self.declare_parameter('cloud_topic', '/nebula280/mtof/points')
        self.declare_parameter('scan_topic', '/scan')
        self.declare_parameter('target_frame', 'base_link')
        self.declare_parameter('min_height', -0.05)
        self.declare_parameter('max_height', 0.25)
        self.declare_parameter('range_min', 0.12)
        self.declare_parameter('range_max', 8.0)
        self.declare_parameter('angle_min', -math.pi / 2)
        self.declare_parameter('angle_max', math.pi / 2)
        self.declare_parameter('angle_increment', math.radians(0.5))
        self.declare_parameter('scan_time', 0.1)
        self.declare_parameter('use_inf', True)

        self._cloud_topic = str(self.get_parameter('cloud_topic').value)
        self._target = str(self.get_parameter('target_frame').value)
        self._z_min = float(self.get_parameter('min_height').value)
        self._z_max = float(self.get_parameter('max_height').value)
        self._r_min = float(self.get_parameter('range_min').value)
        self._r_max = float(self.get_parameter('range_max').value)
        self._a_min = float(self.get_parameter('angle_min').value)
        self._a_max = float(self.get_parameter('angle_max').value)
        self._a_inc = float(self.get_parameter('angle_increment').value)
        self._scan_time = float(self.get_parameter('scan_time').value)
        self._use_inf = bool(self.get_parameter('use_inf').value)

        n = int(round((self._a_max - self._a_min) / self._a_inc)) + 1
        self._n_beams = max(n, 2)
        self._angles = self._a_min + np.arange(self._n_beams, dtype=np.float64) * self._a_inc

        self._tf_buffer = Buffer(cache_time=Duration(seconds=10.0))
        self._tf_listener = TransformListener(self._tf_buffer, self)
        scan_topic = str(self.get_parameter('scan_topic').value)
        self._pub = self.create_publisher(LaserScan, scan_topic, 10)
        self._sub = self.create_subscription(
            PointCloud2, self._cloud_topic, self._on_cloud, 10)

        self.get_logger().info(
            f'ToF→LaserScan: {self._cloud_topic} → {scan_topic} '
            f'(frame={self._target}, z∈[{self._z_min},{self._z_max}] m, '
            f'r≤{self._r_max} m) — RGB/IR 未订阅')

    def _on_cloud(self, msg: PointCloud2):
        pts = _cloud_xyz(msg)
        if pts.size == 0:
            return

        src = msg.header.frame_id
        stamp = Time.from_msg(msg.header.stamp)
        try:
            tf = self._tf_buffer.lookup_transform(
                self._target, src, stamp,
                timeout=Duration(seconds=0.05))
        except TransformException:
            try:
                tf = self._tf_buffer.lookup_transform(
                    self._target, src, Time(),
                    timeout=Duration(seconds=0.05))
            except TransformException as exc:
                self.get_logger().warn(
                    f'TF {src}→{self._target} 失败: {exc}',
                    throttle_duration_sec=2.0)
                return

        pts_b = _transform_points(pts, tf)
        # 高度带：base_link Z 向上
        band = (pts_b[:, 2] >= self._z_min) & (pts_b[:, 2] <= self._z_max)
        pts_b = pts_b[band]
        if pts_b.size == 0:
            return

        ranges = np.full(self._n_beams, np.inf if self._use_inf else self._r_max,
                         dtype=np.float32)
        xy = pts_b[:, :2]
        r = np.linalg.norm(xy, axis=1)
        ang = np.arctan2(xy[:, 1], xy[:, 0])
        valid = (r >= self._r_min) & (r <= self._r_max) & \
                (ang >= self._a_min) & (ang <= self._a_max)
        r = r[valid]
        ang = ang[valid]
        if r.size == 0:
            return

        idx = np.floor((ang - self._a_min) / self._a_inc).astype(np.int32)
        idx = np.clip(idx, 0, self._n_beams - 1)
        np.minimum.at(ranges, idx, r.astype(np.float32))

        scan = LaserScan()
        scan.header.stamp = msg.header.stamp
        scan.header.frame_id = self._target
        scan.angle_min = self._a_min
        scan.angle_max = self._a_max
        scan.angle_increment = self._a_inc
        scan.time_increment = 0.0
        scan.scan_time = self._scan_time
        scan.range_min = self._r_min
        scan.range_max = self._r_max
        scan.ranges = ranges.tolist()
        self._pub.publish(scan)


def main():
    rclpy.init()
    node = TofPointsToLaserScan()
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

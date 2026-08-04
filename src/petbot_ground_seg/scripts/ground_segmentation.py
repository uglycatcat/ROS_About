#!/usr/bin/env python3
"""Nebula ToF 点云地面分割：RANSAC 平面拟合。

只订阅 ToF 点云（默认 /nebula280/mtof/points），不使用 RGB/IR。
点云变换到 base_link 后拟合地面平面，发布地面点与障碍物点。
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
    """提取 PointCloud2 中 xyz（跳过 NaN）。"""
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
    """打包 xyz PointCloud2（float32）。"""
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
    if pts.size == 0:
        msg.data = b''
    else:
        msg.data = np.asarray(pts, dtype=np.float32).tobytes()
    return msg


def _fit_plane(p0: np.ndarray, p1: np.ndarray, p2: np.ndarray):
    """三点拟合平面 ax+by+cz+d=0，法向单位化。失败返回 None。"""
    v1 = p1 - p0
    v2 = p2 - p0
    n = np.cross(v1, v2)
    norm = np.linalg.norm(n)
    if norm < 1e-9:
        return None
    n = n / norm
    d = -float(np.dot(n, p0))
    # 法向朝上
    if n[2] < 0:
        n = -n
        d = -d
    return n, d


def ransac_ground(
    pts: np.ndarray,
    distance_threshold: float,
    iterations: int,
    min_inliers: int,
    normal_z_min: float,
    seed_z_min: float,
    seed_z_max: float,
    stride: int,
    rng: np.random.Generator,
):
    """RANSAC 拟合近似水平地面。返回 (normal, d, inlier_mask) 或 None。"""
    if pts.shape[0] < 3:
        return None

    # RANSAC 用下采样子集加速；最终分类用全点
    sample_idx = np.arange(0, pts.shape[0], max(int(stride), 1))
    sample = pts[sample_idx]
    if sample.shape[0] < 3:
        sample = pts
        sample_idx = np.arange(pts.shape[0])

    seed_mask = (sample[:, 2] >= seed_z_min) & (sample[:, 2] <= seed_z_max)
    seed_pool = np.flatnonzero(seed_mask)
    if seed_pool.size < 3:
        seed_pool = np.arange(sample.shape[0])

    best_n = None
    best_d = 0.0
    best_count = 0

    for _ in range(iterations):
        pick = rng.choice(seed_pool, size=3, replace=False)
        plane = _fit_plane(sample[pick[0]], sample[pick[1]], sample[pick[2]])
        if plane is None:
            continue
        n, d = plane
        if n[2] < normal_z_min:
            continue
        dist = np.abs(sample @ n + d)
        count = int(np.count_nonzero(dist < distance_threshold))
        if count > best_count:
            best_count = count
            best_n = n
            best_d = d

    if best_n is None or best_count < min_inliers:
        return None

    dist_all = np.abs(pts @ best_n + best_d)
    inliers = dist_all < distance_threshold
    # 地面点还应在平面下方附近：去掉明显悬空却落在厚度带内的误检
    # （法向朝上时，点到平面的有符号距离 = n·p+d；地面附近应接近 0）
    return best_n, best_d, inliers


class GroundSegmentation(Node):
    def __init__(self):
        super().__init__('ground_segmentation')
        self.declare_parameter('cloud_topic', '/nebula280/mtof/points')
        self.declare_parameter('ground_topic', '/ground_points')
        self.declare_parameter('obstacle_topic', '/obstacle_points')
        self.declare_parameter('target_frame', 'base_link')
        self.declare_parameter('range_min', 0.12)
        self.declare_parameter('range_max', 6.0)
        self.declare_parameter('z_min', -0.35)
        self.declare_parameter('z_max', 1.20)
        self.declare_parameter('distance_threshold', 0.025)
        self.declare_parameter('ransac_iterations', 120)
        self.declare_parameter('min_inliers', 80)
        self.declare_parameter('normal_z_min', 0.85)
        self.declare_parameter('seed_z_min', -0.12)
        self.declare_parameter('seed_z_max', 0.05)
        self.declare_parameter('ransac_stride', 3)

        self._cloud_topic = str(self.get_parameter('cloud_topic').value)
        self._target = str(self.get_parameter('target_frame').value)
        self._r_min = float(self.get_parameter('range_min').value)
        self._r_max = float(self.get_parameter('range_max').value)
        self._z_min = float(self.get_parameter('z_min').value)
        self._z_max = float(self.get_parameter('z_max').value)
        self._dist_th = float(self.get_parameter('distance_threshold').value)
        self._iters = int(self.get_parameter('ransac_iterations').value)
        self._min_inliers = int(self.get_parameter('min_inliers').value)
        self._normal_z_min = float(self.get_parameter('normal_z_min').value)
        self._seed_z_min = float(self.get_parameter('seed_z_min').value)
        self._seed_z_max = float(self.get_parameter('seed_z_max').value)
        self._stride = int(self.get_parameter('ransac_stride').value)

        self._rng = np.random.default_rng(0)
        self._tf_buffer = Buffer(cache_time=Duration(seconds=10.0))
        self._tf_listener = TransformListener(self._tf_buffer, self)

        ground_topic = str(self.get_parameter('ground_topic').value)
        obstacle_topic = str(self.get_parameter('obstacle_topic').value)
        self._pub_ground = self.create_publisher(PointCloud2, ground_topic, 10)
        self._pub_obs = self.create_publisher(PointCloud2, obstacle_topic, 10)
        self._sub = self.create_subscription(
            PointCloud2, self._cloud_topic, self._on_cloud, 10)

        self.get_logger().info(
            f'GroundSeg: {self._cloud_topic} → {ground_topic} / {obstacle_topic} '
            f'(frame={self._target}, RANSAC th={self._dist_th} m) — RGB/IR 未订阅')

    def _on_cloud(self, msg: PointCloud2):
        pts = _cloud_xyz(msg)
        if pts.size == 0:
            return

        src = msg.header.frame_id
        stamp = Time.from_msg(msg.header.stamp)
        try:
            tf = self._tf_buffer.lookup_transform(
                self._target, src, stamp, timeout=Duration(seconds=0.05))
        except TransformException:
            try:
                tf = self._tf_buffer.lookup_transform(
                    self._target, src, Time(), timeout=Duration(seconds=0.05))
            except TransformException as exc:
                self.get_logger().warn(
                    f'TF {src}→{self._target} 失败: {exc}',
                    throttle_duration_sec=2.0)
                return

        pts_b = _transform_points(pts, tf)
        xy_r = np.linalg.norm(pts_b[:, :2], axis=1)
        pre = (
            (xy_r >= self._r_min) & (xy_r <= self._r_max) &
            (pts_b[:, 2] >= self._z_min) & (pts_b[:, 2] <= self._z_max)
        )
        pts_b = pts_b[pre]
        if pts_b.shape[0] < 3:
            return

        result = ransac_ground(
            pts_b,
            distance_threshold=self._dist_th,
            iterations=self._iters,
            min_inliers=self._min_inliers,
            normal_z_min=self._normal_z_min,
            seed_z_min=self._seed_z_min,
            seed_z_max=self._seed_z_max,
            stride=self._stride,
            rng=self._rng,
        )

        header = Header()
        header.stamp = msg.header.stamp
        header.frame_id = self._target

        if result is None:
            # 拟合失败：全部当障碍，避免把墙当地面
            self._pub_ground.publish(_xyz_cloud(header, np.zeros((0, 3), np.float32)))
            self._pub_obs.publish(_xyz_cloud(header, pts_b))
            self.get_logger().warn(
                'RANSAC 未找到有效地面平面', throttle_duration_sec=2.0)
            return

        n, d, inliers = result
        ground = pts_b[inliers]
        obstacle = pts_b[~inliers]
        self._pub_ground.publish(_xyz_cloud(header, ground))
        self._pub_obs.publish(_xyz_cloud(header, obstacle))
        self.get_logger().info(
            f'plane n=({n[0]:.2f},{n[1]:.2f},{n[2]:.2f}) d={d:.3f} '
            f'ground={ground.shape[0]} obs={obstacle.shape[0]}',
            throttle_duration_sec=2.0)


def main():
    rclpy.init()
    node = GroundSegmentation()
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

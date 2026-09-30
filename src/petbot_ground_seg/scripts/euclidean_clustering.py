#!/usr/bin/env python3
"""前景点云欧式聚类：拆成独立物体假设。

订阅背景剔除后的 /foreground_points（默认 odom 系），不用 RGB/IR。
发布着色簇点云、质心 PoseArray、MarkerArray。
"""

from __future__ import annotations

import colorsys

import numpy as np
import rclpy
from geometry_msgs.msg import Pose, PoseArray
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2, PointField
from std_msgs.msg import Header
from visualization_msgs.msg import Marker, MarkerArray


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


def _cluster_color(i: int) -> tuple[float, float, float]:
    """稳定可区分的 HSV 色相。"""
    h = (i * 0.61803398875) % 1.0
    r, g, b = colorsys.hsv_to_rgb(h, 0.85, 1.0)
    return r, g, b


def _xyzrgb_cloud(header: Header, pts: np.ndarray, colors: np.ndarray) -> PointCloud2:
    """打包 xyz + rgb（float rgb packed as uint32 in FLOAT32 field, PCL style）。"""
    n = int(pts.shape[0])
    msg = PointCloud2()
    msg.header = header
    msg.height = 1
    msg.width = n
    msg.fields = [
        PointField(name='x', offset=0, datatype=PointField.FLOAT32, count=1),
        PointField(name='y', offset=4, datatype=PointField.FLOAT32, count=1),
        PointField(name='z', offset=8, datatype=PointField.FLOAT32, count=1),
        PointField(name='rgb', offset=12, datatype=PointField.FLOAT32, count=1),
    ]
    msg.is_bigendian = False
    msg.point_step = 16
    msg.row_step = 16 * n
    msg.is_dense = True
    if n == 0:
        msg.data = b''
        return msg

    # PCL rgb: 0x00RRGGBB reinterpret as float
    rgb_u = (
        (np.clip(colors[:, 0] * 255.0, 0, 255).astype(np.uint32) << 16) |
        (np.clip(colors[:, 1] * 255.0, 0, 255).astype(np.uint32) << 8) |
        (np.clip(colors[:, 2] * 255.0, 0, 255).astype(np.uint32))
    )
    rgb_f = rgb_u.view(np.float32)
    buf = np.empty((n, 4), dtype=np.float32)
    buf[:, 0:3] = pts
    buf[:, 3] = rgb_f
    msg.data = buf.tobytes()
    return msg


def euclidean_cluster(
    pts: np.ndarray,
    tolerance: float,
    min_size: int,
    max_size: int,
    max_span: float,
) -> list[np.ndarray]:
    """体素哈希邻域 + BFS 欧式聚类，返回每簇的点索引数组。"""
    n = pts.shape[0]
    if n == 0:
        return []

    vs = float(tolerance)
    keys = np.floor(pts / vs).astype(np.int32)
    voxel_map: dict[tuple[int, int, int], list[int]] = {}
    for i in range(n):
        k = (int(keys[i, 0]), int(keys[i, 1]), int(keys[i, 2]))
        voxel_map.setdefault(k, []).append(i)

    visited = np.zeros(n, dtype=bool)
    clusters: list[np.ndarray] = []
    tol2 = tolerance * tolerance
    neighbor_offsets = [
        (dx, dy, dz)
        for dx in (-1, 0, 1)
        for dy in (-1, 0, 1)
        for dz in (-1, 0, 1)
    ]

    for seed in range(n):
        if visited[seed]:
            continue
        queue = [seed]
        visited[seed] = True
        members = [seed]
        qi = 0
        while qi < len(queue):
            i = queue[qi]
            qi += 1
            ki = (int(keys[i, 0]), int(keys[i, 1]), int(keys[i, 2]))
            pi = pts[i]
            for off in neighbor_offsets:
                nk = (ki[0] + off[0], ki[1] + off[1], ki[2] + off[2])
                for j in voxel_map.get(nk, ()):
                    if visited[j]:
                        continue
                    d = pts[j] - pi
                    if float(d[0] * d[0] + d[1] * d[1] + d[2] * d[2]) <= tol2:
                        visited[j] = True
                        queue.append(j)
                        members.append(j)
                        if len(members) > max_size:
                            break
                if len(members) > max_size:
                    break
            if len(members) > max_size:
                break

        if len(members) < min_size or len(members) > max_size:
            continue
        idx = np.asarray(members, dtype=np.int32)
        cpts = pts[idx]
        span = float(np.linalg.norm(cpts.max(axis=0) - cpts.min(axis=0)))
        if span > max_span:
            continue
        clusters.append(idx)

    clusters.sort(key=lambda a: a.size, reverse=True)
    return clusters


class EuclideanClustering(Node):
    def __init__(self):
        super().__init__('euclidean_clustering')
        self.declare_parameter('input_topic', '/foreground_points')
        self.declare_parameter('clustered_cloud_topic', '/cluster_points')
        self.declare_parameter('markers_topic', '/cluster_markers')
        self.declare_parameter('centroids_topic', '/cluster_centroids')
        self.declare_parameter('cluster_tolerance', 0.12)
        self.declare_parameter('min_cluster_size', 8)
        self.declare_parameter('max_cluster_size', 5000)
        self.declare_parameter('max_cluster_span', 2.8)
        self.declare_parameter('max_clusters', 20)

        self._input = str(self.get_parameter('input_topic').value)
        self._tol = float(self.get_parameter('cluster_tolerance').value)
        self._min_n = int(self.get_parameter('min_cluster_size').value)
        self._max_n = int(self.get_parameter('max_cluster_size').value)
        self._max_span = float(self.get_parameter('max_cluster_span').value)
        self._max_clusters = int(self.get_parameter('max_clusters').value)

        cloud_topic = str(self.get_parameter('clustered_cloud_topic').value)
        markers_topic = str(self.get_parameter('markers_topic').value)
        centroids_topic = str(self.get_parameter('centroids_topic').value)

        self._pub_cloud = self.create_publisher(PointCloud2, cloud_topic, 10)
        self._pub_markers = self.create_publisher(MarkerArray, markers_topic, 10)
        self._pub_centroids = self.create_publisher(PoseArray, centroids_topic, 10)
        self._sub = self.create_subscription(
            PointCloud2, self._input, self._on_cloud, 10)

        self.get_logger().info(
            f'Cluster: {self._input} → {cloud_topic} / {centroids_topic} '
            f'(tol={self._tol} m, n∈[{self._min_n},{self._max_n}])')

    def _on_cloud(self, msg: PointCloud2):
        pts = _cloud_xyz(msg)
        header = Header()
        header.stamp = msg.header.stamp
        header.frame_id = msg.header.frame_id or 'odom'

        if pts.shape[0] == 0:
            self._pub_cloud.publish(_xyzrgb_cloud(
                header, np.zeros((0, 3), np.float32), np.zeros((0, 3), np.float32)))
            self._pub_centroids.publish(PoseArray(header=header))
            self._clear_markers(header)
            return

        clusters = euclidean_cluster(
            pts, self._tol, self._min_n, self._max_n, self._max_span)
        clusters = clusters[: self._max_clusters]

        out_pts = []
        out_cols = []
        poses = PoseArray()
        poses.header = header
        markers = MarkerArray()

        # 先发 DELETEALL，避免旧 marker 残留
        clear = Marker()
        clear.header = header
        clear.ns = 'clusters'
        clear.id = 0
        clear.action = Marker.DELETEALL
        markers.markers.append(clear)

        for ci, idx in enumerate(clusters):
            cpts = pts[idx]
            color = _cluster_color(ci)
            out_pts.append(cpts)
            out_cols.append(np.tile(np.asarray(color, dtype=np.float32), (cpts.shape[0], 1)))

            centroid = cpts.mean(axis=0)
            pose = Pose()
            pose.position.x = float(centroid[0])
            pose.position.y = float(centroid[1])
            pose.position.z = float(centroid[2])
            # 约定：orientation.x = 簇点数，供跟随选大目标（行人）
            pose.orientation.x = float(cpts.shape[0])
            pose.orientation.w = 1.0
            poses.poses.append(pose)

            # 质心球
            m = Marker()
            m.header = header
            m.ns = 'clusters'
            m.id = ci + 1
            m.type = Marker.SPHERE
            m.action = Marker.ADD
            m.pose = pose
            extent = cpts.max(axis=0) - cpts.min(axis=0)
            r = float(max(0.05, 0.5 * np.linalg.norm(extent) * 0.35))
            m.scale.x = m.scale.y = m.scale.z = r
            m.color.r, m.color.g, m.color.b = color
            m.color.a = 0.55
            markers.markers.append(m)

            # 编号
            t = Marker()
            t.header = header
            t.ns = 'cluster_ids'
            t.id = ci + 1
            t.type = Marker.TEXT_VIEW_FACING
            t.action = Marker.ADD
            t.pose.position.x = float(centroid[0])
            t.pose.position.y = float(centroid[1])
            t.pose.position.z = float(centroid[2] + r + 0.05)
            t.pose.orientation.w = 1.0
            t.scale.z = 0.12
            t.color.r = t.color.g = t.color.b = 1.0
            t.color.a = 0.95
            t.text = f'{ci}:{cpts.shape[0]}'
            markers.markers.append(t)

        if out_pts:
            all_pts = np.vstack(out_pts).astype(np.float32)
            all_cols = np.vstack(out_cols).astype(np.float32)
        else:
            all_pts = np.zeros((0, 3), np.float32)
            all_cols = np.zeros((0, 3), np.float32)

        self._pub_cloud.publish(_xyzrgb_cloud(header, all_pts, all_cols))
        self._pub_centroids.publish(poses)
        self._pub_markers.publish(markers)
        self.get_logger().info(
            f'clusters={len(clusters)} pts_in={pts.shape[0]} pts_out={all_pts.shape[0]}',
            throttle_duration_sec=2.0)

    def _clear_markers(self, header: Header):
        arr = MarkerArray()
        m = Marker()
        m.header = header
        m.ns = 'clusters'
        m.action = Marker.DELETEALL
        arr.markers.append(m)
        m2 = Marker()
        m2.header = header
        m2.ns = 'cluster_ids'
        m2.action = Marker.DELETEALL
        arr.markers.append(m2)
        self._pub_markers.publish(arr)


def main():
    rclpy.init()
    node = EuclideanClustering()
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

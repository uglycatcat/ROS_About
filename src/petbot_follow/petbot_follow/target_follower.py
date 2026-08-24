"""自动跟随：簇质心选目标 + 常速 KF + base_link 相对追控。

订阅 /cluster_centroids（odom），发布 /cmd_vel。
策略：关联门控跟踪；丢失后慢转搜索；先对准再前进，保持 standoff。
"""

from __future__ import annotations

import math

import numpy as np
import rclpy
from geometry_msgs.msg import PoseArray, PoseStamped, TransformStamped, Twist
from rclpy.duration import Duration
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from rclpy.time import Time
from std_msgs.msg import Header, String
from tf2_ros import Buffer, TransformException, TransformListener
from visualization_msgs.msg import Marker


def _tf_to_mat(tf: TransformStamped) -> np.ndarray:
    t = tf.transform.translation
    q = tf.transform.rotation
    x, y, z, w = q.x, q.y, q.z, q.w
    R = np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ], dtype=np.float64)
    T = np.eye(4, dtype=np.float64)
    T[:3, :3] = R
    T[0, 3] = t.x
    T[1, 3] = t.y
    T[2, 3] = t.z
    return T


def _transform_xy(pts_xy: np.ndarray, T: np.ndarray) -> np.ndarray:
    if pts_xy.size == 0:
        return pts_xy
    n = pts_xy.shape[0]
    hom = np.ones((n, 4), dtype=np.float64)
    hom[:, 0] = pts_xy[:, 0]
    hom[:, 1] = pts_xy[:, 1]
    out = (T @ hom.T).T
    return out[:, :2]


class ConstantVelocityKF:
    """二维常速：[x, y, vx, vy]。"""

    def __init__(self, q: float, r: float):
        self.q = float(q)
        self.r = float(r)
        self.x = np.zeros(4, dtype=np.float64)
        self.P = np.eye(4, dtype=np.float64)
        self.initialized = False

    def init(self, xy: np.ndarray):
        self.x[:] = [float(xy[0]), float(xy[1]), 0.0, 0.0]
        self.P = np.eye(4, dtype=np.float64) * 0.5
        self.initialized = True

    def predict(self, dt: float):
        if not self.initialized or dt <= 0.0:
            return
        F = np.array([
            [1, 0, dt, 0],
            [0, 1, 0, dt],
            [0, 0, 1, 0],
            [0, 0, 0, 1],
        ], dtype=np.float64)
        Q = np.array([
            [dt ** 4 / 4, 0, dt ** 3 / 2, 0],
            [0, dt ** 4 / 4, 0, dt ** 3 / 2],
            [dt ** 3 / 2, 0, dt ** 2, 0],
            [0, dt ** 3 / 2, 0, dt ** 2],
        ], dtype=np.float64) * (self.q ** 2)
        self.x = F @ self.x
        self.P = F @ self.P @ F.T + Q

    def update(self, z: np.ndarray):
        if not self.initialized:
            self.init(z)
            return
        H = np.array([[1, 0, 0, 0], [0, 1, 0, 0]], dtype=np.float64)
        R = np.eye(2, dtype=np.float64) * (self.r ** 2)
        y = z - H @ self.x
        S = H @ self.P @ H.T + R
        K = self.P @ H.T @ np.linalg.inv(S)
        self.x = self.x + K @ y
        self.P = (np.eye(4) - K @ H) @ self.P

    def pos(self) -> np.ndarray:
        return self.x[:2].copy()

    def extrapolated(self, dt: float) -> np.ndarray:
        return self.x[:2] + self.x[2:4] * max(0.0, dt)

    def reset(self):
        self.initialized = False
        self.x[:] = 0.0


class TargetFollower(Node):
    def __init__(self):
        super().__init__('target_follower')
        self.declare_parameter('centroids_topic', '/cluster_centroids')
        self.declare_parameter('cmd_vel_topic', '/cmd_vel')
        self.declare_parameter('target_marker_topic', '/follow_target_marker')
        self.declare_parameter('target_pose_topic', '/follow_target_pose')
        self.declare_parameter('base_frame', 'base_link')
        self.declare_parameter('enable_control', True)
        self.declare_parameter('mode_topic', '/control_mode')
        self.declare_parameter('require_follow_mode', True)
        self.declare_parameter('fov_half_angle', 1.4)
        self.declare_parameter('associate_gate', 1.2)
        self.declare_parameter('min_target_range', 0.12)
        self.declare_parameter('max_target_range', 6.0)
        self.declare_parameter('lost_timeout', 1.5)
        self.declare_parameter('search_spin', 0.55)
        self.declare_parameter('min_cluster_points', 15)
        self.declare_parameter('standoff_distance', 0.20)
        self.declare_parameter('align_angle', 0.35)
        self.declare_parameter('kp_linear', 0.7)
        self.declare_parameter('kp_angular', 1.8)
        self.declare_parameter('max_linear_x', 1.2)
        self.declare_parameter('max_angular_z', 1.0)
        self.declare_parameter('max_backup', 0.25)
        self.declare_parameter('control_rate', 20.0)
        self.declare_parameter('process_noise', 0.5)
        self.declare_parameter('measurement_noise', 0.08)

        g = self.get_parameter
        self._base = str(g('base_frame').value)
        self._enable = bool(g('enable_control').value)
        self._require_mode = bool(g('require_follow_mode').value)
        self._mode = 'manual'  # 默认手动，等 /control_mode
        self._fov = float(g('fov_half_angle').value)
        self._gate = float(g('associate_gate').value)
        self._rmin = float(g('min_target_range').value)
        self._rmax = float(g('max_target_range').value)
        self._lost_timeout = float(g('lost_timeout').value)
        self._search_spin = float(g('search_spin').value)
        self._min_pts = int(g('min_cluster_points').value)
        self._standoff = float(g('standoff_distance').value)
        self._align = float(g('align_angle').value)
        self._kp_v = float(g('kp_linear').value)
        self._kp_w = float(g('kp_angular').value)
        self._vmax = float(g('max_linear_x').value)
        self._wmax = float(g('max_angular_z').value)
        self._max_backup = float(g('max_backup').value)

        self._kf = ConstantVelocityKF(
            q=float(g('process_noise').value),
            r=float(g('measurement_noise').value),
        )
        self._has_target = False
        self._last_detect: Time | None = None
        self._last_predict_t: Time | None = None
        self._msg_stamp: Time | None = None
        self._centroids_frame = 'odom'
        self._centroids = np.zeros((0, 2), dtype=np.float64)
        self._sizes = np.zeros(0, dtype=np.float64)

        self._tf_buffer = Buffer(cache_time=Duration(seconds=10.0))
        self._tf_listener = TransformListener(self._tf_buffer, self)

        mode_qos = QoSProfile(
            depth=1,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            reliability=ReliabilityPolicy.RELIABLE,
        )

        cmd_topic = str(g('cmd_vel_topic').value)
        self._pub_cmd = self.create_publisher(Twist, cmd_topic, 10)
        self._pub_marker = self.create_publisher(
            Marker, str(g('target_marker_topic').value), 10)
        self._pub_pose = self.create_publisher(
            PoseStamped, str(g('target_pose_topic').value), 10)
        self.create_subscription(
            PoseArray, str(g('centroids_topic').value), self._on_centroids, 10)
        self.create_subscription(
            String, str(g('mode_topic').value), self._on_mode, mode_qos)

        rate = float(g('control_rate').value)
        self.create_timer(1.0 / max(rate, 1.0), self._on_control)

        self.get_logger().info(
            f'Follow: /cluster_centroids → {cmd_topic}  '
            f'standoff={self._standoff:.2f} m  '
            f'mode_gate={"ON" if self._require_mode else "OFF"}  '
            f'v≤{self._vmax} w≤{self._wmax}')

    def _on_mode(self, msg: String):
        mode = msg.data.strip().lower()
        if mode not in ('manual', 'follow'):
            return
        if mode == self._mode:
            return
        prev = self._mode
        self._mode = mode
        self.get_logger().info(f'控制模式 {prev} → {mode}')
        if mode == 'manual':
            self._pub_cmd.publish(Twist())
        else:
            # 进入跟随：清空旧锁，立刻用当前簇重选（偏大目标/行人）
            self._clear_target()
            if self._centroids.shape[0] > 0:
                self._associate(self._centroids, self._sizes, force_new=True)

    def _follow_active(self) -> bool:
        if not self._enable:
            return False
        if self._require_mode and self._mode != 'follow':
            return False
        return True

    def _compute_follow_speed(self, dist: float, bearing: float) -> tuple[float, float]:
        """保持 standoff：过近只后退/刹停，过远才前进；大偏航只转不冲。"""
        w = max(-self._wmax, min(self._wmax, self._kp_w * bearing))
        if abs(bearing) > self._align:
            return 0.0, w

        err = dist - self._standoff
        if err > 0.05:
            # 太远：前进靠近，偏航越大前进越小
            v = self._kp_v * err
            v = min(self._vmax, v)
            v *= max(0.0, 1.0 - abs(bearing) / max(self._align, 1e-3))
        elif err < -0.05:
            # 太近：后退拉开，禁止继续前冲
            v = self._kp_v * err  # 负值
            v = max(-self._max_backup, v)
        else:
            # 在保持带内：只转向对准
            v = 0.0
        return float(v), float(w)

    def _on_centroids(self, msg: PoseArray):
        self._centroids_frame = msg.header.frame_id or 'odom'
        if msg.header.stamp.sec or msg.header.stamp.nanosec:
            self._msg_stamp = Time.from_msg(msg.header.stamp)
        if msg.poses:
            self._centroids = np.array(
                [[p.position.x, p.position.y] for p in msg.poses],
                dtype=np.float64,
            )
            # orientation.x 约定为簇点数（见 euclidean_clustering）
            self._sizes = np.array(
                [max(1.0, float(p.orientation.x)) for p in msg.poses],
                dtype=np.float64,
            )
        else:
            self._centroids = np.zeros((0, 2), dtype=np.float64)
            self._sizes = np.zeros(0, dtype=np.float64)
        self._associate(self._centroids, self._sizes)

    def _associate(
        self,
        centroids: np.ndarray,
        sizes: np.ndarray,
        force_new: bool = False,
    ):
        now = self.get_clock().now()
        if self._has_target and self._last_predict_t is not None and not force_new:
            dt = max(1e-3, (now - self._last_predict_t).nanoseconds * 1e-9)
            self._kf.predict(dt)
        self._last_predict_t = now

        if centroids.shape[0] == 0:
            return

        meas = None
        if self._has_target and not force_new:
            d = np.linalg.norm(centroids - self._kf.pos()[None, :], axis=1)
            i = int(np.argmin(d))
            if d[i] <= self._gate:
                meas = centroids[i]

        if meas is None:
            # 跟丢或新锁定：视场内选「大且不太远」的簇（行人优先于噪点）
            meas = self._pick_in_fov(centroids, sizes)

        if meas is None:
            return

        if not self._has_target or force_new:
            self._kf.init(meas)
            self._has_target = True
            self.get_logger().info(f'锁定目标 ({meas[0]:.2f}, {meas[1]:.2f})')
        else:
            self._kf.update(meas)
        self._last_detect = now

    def _pick_in_fov(
        self,
        centroids_odom: np.ndarray,
        sizes: np.ndarray | None = None,
    ) -> np.ndarray | None:
        try:
            tf = self._lookup_tf(self._base, self._centroids_frame)
        except TransformException:
            return None
        pts_b = _transform_xy(centroids_odom, _tf_to_mat(tf))
        ranges = np.linalg.norm(pts_b, axis=1)
        bearings = np.arctan2(pts_b[:, 1], pts_b[:, 0])
        if sizes is None or sizes.shape[0] != centroids_odom.shape[0]:
            sizes = np.ones(centroids_odom.shape[0], dtype=np.float64)
        mask = (
            (pts_b[:, 0] > 0.05) &
            (np.abs(bearings) <= self._fov) &
            (ranges >= self._rmin) &
            (ranges <= self._rmax) &
            (sizes >= float(self._min_pts))
        )
        if not np.any(mask):
            # 放宽：若没有够大的簇，仍允许点数>=8 的候选
            mask = (
                (pts_b[:, 0] > 0.05) &
                (np.abs(bearings) <= self._fov) &
                (ranges >= self._rmin) &
                (ranges <= self._rmax) &
                (sizes >= 8.0)
            )
        if not np.any(mask):
            return None
        idx = np.flatnonzero(mask)
        # 分数：点数 / (距离+0.5)，偏行人等大目标
        score = sizes[idx] / (ranges[idx] + 0.5)
        best = idx[int(np.argmax(score))]
        return centroids_odom[best]

    def _lookup_tf(self, target: str, source: str) -> TransformStamped:
        stamp = self._msg_stamp if self._msg_stamp is not None else Time()
        try:
            return self._tf_buffer.lookup_transform(
                target, source, stamp, timeout=Duration(seconds=0.05))
        except TransformException:
            return self._tf_buffer.lookup_transform(
                target, source, Time(), timeout=Duration(seconds=0.05))

    def _clear_target(self):
        if self._has_target:
            self.get_logger().warn('目标丢失，进入搜索', throttle_duration_sec=2.0)
        self._has_target = False
        self._kf.reset()
        self._last_detect = None
        self._last_predict_t = None

    def _on_control(self):
        now = self.get_clock().now()
        cmd = Twist()

        if not self._follow_active():
            # 手动模式：不发 cmd_vel，避免抢遥控
            self._publish_viz(
                self._kf.extrapolated(0.0) if self._has_target and self._kf.initialized
                else None)
            return

        # 超时丢目标
        if self._has_target:
            if self._last_detect is None:
                self._clear_target()
            else:
                age = (now - self._last_detect).nanoseconds * 1e-9
                if age > self._lost_timeout:
                    self._clear_target()

        # 无目标时尝试锁定 + 搜索旋转
        if not self._has_target:
            if self._centroids.shape[0] > 0:
                meas = self._pick_in_fov(self._centroids, self._sizes)
                if meas is not None:
                    self._kf.init(meas)
                    self._has_target = True
                    self._last_detect = now
                    self._last_predict_t = now
                    self.get_logger().info(
                        f'搜索锁定 ({meas[0]:.2f}, {meas[1]:.2f})')
            if not self._has_target:
                cmd.angular.z = float(self._search_spin)
                self._pub_cmd.publish(cmd)
                self._publish_viz(None)
                return

        dt = 0.0
        if self._last_predict_t is not None:
            dt = (now - self._last_predict_t).nanoseconds * 1e-9
        target_odom = self._kf.extrapolated(dt)

        try:
            tf = self._lookup_tf(self._base, self._centroids_frame)
            p_b = _transform_xy(target_odom.reshape(1, 2), _tf_to_mat(tf))[0]
        except TransformException as exc:
            self.get_logger().warn(f'TF 失败: {exc}', throttle_duration_sec=2.0)
            self._pub_cmd.publish(Twist())
            self._publish_viz(target_odom)
            return

        bearing = math.atan2(float(p_b[1]), float(p_b[0]))
        dist = float(np.linalg.norm(p_b))
        v, w = self._compute_follow_speed(dist, bearing)
        cmd.linear.x = v
        cmd.angular.z = w
        self._publish_viz(target_odom)
        self._pub_cmd.publish(cmd)

        self.get_logger().info(
            f'[{self._mode}] dist={dist:.2f} (standoff={self._standoff:.2f}) '
            f'bear={bearing:.2f} v={v:.2f} w={w:.2f}',
            throttle_duration_sec=2.0)

    def _publish_viz(self, target_odom: np.ndarray | None):
        header = Header()
        header.stamp = self.get_clock().now().to_msg()
        header.frame_id = self._centroids_frame
        m = Marker()
        m.header = header
        m.ns = 'follow_target'
        m.id = 1
        if target_odom is None:
            m.action = Marker.DELETE
            self._pub_marker.publish(m)
            return
        m.type = Marker.SPHERE
        m.action = Marker.ADD
        m.pose.position.x = float(target_odom[0])
        m.pose.position.y = float(target_odom[1])
        m.pose.position.z = 0.15
        m.pose.orientation.w = 1.0
        m.scale.x = m.scale.y = m.scale.z = 0.22
        m.color.r, m.color.g, m.color.b, m.color.a = 0.1, 0.95, 0.25, 0.85
        self._pub_marker.publish(m)

        ps = PoseStamped()
        ps.header = header
        ps.pose.position.x = float(target_odom[0])
        ps.pose.position.y = float(target_odom[1])
        ps.pose.orientation.w = 1.0
        self._pub_pose.publish(ps)


def main():
    rclpy.init()
    node = TargetFollower()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            node._pub_cmd.publish(Twist())
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

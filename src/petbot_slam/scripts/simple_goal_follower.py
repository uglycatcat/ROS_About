#!/usr/bin/env python3
"""根据 RViz 发布的 /goal_pose，用简单 P 控制驱动差速车到达目标。"""
import math

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped, Twist
from tf2_ros import Buffer, TransformListener, TransformException


class SimpleGoalFollower(Node):
    def __init__(self):
        super().__init__('simple_goal_follower')
        self.declare_parameter('map_frame', 'map')
        self.declare_parameter('base_frame', 'base_footprint')
        self.declare_parameter('linear_gain', 0.8)
        self.declare_parameter('angular_gain', 1.5)
        self.declare_parameter('max_linear', 0.35)
        self.declare_parameter('max_angular', 1.0)
        self.declare_parameter('goal_tolerance', 0.15)
        self.declare_parameter('yaw_tolerance', 0.25)

        self.map_frame = self.get_parameter('map_frame').value
        self.base_frame = self.get_parameter('base_frame').value
        self.linear_gain = self.get_parameter('linear_gain').value
        self.angular_gain = self.get_parameter('angular_gain').value
        self.max_linear = self.get_parameter('max_linear').value
        self.max_angular = self.get_parameter('max_angular').value
        self.goal_tolerance = self.get_parameter('goal_tolerance').value
        self.yaw_tolerance = self.get_parameter('yaw_tolerance').value

        self.goal = None
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.cmd_pub = self.create_publisher(Twist, 'cmd_vel', 10)
        self.create_subscription(PoseStamped, 'goal_pose', self._on_goal, 10)
        self.create_timer(0.1, self._control)
        self.get_logger().info('等待 RViz「2D Goal Pose」下发目标 (/goal_pose)')

    def _on_goal(self, msg: PoseStamped):
        self.goal = msg
        self.get_logger().info(
            f'新目标: ({msg.pose.position.x:.2f}, {msg.pose.position.y:.2f})'
        )

    def _control(self):
        if self.goal is None:
            return
        try:
            tf = self.tf_buffer.lookup_transform(
                self.map_frame, self.base_frame, rclpy.time.Time()
            )
        except TransformException:
            return

        t = tf.transform.translation
        q = tf.transform.rotation
        yaw = math.atan2(
            2.0 * (q.w * q.z + q.x * q.y),
            1.0 - 2.0 * (q.y * q.y + q.z * q.z),
        )

        gx = self.goal.pose.position.x
        gy = self.goal.pose.position.y
        dx = gx - t.x
        dy = gy - t.y
        dist = math.hypot(dx, dy)
        target_yaw = math.atan2(dy, dx)
        yaw_err = math.atan2(math.sin(target_yaw - yaw), math.cos(target_yaw - yaw))

        cmd = Twist()
        if dist < self.goal_tolerance:
            self.cmd_pub.publish(cmd)
            self.get_logger().info('已到达目标')
            self.goal = None
            return

        # 先转向，再前进
        cmd.angular.z = max(
            -self.max_angular,
            min(self.max_angular, self.angular_gain * yaw_err),
        )
        if abs(yaw_err) < self.yaw_tolerance:
            cmd.linear.x = max(
                -self.max_linear,
                min(self.max_linear, self.linear_gain * dist),
            )
        self.cmd_pub.publish(cmd)


def main():
    rclpy.init()
    node = SimpleGoalFollower()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()

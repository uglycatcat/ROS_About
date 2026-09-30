#!/usr/bin/env python3
"""将 Gazebo 32FC1 深度图转为 mono8，便于 RViz Image 显示。

Gazebo 无效像素为 +Inf；RViz 对含 Inf 的 float 图做 Normalize 时常整幅变黑。
本节点过滤 Inf/NaN，按 [min_depth, max_depth] 线性映射到 0~255（近亮远暗）。
"""

from __future__ import annotations

import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image


class DepthToGray(Node):
    def __init__(self):
        super().__init__('depth_to_gray')
        self.declare_parameter('min_depth', 0.1)
        self.declare_parameter('max_depth', 8.0)
        self._min = float(self.get_parameter('min_depth').value)
        self._max = float(self.get_parameter('max_depth').value)
        if self._max <= self._min:
            self._max = self._min + 1.0

        self._pub = self.create_publisher(Image, 'depth/image_viz', 10)
        self._sub = self.create_subscription(
            Image, 'depth/image_raw', self._on_depth, 10)
        self.get_logger().info(
            f'深度可视化: depth/image_raw → depth/image_viz '
            f'[{self._min:.2f}, {self._max:.2f}] m')

    def _on_depth(self, msg: Image):
        if msg.encoding != '32FC1':
            self.get_logger().warn(
                f'不支持的 encoding={msg.encoding}，需要 32FC1',
                throttle_duration_sec=5.0)
            return

        depth = np.frombuffer(msg.data, dtype=np.float32).reshape(
            msg.height, msg.width)
        valid = np.isfinite(depth)
        gray = np.zeros(depth.shape, dtype=np.uint8)
        if valid.any():
            t = (depth[valid] - self._min) / (self._max - self._min)
            t = np.clip(t, 0.0, 1.0)
            gray[valid] = ((1.0 - t) * 255.0).astype(np.uint8)

        viz = Image()
        viz.header = msg.header
        viz.height = msg.height
        viz.width = msg.width
        viz.encoding = 'mono8'
        viz.is_bigendian = 0
        viz.step = msg.width
        viz.data = gray.tobytes()
        self._pub.publish(viz)


def main():
    rclpy.init()
    node = DepthToGray()
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

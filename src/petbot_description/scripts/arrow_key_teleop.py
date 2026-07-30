#!/usr/bin/env python3
"""PetBot 键盘遥控 → geometry_msgs/Twist (/cmd_vel)

约定（ROS 差速底盘常用）：
  Twist.linear.x  > 0 前进，< 0 后退   [m/s]
  Twist.angular.z > 0 左转（逆时针），< 0 右转  [rad/s]
  其余分量保持 0

按住方向键输出峰值速度，松开为 0；空格急停。
优先 X11 全局抓键；无 DISPLAY 时回退终端读键。
"""

from __future__ import annotations

import os
import select
import termios
import threading
import tty
from ctypes import (
    CDLL,
    POINTER,
    Structure,
    Union,
    byref,
    c_char_p,
    c_int,
    c_long,
    c_uint,
    c_ulong,
    c_void_p,
)

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node


HELP = """
PetBot Twist 遥控  (/cmd_vel)
--------------------------------
  ↑ / ↓     : linear.x  = ± max_linear_x
  ← / →     : angular.z = ± max_angular_z
  空格      : 急停（清零 Twist）
  Ctrl+C    : 退出

默认峰值：linear.x = 2.0 m/s，angular.z = 2.5 rad/s
已启用全局抓键（Gazebo / RViz 焦点下也可用）。
"""

XK_SPACE = 0x0020
XK_LEFT = 0xFF51
XK_UP = 0xFF52
XK_RIGHT = 0xFF53
XK_DOWN = 0xFF54
KEY_PRESS = 2
KEY_RELEASE = 3
GRAB_MODE_ASYNC = 1
LOCK_MASK = 1 << 1
MOD2_MASK = 1 << 4


class _XKeyEvent(Structure):
    _fields_ = [
        ('type', c_int),
        ('serial', c_ulong),
        ('send_event', c_int),
        ('display', c_void_p),
        ('window', c_ulong),
        ('root', c_ulong),
        ('subwindow', c_ulong),
        ('time', c_ulong),
        ('x', c_int),
        ('y', c_int),
        ('x_root', c_int),
        ('y_root', c_int),
        ('state', c_uint),
        ('keycode', c_uint),
        ('same_screen', c_int),
    ]


class _XEvent(Union):
    _fields_ = [
        ('type', c_int),
        ('xkey', _XKeyEvent),
        ('pad', c_long * 24),
    ]


class TwistTeleop(Node):
    """按键状态 → 周期性发布 Twist。"""

    def __init__(self):
        super().__init__('twist_teleop')
        self.declare_parameter('cmd_vel_topic', 'cmd_vel')
        self.declare_parameter('max_linear_x', 2.0)      # m/s 峰值
        self.declare_parameter('max_angular_z', 2.5)     # rad/s 峰值
        self.declare_parameter('publish_rate', 20.0)     # Hz

        topic = str(self.get_parameter('cmd_vel_topic').value)
        self._max_lin = float(self.get_parameter('max_linear_x').value)
        self._max_ang = float(self.get_parameter('max_angular_z').value)
        rate = float(self.get_parameter('publish_rate').value)
        if rate <= 0.0:
            rate = 20.0

        self._pub = self.create_publisher(Twist, topic, 10)
        self._pressed: set[str] = set()
        self._lock = threading.Lock()
        self._last = Twist()
        period = 1.0 / rate
        self.create_timer(period, self._on_timer)

        self.get_logger().info(
            f'Twist teleop → {topic}  '
            f'max linear.x={self._max_lin:.2f} m/s  '
            f'max angular.z={self._max_ang:.2f} rad/s  '
            f'@ {rate:.0f} Hz'
        )

    def set_key(self, name: str, down: bool):
        with self._lock:
            if name == 'space' and down:
                self._pressed.clear()
                return
            if down:
                self._pressed.add(name)
            else:
                self._pressed.discard(name)

    def stop(self):
        with self._lock:
            self._pressed.clear()
        self._publish_twist(0.0, 0.0)

    def _desired_twist(self) -> tuple[float, float]:
        with self._lock:
            keys = set(self._pressed)
        lin = 0.0
        ang = 0.0
        if 'up' in keys:
            lin += self._max_lin
        if 'down' in keys:
            lin -= self._max_lin
        if 'left' in keys:
            ang += self._max_ang
        if 'right' in keys:
            ang -= self._max_ang
        # 同时前进+后退 → 0；峰值已是单键满速，对角组合不叠加超过峰值
        lin = max(-self._max_lin, min(self._max_lin, lin))
        ang = max(-self._max_ang, min(self._max_ang, ang))
        return lin, ang

    def _on_timer(self):
        lin, ang = self._desired_twist()
        self._publish_twist(lin, ang)

    def _publish_twist(self, linear_x: float, angular_z: float):
        msg = Twist()
        msg.linear.x = float(linear_x)
        msg.angular.z = float(angular_z)
        self._pub.publish(msg)
        self._last = msg


def _keycode_to_name(code: int, mapping: dict[int, str]) -> str | None:
    return mapping.get(code)


def _run_x11_grab(node: TwistTeleop) -> bool:
    display_name = os.environ.get('DISPLAY')
    if not display_name:
        return False

    try:
        x11 = CDLL('libX11.so.6')
    except OSError:
        node.get_logger().warn('未找到 libX11，回退到终端读键')
        return False

    x11.XOpenDisplay.argtypes = [c_char_p]
    x11.XOpenDisplay.restype = c_void_p
    x11.XDefaultRootWindow.argtypes = [c_void_p]
    x11.XDefaultRootWindow.restype = c_ulong
    x11.XKeysymToKeycode.argtypes = [c_void_p, c_ulong]
    x11.XKeysymToKeycode.restype = c_uint
    x11.XGrabKey.argtypes = [c_void_p, c_int, c_uint, c_ulong, c_int, c_int, c_int]
    x11.XGrabKey.restype = c_int
    x11.XUngrabKey.argtypes = [c_void_p, c_int, c_uint, c_ulong]
    x11.XUngrabKey.restype = c_int
    x11.XPending.argtypes = [c_void_p]
    x11.XPending.restype = c_int
    x11.XNextEvent.argtypes = [c_void_p, POINTER(_XEvent)]
    x11.XNextEvent.restype = c_int
    x11.XFlush.argtypes = [c_void_p]
    x11.XCloseDisplay.argtypes = [c_void_p]
    x11.XCloseDisplay.restype = c_int

    dpy = x11.XOpenDisplay(display_name.encode())
    if not dpy:
        node.get_logger().warn(f'无法打开 X display {display_name}，回退到终端读键')
        return False

    root = x11.XDefaultRootWindow(dpy)
    keysyms = {
        'up': XK_UP,
        'down': XK_DOWN,
        'left': XK_LEFT,
        'right': XK_RIGHT,
        'space': XK_SPACE,
    }
    keycodes = {name: x11.XKeysymToKeycode(dpy, ks) for name, ks in keysyms.items()}
    if any(code == 0 for code in keycodes.values()):
        x11.XCloseDisplay(dpy)
        node.get_logger().warn('方向键 keycode 无效，回退到终端读键')
        return False

    code_to_name = {code: name for name, code in keycodes.items()}
    modifier_masks = [0, LOCK_MASK, MOD2_MASK, LOCK_MASK | MOD2_MASK]
    grabbed = []
    for code in keycodes.values():
        for mods in modifier_masks:
            x11.XGrabKey(dpy, code, mods, root, True, GRAB_MODE_ASYNC, GRAB_MODE_ASYNC)
            grabbed.append((code, mods))
    x11.XFlush(dpy)
    node.get_logger().info('X11 全局抓键已启用')

    event = _XEvent()
    try:
        while rclpy.ok():
            if x11.XPending(dpy) == 0:
                rclpy.spin_once(node, timeout_sec=0.02)
                continue
            x11.XNextEvent(dpy, byref(event))
            name = _keycode_to_name(int(event.xkey.keycode), code_to_name)
            if name is None:
                continue
            if int(event.type) == KEY_PRESS:
                node.set_key(name, True)
            elif int(event.type) == KEY_RELEASE:
                node.set_key(name, False)
    finally:
        for code, mods in grabbed:
            x11.XUngrabKey(dpy, code, mods, root)
        x11.XCloseDisplay(dpy)
    return True


def _get_key(tty_in, settings):
    tty.setraw(tty_in.fileno())
    rlist, _, _ = select.select([tty_in], [], [], 0.1)
    key = tty_in.read(1) if rlist else ''
    if key == '\x1b':
        if select.select([tty_in], [], [], 0.01)[0]:
            key += tty_in.read(1)
        if len(key) >= 2 and select.select([tty_in], [], [], 0.01)[0]:
            key += tty_in.read(1)
    termios.tcsetattr(tty_in, termios.TCSADRAIN, settings)
    return key


def _run_tty(node: TwistTeleop):
    tty_in = open('/dev/tty', 'r')
    settings = termios.tcgetattr(tty_in)
    node.get_logger().warn('终端读键模式：请先点击运行 launch 的终端')
    try:
        while rclpy.ok():
            key = _get_key(tty_in, settings)
            if key == '\x03':
                break
            mapping = {
                '\x1b[A': 'up',
                '\x1b[B': 'down',
                '\x1b[D': 'left',
                '\x1b[C': 'right',
                ' ': 'space',
            }
            name = mapping.get(key)
            if name == 'space':
                node.set_key('space', True)
            elif name:
                with node._lock:
                    node._pressed.clear()
                    node._pressed.add(name)
            rclpy.spin_once(node, timeout_sec=0.0)
    finally:
        termios.tcsetattr(tty_in, termios.TCSADRAIN, settings)
        tty_in.close()


def main():
    rclpy.init()
    node = TwistTeleop()
    print(HELP, flush=True)
    try:
        if not _run_x11_grab(node):
            _run_tty(node)
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        node.get_logger().error(str(exc))
    finally:
        try:
            if rclpy.ok():
                node.stop()
        except Exception:
            pass
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

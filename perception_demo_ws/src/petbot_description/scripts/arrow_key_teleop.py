#!/usr/bin/env python3
"""PetBot 键盘遥控 → geometry_msgs/Twist (/cmd_vel)

约定（ROS 差速底盘常用）：
  Twist.linear.x  > 0 前进，< 0 后退   [m/s]
  Twist.angular.z > 0 左转（逆时针），< 0 右转  [rad/s]
  其余分量保持 0

按住方向键输出峰值速度，松开为 0。
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
    c_char,
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
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import String


HELP = """
PetBot Twist 遥控  (/cmd_vel)
--------------------------------
  ↑ / ↓     : linear.x  = ± max_linear_x
  ← / →     : angular.z = ± max_angular_z
  F         : 手动遥控 ⇄ 自动跟随（仅 follow.launch 或 teleop_mode_toggle:=true）
  Ctrl+C    : 退出

跟随请用:  ros2 launch petbot_follow follow.launch.py
（只开 ground_seg 时按 F 不会切换，只会在终端打出字母 f）
"""

XK_LEFT = 0xFF51
XK_UP = 0xFF52
XK_RIGHT = 0xFF53
XK_DOWN = 0xFF54
XK_F = 0x0066
XK_F_UPPER = 0x0046
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
    """按键状态 → 周期性发布 Twist；可选 F 键切换手动/跟随。"""

    MODE_MANUAL = 'manual'
    MODE_FOLLOW = 'follow'

    def __init__(self):
        super().__init__('twist_teleop')
        self.declare_parameter('cmd_vel_topic', 'cmd_vel')
        self.declare_parameter('max_linear_x', 1.2)     # m/s 峰值
        self.declare_parameter('max_angular_z', 1.0)     # rad/s 峰值
        self.declare_parameter('publish_rate', 20.0)     # Hz
        self.declare_parameter('enable_mode_toggle', False)
        self.declare_parameter('mode_topic', '/control_mode')
        self.declare_parameter('initial_mode', 'manual')

        topic = str(self.get_parameter('cmd_vel_topic').value)
        self._max_lin = float(self.get_parameter('max_linear_x').value)
        self._max_ang = float(self.get_parameter('max_angular_z').value)
        rate = float(self.get_parameter('publish_rate').value)
        if rate <= 0.0:
            rate = 20.0

        self._mode_toggle = bool(self.get_parameter('enable_mode_toggle').value)
        init_mode = str(self.get_parameter('initial_mode').value).strip().lower()
        if init_mode not in (self.MODE_MANUAL, self.MODE_FOLLOW):
            init_mode = self.MODE_MANUAL
        self._mode = init_mode
        self._mode_topic = str(self.get_parameter('mode_topic').value)

        self._pub = self.create_publisher(Twist, topic, 10)
        mode_qos = QoSProfile(
            depth=1,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            reliability=ReliabilityPolicy.RELIABLE,
        )
        self._mode_pub = self.create_publisher(String, self._mode_topic, mode_qos)
        self._pressed: set[str] = set()
        self._lock = threading.Lock()
        self._last = Twist()
        self._f_down = False
        period = 1.0 / rate
        self.create_timer(period, self._on_timer)
        self._mode_boot_left = 5 if self._mode_toggle else 0
        if self._mode_toggle:
            self.create_timer(0.2, self._boot_publish_mode)

        self.get_logger().info(
            f'Twist teleop → {topic}  '
            f'max linear.x={self._max_lin:.2f} m/s  '
            f'max angular.z={self._max_ang:.2f} rad/s  '
            f'@ {rate:.0f} Hz'
        )
        if self._mode_toggle:
            self.get_logger().info(
                f'模式切换已启用：按 F 切换 manual/follow '
                f'(当前={self._mode}，{self._mode_topic})')
        else:
            self.get_logger().warn(
                '模式切换未启用（enable_mode_toggle=false）。'
                '若要跟目标请用: ros2 launch petbot_follow follow.launch.py')

    def _boot_publish_mode(self):
        if self._mode_boot_left <= 0:
            return
        self._publish_mode()
        self._mode_boot_left -= 1

    def _publish_mode(self):
        msg = String()
        msg.data = self._mode
        self._mode_pub.publish(msg)

    def toggle_mode(self):
        if not self._mode_toggle:
            return
        with self._lock:
            self._mode = (
                self.MODE_FOLLOW if self._mode == self.MODE_MANUAL else self.MODE_MANUAL)
            self._pressed.clear()
        self._publish_twist(0.0, 0.0)
        self._publish_mode()
        self.get_logger().info(f'控制模式 → {self._mode}')

    def set_key(self, name: str, down: bool):
        if name == 'mode_toggle':
            if down and not self._f_down:
                self._f_down = True
                self.toggle_mode()
            elif not down:
                self._f_down = False
            return
        with self._lock:
            if self._mode != self.MODE_MANUAL:
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
        if self._mode != self.MODE_MANUAL:
            return 0.0, 0.0
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
        lin = max(-self._max_lin, min(self._max_lin, lin))
        ang = max(-self._max_ang, min(self._max_ang, ang))
        return lin, ang

    def _on_timer(self):
        lin, ang = self._desired_twist()
        # 跟随模式不抢 cmd_vel（发 0 会顶掉跟随指令），直接跳过
        if self._mode == self.MODE_FOLLOW:
            return
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
    }
    # 字母 F 用 XQueryKeymap 轮询（XGrabKey 对字母键常无效），不依赖窗口焦点
    mode_keycode = 0
    if node._mode_toggle:
        mode_keycode = int(x11.XKeysymToKeycode(dpy, XK_F))
        if mode_keycode == 0:
            node.get_logger().warn('F 键 keycode 无效，模式切换不可用')

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
    node.get_logger().info('X11 全局抓键已启用（方向键）')
    if mode_keycode:
        node.get_logger().info(f'模式键 F 使用键盘状态轮询 (keycode={mode_keycode})')

    x11.XQueryKeymap.argtypes = [c_void_p, POINTER(c_char)]
    x11.XQueryKeymap.restype = c_int
    keymap = (c_char * 32)()
    f_was_down = False

    event = _XEvent()
    try:
        while rclpy.ok():
            # 轮询 F：不抢焦点也能切模式
            if mode_keycode:
                x11.XQueryKeymap(dpy, keymap)
                down = bool(keymap[mode_keycode // 8][0] & (1 << (mode_keycode % 8)))
                if down and not f_was_down:
                    node.set_key('mode_toggle', True)
                    node.set_key('mode_toggle', False)
                f_was_down = down

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
                'f': 'mode_toggle',
                'F': 'mode_toggle',
            }
            name = mapping.get(key)
            if name == 'mode_toggle':
                node.set_key('mode_toggle', True)
                node.set_key('mode_toggle', False)
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

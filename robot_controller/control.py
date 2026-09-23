"""PetBot driving commands and joint torque control, independent of the UI."""

from dataclasses import dataclass

import mujoco
import numpy as np


FRONT_WHEEL_FRICTION = 0.05


def configure_simulation(model: mujoco.MjModel):
    """Runtime-only tuning; keep the source MJCF and rear traction unchanged."""
    model.opt.integrator = mujoco.mjtIntegrator.mjINT_IMPLICITFAST
    floor = model.geom('floor').id
    for name in ('left_front_wheel', 'right_front_wheel'):
        wheel = model.geom(name).id
        model.geom_friction[wheel, 0] = FRONT_WHEEL_FRICTION
        # Equal-priority geoms use the larger friction coefficient. Override the
        # floor's 1.5 here, otherwise lowering only the wheel has no effect.
        # These wheels' collision masks allow contact with the floor only.
        model.geom_priority[wheel] = model.geom_priority[floor] + 1


@dataclass(frozen=True)
class DriveConfig:
    # SI units: m/s, rad/s, m/s², rad/s².
    max_speed: float = 0.35
    max_yaw_rate: float = 1.5
    acceleration: float = 0.35
    braking: float = 0.65
    yaw_acceleration: float = 2.5
    yaw_braking: float = 4.0
    wheel_radius: float = 0.030
    track_width: float = 0.100


def approach(value: float, target: float, rate: float, dt: float) -> float:
    return value + float(np.clip(target - value, -rate * dt, rate * dt))


def ramp(value: float, target: float, acceleration: float, braking: float,
         dt: float) -> float:
    # Brake through zero before accelerating in the opposite direction.
    if value * target < 0:
        return approach(value, 0.0, braking, dt)
    rate = acceleration if abs(target) > abs(value) else braking
    return approach(value, target, rate, dt)


class DriveCommand:
    def __init__(self, config: DriveConfig):
        self.config = config
        self.speed = 0.0
        self.yaw_rate = 0.0

    def update(self, keys: set[str], dt: float, active: bool = True):
        c = self.config
        throttle = int('up' in keys) - int('down' in keys) if active else 0
        steering = int('left' in keys) - int('right' in keys) if active else 0
        if 'space' in keys:
            throttle = steering = 0
        self.speed = ramp(self.speed, throttle * c.max_speed,
                          c.acceleration, c.braking, dt)
        self.yaw_rate = ramp(self.yaw_rate, steering * c.max_yaw_rate,
                             c.yaw_acceleration, c.yaw_braking, dt)
        return self.wheel_speeds()

    def wheel_speeds(self):
        c = self.config
        return np.array([
            (self.speed - self.yaw_rate * c.track_width / 2) / c.wheel_radius,
            (self.speed + self.yaw_rate * c.track_width / 2) / c.wheel_radius,
        ])


class RobotController:
    # Each tuple is (joint/actuator name, Kp, Ki, Kd). Targets are radians.
    HOLD_GAINS = (
        ('head', 2.5, 1.0, 0.10),
        ('left_ear', 0.18, 0.12, 0.008),
        ('right_ear', 0.18, 0.12, 0.008),
        ('left_frame', 5.0, 2.0, 0.15),
        ('right_frame', 5.0, 2.0, 0.15),
    )

    def __init__(self, model: mujoco.MjModel, config: DriveConfig | None = None):
        self.drive = DriveCommand(config or DriveConfig())
        names = [row[0] for row in self.HOLD_GAINS]
        self.qpos = np.array([model.joint(n).qposadr[0] for n in names])
        self.dof = np.array([model.joint(n).dofadr[0] for n in names])
        self.actuators = np.array([model.actuator(n).id for n in names])
        self.kp, self.ki, self.kd = np.array([r[1:] for r in self.HOLD_GAINS]).T
        self.integral = np.zeros(len(names))
        self.targets = np.zeros(len(names))
        self.low = model.actuator_ctrlrange[self.actuators, 0]
        self.high = model.actuator_ctrlrange[self.actuators, 1]
        self.wheels = np.array([model.actuator(n).id for n in
                               ('left_rear_wheel', 'right_rear_wheel')])
        self.wheel_limits = model.actuator_ctrlrange[self.wheels]

    def step(self, data: mujoco.MjData, keys: set[str], dt: float,
             active: bool = True):
        error = self.targets - data.qpos[self.qpos]
        proposed = self.integral + error * dt
        raw = self.kp * error + self.ki * proposed - self.kd * data.qvel[self.dof]
        # Conditional integration: don't wind up while pushing into saturation.
        blocked = ((raw > self.high) & (error > 0)) | ((raw < self.low) & (error < 0))
        self.integral = np.where(blocked, self.integral, proposed)
        torque = self.kp * error + self.ki * self.integral - self.kd * data.qvel[self.dof]
        data.ctrl[self.actuators] = np.clip(torque, self.low, self.high)
        wheels = self.drive.update(keys, dt, active)
        # Preserve curvature if a later configuration exceeds motor speed limits.
        bound = np.minimum(-self.wheel_limits[:, 0], self.wheel_limits[:, 1])
        scale = max(1.0, float(np.max(np.abs(wheels) / bound)))
        data.ctrl[self.wheels] = wheels / scale

# ============================================================
# DB4 cooling PID controller.
# Cooling-only: positive error (too warm) => more cooling.
# update() returns an output clamped to [0, 100] %.
# ============================================================

import time

import config


class CoolingPID:
    def __init__(self, setpoint=config.TARGET_TEMP,
                 kp=config.PID_KP, ki=config.PID_KI, kd=config.PID_KD,
                 integral_limit=config.PID_INTEGRAL_LIMIT,
                 out_min=0.0, out_max=100.0):
        self.setpoint = setpoint
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.integral_limit = integral_limit
        self.out_min = out_min
        self.out_max = out_max
        self.reset()

    def reset(self):
        self.integral = 0.0
        self.last_error = 0.0
        self.last_time = time.time()

    @staticmethod
    def _clamp(value, low, high):
        return low if value < low else high if value > high else value

    def update(self, temp_c):
        """Return (output_pct, error). output_pct is 0..100."""
        if temp_c is None:
            return 0.0, 0.0

        now = time.time()
        dt = now - self.last_time
        if dt <= 0:
            dt = config.SAMPLE_TIME
        self.last_time = now

        error = temp_c - self.setpoint

        self.integral = self._clamp(
            self.integral + error * dt,
            -self.integral_limit, self.integral_limit,
        )
        derivative = (error - self.last_error) / dt
        self.last_error = error

        output = self.kp * error + self.ki * self.integral + self.kd * derivative
        return self._clamp(output, self.out_min, self.out_max), error

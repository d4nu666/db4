# ============================================================
# DB4 PID CONTROLLER
# Cooling-only PID for mussel tank temperature control.
# Positive error = water is too warm and cooling is needed.
# ============================================================

import time


class CoolingPID:
    def __init__(
        self,
        setpoint=18.0,
        kp=45.0,
        ki=0.006,
        kd=0.0,
        output_min=0.0,
        output_max=100.0,
        deadband=0.2,
        window_s=30,
        integral_limit=500.0,
    ):
        self.setpoint = setpoint
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.output_min = output_min
        self.output_max = output_max
        self.deadband = deadband
        self.window_s = window_s
        self.integral_limit = integral_limit

        self.integral = 0.0
        self.last_error = 0.0
        self.last_time = time.time()
        self.window_start = time.time()
        self.output = 0.0
        self.cooling_state = False

    def reset(self):
        self.integral = 0.0
        self.last_error = 0.0
        self.last_time = time.time()
        self.window_start = time.time()
        self.output = 0.0
        self.cooling_state = False

    def update(self, current_temp):
        if current_temp is None:
            self.output = 0.0
            self.cooling_state = False
            return self.output, self.cooling_state, 0.0

        now = time.time()
        dt = now - self.last_time
        if dt <= 0:
            dt = 1.0
        self.last_time = now

        # Cooling-only error. Positive means too warm.
        error = current_temp - self.setpoint

        # Stop cooling when at or below target.
        if error <= 0:
            self.integral *= 0.8
            self.last_error = error
            self.output = 0.0
            self.cooling_state = False
            return self.output, self.cooling_state, error

        self.integral += error * dt
        if self.integral > self.integral_limit:
            self.integral = self.integral_limit
        elif self.integral < -self.integral_limit:
            self.integral = -self.integral_limit

        derivative = (error - self.last_error) / dt
        self.last_error = error

        output = self.kp * error + self.ki * self.integral + self.kd * derivative

        if output > self.output_max:
            output = self.output_max
        elif output < self.output_min:
            output = self.output_min

        self.output = output

        # Slow PWM-like relay window for the cooling module.
        if now - self.window_start >= self.window_s:
            self.window_start = now

        time_in_window = now - self.window_start
        on_time = self.window_s * (self.output / 100.0)

        if current_temp > self.setpoint + self.deadband:
            self.cooling_state = time_in_window < on_time
        elif current_temp <= self.setpoint:
            self.cooling_state = False

        return self.output, self.cooling_state, error

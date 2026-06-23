# ============================================================
# DB4 biological scheduler.
# Estimates algae/waste levels and decides when to run the
# algae and waste pumps. The two pumps never run together.
# See report section 5 (control-oriented model).
# ============================================================

import time

import config


def _clamp(value, low, high):
    return low if value < low else high if value > high else value


class BioController:
    def __init__(self, algae_pump, waste_pump):
        self.algae_pump = algae_pump
        self.waste_pump = waste_pump

        # Estimated state
        self.Am = config.INIT_AM
        self.Aa = config.INIT_AA
        self.Wm = config.INIT_WM
        self.Wa = config.INIT_WA

        # Pump activity tracking
        self.algae_feeding = False
        self.waste_pumping = False
        self.algae_feed_start = 0
        self.waste_pump_start = 0
        self.last_algae_feed_start = -999999
        self.last_waste_pump_start = -999999

        self._last_model_time = time.time()

    # ---- model integration ------------------------------------
    def _update_model(self):
        now = time.time()
        dt_h = max(now - self._last_model_time, config.SAMPLE_TIME) / 3600.0
        self._last_model_time = now

        ua = self.algae_pump.state
        uw = self.waste_pump.state

        dAm = ua * config.ALPHA_A * (self.Aa - self.Am) - config.KF * self.Am
        dWm = config.WASTE_YIELD * config.KF * self.Am - uw * config.ALPHA_W * self.Wm
        dAa = config.MU * self.Aa + config.ETA * self.Wa * self.Aa - ua * config.ALPHA_A * self.Aa
        dWa = uw * config.ALPHA_W * self.Wm - config.ETA * self.Wa * self.Aa

        self.Am = _clamp(self.Am + dAm * dt_h, 0.0, 1.50)
        self.Wm = _clamp(self.Wm + dWm * dt_h, 0.0, 2.00)
        self.Aa = _clamp(self.Aa + dAa * dt_h, 0.0, 2.00)
        self.Wa = _clamp(self.Wa + dWa * dt_h, 0.0, 2.00)

    # ---- scheduler --------------------------------------------
    def update(self, elapsed):
        self._update_model()
        self._stop_finished_doses(elapsed)
        if self.algae_feeding or self.waste_pumping:
            return
        if self._maybe_feed_algae(elapsed):
            return
        self._maybe_pump_waste(elapsed)

    def _stop_finished_doses(self, elapsed):
        if self.algae_feeding and elapsed - self.algae_feed_start >= config.ALGAE_FEED_DURATION:
            self.algae_pump.off()
            self.algae_feeding = False
            print("Algae feeding finished")
        if self.waste_pumping and elapsed - self.waste_pump_start >= config.WASTE_PUMP_DURATION:
            self.waste_pump.off()
            self.waste_pumping = False
            print("Waste pump finished")

    def _maybe_feed_algae(self, elapsed):
        since_feed = elapsed - self.last_algae_feed_start
        too_low = self.Am < config.A_LOW
        ready = since_feed >= config.MIN_TIME_BETWEEN_ALGAE_FEEDS
        overdue = since_feed >= config.MAX_TIME_BETWEEN_ALGAE_FEEDS
        first_run = self.last_algae_feed_start < 0

        if (too_low and ready) or overdue or first_run:
            print("Starting algae pump: mussel tank needs food")
            self.algae_pump.on()
            self.algae_feeding = True
            self.algae_feed_start = elapsed
            self.last_algae_feed_start = elapsed
            return True
        return False

    def _maybe_pump_waste(self, elapsed):
        if elapsed - self.last_waste_pump_start < config.MIN_TIME_BETWEEN_WASTE_PUMPS:
            return
        since_feed = elapsed - self.last_algae_feed_start
        too_high = self.Wm > config.W_MAX
        delay_ok = since_feed >= config.MIN_WASTE_DELAY_AFTER_FEED
        backup_due = since_feed >= config.MAX_WASTE_DELAY_AFTER_FEED

        if too_high and delay_ok:
            reason = "mussel waste is high"
        elif backup_due:
            reason = "backup after algae feeding"
        else:
            return

        print("Starting waste pump:", reason)
        self.waste_pump.on()
        self.waste_pumping = True
        self.waste_pump_start = elapsed
        self.last_waste_pump_start = elapsed

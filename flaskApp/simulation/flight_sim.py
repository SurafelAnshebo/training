"""
Kinematic BVLOS flight simulator.

Replaces ArduPilot SITL with a self-contained Python model suitable for
procedure training. Not intended for aerodynamic research.

Physics model:
  - Multirotor kinematics: position updated via spherical geometry
  - Speed ramps with constant acceleration; nose-down in cruise, banked in turns
  - GPS noise injected during GPS_DEGRADED scenario
  - Battery drained proportionally to flight phase and active scenarios
"""
import math
import time
import threading
import random
import logging
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)

from flaskApp.simulation.traffic import make_traffic


# ---------------------------------------------------------------------------
# Geo math helpers
# ---------------------------------------------------------------------------

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance in metres between two WGS-84 coordinates."""
    R = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def initial_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Initial bearing in degrees (0 = N, 90 = E)."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    x = math.sin(dl) * math.cos(p2)
    y = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def move_along_bearing(lat: float, lon: float, brg_deg: float, dist_m: float):
    """Return (lat, lon) after travelling dist_m metres on bearing brg_deg."""
    R = 6_371_000.0
    ad = dist_m / R
    brg = math.radians(brg_deg)
    lat_r = math.radians(lat)
    lon_r = math.radians(lon)
    lat2 = math.asin(
        math.sin(lat_r) * math.cos(ad)
        + math.cos(lat_r) * math.sin(ad) * math.cos(brg)
    )
    lon2 = lon_r + math.atan2(
        math.sin(brg) * math.sin(ad) * math.cos(lat_r),
        math.cos(ad) - math.sin(lat_r) * math.sin(lat2),
    )
    return math.degrees(lat2), math.degrees(lon2)


# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------

class MissionState(Enum):
    IDLE      = "IDLE"
    TAKEOFF   = "TAKEOFF"
    NAVIGATING = "NAVIGATING"
    HOVERING  = "HOVERING"
    RTL       = "RTL"
    LANDING   = "LANDING"
    COMPLETE  = "COMPLETE"
    ABORTED   = "ABORTED"
    CRASHED   = "CRASHED"


# ---------------------------------------------------------------------------
# Simulator
# ---------------------------------------------------------------------------

class FlightSimulator:
    SIM_HZ = 10           # physics update rate
    RECORD_HZ = 2         # telemetry snapshot rate (stored + emitted)
    WP_ACCEPT_M = 30.0    # waypoint acceptance radius in metres (wide for BVLOS speeds)
    DEFAULT_SPEED = 50.0  # m/s — minimum BVLOS cruise speed
    MIN_SPEED = 50.0      # m/s — pilots cannot set below this
    MAX_SPEED_CAP = 80.0  # m/s — hard upper limit
    MAX_CLIMB = 5.0       # m/s
    MAX_DESCENT = 4.0     # m/s
    ACCEL = 4.0           # m/s² — higher accel for BVLOS speeds
    MAX_YAW_RATE = 90.0   # deg/s
    BATTERY_MAH = 6000
    IDLE_A = 3.0          # amps: hover
    CRUISE_A = 16.0       # amps: cruise
    CLIMB_A = 22.0        # amps: hard climb

    def __init__(self, home_lat: float, home_lon: float):
        self.home_lat = home_lat
        self.home_lon = home_lon

        # Cruise speed (set by pilot at launch, clamped to [MIN_SPEED, MAX_SPEED_CAP])
        self._max_speed = self.DEFAULT_SPEED

        # Position / motion
        self.lat = home_lat
        self.lon = home_lon
        self.alt = 0.0
        self._target_alt = 0.0
        self._groundspeed = 0.0
        self._vertical_rate = 0.0
        self._heading = 0.0   # degrees
        self._pitch = 0.0
        self._roll = 0.0

        # Battery (4S LiPo)
        self._bat_mah_used = 0.0
        self._bat_voltage = 16.8
        self._bat_current = 0.0
        self._bat_level = 100.0

        # GPS
        self._gps_fix = 3
        self._gps_sats = 14
        self._gps_lost_drift: Optional[float] = None  # deg/step, set on first GPS_LOST tick

        # Traffic (DAA)
        self._traffic = make_traffic()
        self._proximity: dict[str, dict] = {}   # callsign → alert data
        self._collision_info: Optional[dict] = None

        # Proximity thresholds
        self._WARN_H  = 500.0   # m horizontal — TCAS advisory
        self._CRASH_H = 80.0    # m horizontal — collision
        self._WARN_V  = 60.0    # m vertical   — TCAS advisory
        self._CRASH_V = 25.0    # m vertical   — collision

        # State
        self.flight_mode = "STABILIZE"
        self.armed = False
        self._state = MissionState.IDLE

        # Mission
        self._waypoints: list[dict] = []   # raw dicts from frontend
        self._wp_idx = 0

        # Scenarios: name → expiry_time | None (permanent)
        self._scenarios: dict[str, Optional[float]] = {}

        # Logs
        self.flight_log: list[dict] = []
        self.event_log: list[dict] = []
        self._session_start: Optional[float] = None

        # Threading
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------ public API

    def arm(self):
        with self._lock:
            if self._state != MissionState.IDLE:
                raise RuntimeError("Cannot arm: mission already active")
            self.armed = True
            self.flight_mode = "GUIDED"
            self._session_start = time.time()
            self._log_event("ARMED")

    def start_mission(self, waypoints: list[dict], speed_ms: float = None,
                      scenario_events: list[dict] = None):
        with self._lock:
            if not self.armed:
                raise RuntimeError("Arm vehicle before starting mission")
            if speed_ms is not None:
                self._max_speed = max(self.MIN_SPEED, min(float(speed_ms), self.MAX_SPEED_CAP))
            self._waypoints = waypoints
            self._wp_idx = 0
            self._target_alt = float(waypoints[0].get("altitude", 30)) if waypoints else 30.0
            self._state = MissionState.TAKEOFF
            self.flight_mode = "AUTO"
            self._log_event("MISSION_START", {"waypoints": len(waypoints), "speed_ms": self._max_speed})

        if scenario_events:
            self._run_scenario_script(scenario_events)

    def _run_scenario_script(self, events: list[dict]):
        """Fire scripted training events at their designated elapsed times."""
        sorted_events = sorted(events, key=lambda e: e["at_s"])

        def _fire():
            for ev in sorted_events:
                target_s = ev["at_s"]
                # Wait until elapsed time reaches the trigger point
                while self._running:
                    elapsed = time.time() - self._session_start if self._session_start else 0
                    if elapsed >= target_s:
                        break
                    time.sleep(0.3)
                if not self._running:
                    return
                with self._lock:
                    if self._state in (MissionState.COMPLETE, MissionState.ABORTED):
                        return
                self.inject_scenario(ev["type"], ev.get("duration_s"))

        threading.Thread(target=_fire, daemon=True, name="scenario-script").start()

    def hover(self):
        with self._lock:
            if self._state in (MissionState.NAVIGATING, MissionState.TAKEOFF):
                self._state = MissionState.HOVERING
                self.flight_mode = "GUIDED"
                self._log_event("HOVER")

    def resume(self):
        with self._lock:
            if self._state == MissionState.HOVERING:
                self._state = MissionState.NAVIGATING
                self.flight_mode = "AUTO"
                self._log_event("RESUME")

    def land(self):
        with self._lock:
            self._state = MissionState.LANDING
            self.flight_mode = "LAND"
            self._log_event("LAND_COMMANDED")

    def rtl(self):
        """Return-to-launch: fly back to home and land there."""
        with self._lock:
            if self._state not in (MissionState.NAVIGATING, MissionState.HOVERING,
                                   MissionState.TAKEOFF, MissionState.RTL):
                return
            # Replace remaining route with a direct glide back to the launch point.
            # One waypoint at altitude=0 triggers the glide-slope approach.
            self._waypoints = [
                {"lat": self.home_lat, "lng": self.home_lon, "altitude": 0}
            ]
            self._wp_idx = 0
            self._state = MissionState.RTL
            self.flight_mode = "RTL"
            self._log_event("RTL_COMMANDED")

    def abort(self):
        with self._lock:
            self._state = MissionState.ABORTED
            self.flight_mode = "STABILIZE"
            self.armed = False
            self._log_event("ABORTED")

    def inject_scenario(self, scenario_type: str, duration_s: Optional[float]):
        with self._lock:
            expiry = time.time() + duration_s if duration_s else None
            self._scenarios[scenario_type] = expiry
            self._log_event("SCENARIO_INJECTED", {"type": scenario_type, "duration": duration_s})

    def clear_scenario(self, scenario_type: str):
        with self._lock:
            self._scenarios.pop(scenario_type, None)
            self._log_event("SCENARIO_CLEARED", {"type": scenario_type})

    def get_telemetry(self) -> dict:
        with self._lock:
            return self._snapshot()

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="flight-sim")
        self._thread.start()

    def stop(self):
        self._running = False

    def reset(self):
        self.stop()
        home_lat, home_lon = self.home_lat, self.home_lon
        self.__init__(home_lat, home_lon)

    # ------------------------------------------------------------------ sim loop

    def _loop(self):
        dt = 1.0 / self.SIM_HZ
        record_every = max(1, self.SIM_HZ // self.RECORD_HZ)
        step = 0
        while self._running:
            t0 = time.monotonic()
            with self._lock:
                self._step(dt)
                if step % record_every == 0:
                    self.flight_log.append(self._snapshot())
            step += 1
            elapsed = time.monotonic() - t0
            time.sleep(max(0.0, dt - elapsed))

    def _update_traffic(self, dt: float):
        """Advance all traffic aircraft and check for proximity / collision."""
        active_states = {
            MissionState.TAKEOFF, MissionState.NAVIGATING,
            MissionState.HOVERING, MissionState.RTL, MissionState.LANDING,
        }
        trainee_airborne = self._state in active_states and self.alt > 5.0

        new_prox: dict[str, dict] = {}
        for tf in self._traffic:
            tf.step(dt)
            if not trainee_airborne:
                continue

            h = haversine(self.lat, self.lon, tf.lat, tf.lon)
            v = abs(self.alt - tf.alt)

            if h < self._CRASH_H and v < self._CRASH_V:
                self._state = MissionState.CRASHED
                self.armed  = False
                self.flight_mode = "CRASH"
                self._collision_info = {
                    "callsign":  tf.callsign,
                    "h_dist_m":  round(h),
                    "v_dist_m":  round(v),
                }
                self._log_event("COLLISION", self._collision_info)
                return   # skip further traffic checks

            if h < self._WARN_H and v < self._WARN_V:
                bearing = initial_bearing(self.lat, self.lon, tf.lat, tf.lon)
                new_prox[tf.callsign] = {
                    "callsign":    tf.callsign,
                    "distance_m":  round(h),
                    "bearing":     round(bearing),
                    "alt_diff_m":  round(tf.alt - self.alt),
                }

        self._proximity = new_prox

    def _step(self, dt: float):
        self._expire_scenarios()
        self._update_traffic(dt)
        if self._state == MissionState.CRASHED:
            return                       # physics frozen after collision
        s = self._state
        if s == MissionState.TAKEOFF:
            self._step_takeoff(dt)
        elif s in (MissionState.NAVIGATING, MissionState.RTL):
            self._step_navigate(dt)
        elif s == MissionState.HOVERING:
            self._step_hover(dt)
        elif s == MissionState.LANDING:
            self._step_land(dt)
        self._update_battery(dt)

    # ---- phase handlers ----

    def _step_takeoff(self, dt: float):
        climb = min(self.MAX_CLIMB, max(0.0, self._target_alt - self.alt))
        self._vertical_rate = climb
        self.alt += climb * dt
        self._groundspeed = 0.0
        self._pitch = -math.degrees(math.atan2(climb, 1.0)) if climb > 0.1 else 0.0

        if self.alt >= self._target_alt * 0.98:
            self.alt = self._target_alt
            self._vertical_rate = 0.0
            self._pitch = 0.0
            self._state = MissionState.NAVIGATING if self._waypoints else MissionState.HOVERING
            if self._waypoints:
                self._log_event("WAYPOINT_PHASE_START")

    # Glide slope for final approach (4 degrees — realistic for multirotor)
    _GLIDE_TAN = math.tan(math.radians(4.0))
    # Start decelerating this far from the landing waypoint
    _APPROACH_DECEL_M = 1200.0

    def _step_navigate(self, dt: float):
        if self._wp_idx >= len(self._waypoints):
            self._state = MissionState.LANDING
            return

        wp = self._waypoints[self._wp_idx]
        wp_lat = float(wp["lat"])
        wp_lon = float(wp["lng"])
        wp_alt = float(wp.get("altitude", 30))

        # The final waypoint is always the landing zone (altitude = 0)
        is_final = (self._wp_idx == len(self._waypoints) - 1) and wp_alt < 5.0

        dist = haversine(self.lat, self.lon, wp_lat, wp_lon)

        # ---- Altitude control -----------------------------------------------
        if is_final:
            # 4° glide slope: ideal altitude at this distance is dist * tan(4°).
            # If we're above the slope, descend at MAX_DESCENT to intercept it.
            # Once on it, maintain the geometrically required sink rate.
            glide_target = dist * self._GLIDE_TAN
            if self.alt > glide_target + 3.0:
                vrate = -self.MAX_DESCENT          # dive to intercept slope
            else:
                # On the slope: vrate = -groundspeed * tan(slope)
                vrate = max(-self.MAX_DESCENT, -self._groundspeed * self._GLIDE_TAN)
        else:
            alt_err = wp_alt - self.alt
            vrate = max(-self.MAX_DESCENT, min(self.MAX_CLIMB, alt_err * 0.5))

        self._vertical_rate = vrate
        self.alt = max(0.0, self.alt + vrate * dt)

        # ---- Waypoint reached -----------------------------------------------
        if dist <= self.WP_ACCEPT_M:
            self.alt = max(0.0, wp_alt)
            self._vertical_rate = 0.0
            self._log_event("WAYPOINT_REACHED", {"index": self._wp_idx})
            self._wp_idx += 1
            if self._wp_idx >= len(self._waypoints):
                self._state = MissionState.LANDING
            return

        # ---- Speed control --------------------------------------------------
        if is_final and dist < self._APPROACH_DECEL_M:
            # Smooth deceleration from cruise to ~3 m/s over the approach
            desired_spd = max(3.0, self._max_speed * (dist / self._APPROACH_DECEL_M))
        elif not is_final and dist < 60:
            # Slow down for intermediate waypoints
            desired_spd = max(5.0, dist / 60 * self._max_speed)
        else:
            desired_spd = self._max_speed

        if "WIND_SHEAR" in self._scenarios:
            desired_spd = max(1.0, desired_spd + random.uniform(-4, 4))

        spd_err = desired_spd - self._groundspeed
        self._groundspeed += math.copysign(min(abs(spd_err), self.ACCEL * dt), spd_err)
        self._groundspeed = max(0.0, self._groundspeed)

        # ---- Heading / attitude  (GPS state determines navigation accuracy) ---
        if "GPS_LOST" in self._scenarios:
            # ── Dead reckoning ──────────────────────────────────────────────
            # Autopilot loses its position reference entirely.
            # A consistent sideways drift accumulates — the aircraft stops
            # correcting toward the waypoint and slowly turns away.
            # The drift direction (left / right) is randomised once per event.
            if self._gps_lost_drift is None:
                self._gps_lost_drift = (random.choice([-1, 1])
                                        * random.uniform(0.12, 0.20))
            target_brg = (self._heading + self._gps_lost_drift
                          + random.gauss(0, 0.05)) % 360
            self._gps_fix  = 1
            self._gps_sats = random.randint(2, 4)
        else:
            # GPS_LOST cleared — reset drift so next event is fresh
            self._gps_lost_drift = None

            if "GPS_DEGRADED" in self._scenarios:
                # ── Noisy navigation ────────────────────────────────────────
                # Position estimate is off by ~20 m, so the computed bearing
                # to the waypoint is wrong — aircraft snakes around the route.
                target_brg = (initial_bearing(self.lat, self.lon, wp_lat, wp_lon)
                              + random.gauss(0, 12)) % 360
                self._gps_fix  = 2
                self._gps_sats = random.randint(4, 7)
            else:
                # ── Normal GPS ──────────────────────────────────────────────
                target_brg = initial_bearing(self.lat, self.lon, wp_lat, wp_lon)
                self._gps_fix  = 3
                self._gps_sats = random.randint(12, 16)

        turn = ((target_brg - self._heading + 540) % 360) - 180
        yaw_step = math.copysign(min(abs(turn), self.MAX_YAW_RATE * dt), turn)
        self._heading = (self._heading + yaw_step) % 360
        self._roll = math.copysign(min(abs(turn) * 0.35, 25), turn)
        # Pitch reflects forward speed; flares to nose-up on final approach
        if is_final and dist < self._APPROACH_DECEL_M:
            approach_frac = 1.0 - (dist / self._APPROACH_DECEL_M)
            self._pitch = -math.degrees(math.atan2(self._groundspeed * 0.12, 1.0)) * (1 - approach_frac)
        else:
            self._pitch = -math.degrees(math.atan2(self._groundspeed * 0.12, 1.0))

        # ---- Position update ------------------------------------------------
        # Physics always use the true heading — the drift IS the physics.
        # GPS state only affects how accurately the aircraft knows where to go.
        move_m = self._groundspeed * dt
        self.lat, self.lon = move_along_bearing(self.lat, self.lon, self._heading, move_m)

    def _step_hover(self, dt: float):
        self._groundspeed = max(0.0, self._groundspeed - self.ACCEL * dt)
        self._vertical_rate = 0.0
        self._pitch = max(-2.0, min(0.0, self._pitch + 1.5 * dt))
        self._roll = self._roll * max(0.0, 1 - 3 * dt)

    def _step_land(self, dt: float):
        # Decelerate horizontally to a stop while descending — keeps the aircraft
        # translating toward (or at) the LZ rather than dropping straight down
        self._groundspeed = max(0.0, self._groundspeed - self.ACCEL * 1.5 * dt)
        if self._groundspeed > 0.1:
            self.lat, self.lon = move_along_bearing(
                self.lat, self.lon, self._heading, self._groundspeed * dt
            )

        # Vertical descent: proportional at high alt, constant at low alt
        descent = min(self.MAX_DESCENT, max(0.5, self.alt * 0.4))
        self._vertical_rate = -descent
        self.alt = max(0.0, self.alt - descent * dt)

        # Flare: nose gradually levels out
        self._pitch = max(-2.0, self._pitch + 2.0 * dt)
        self._roll = self._roll * max(0.0, 1 - 2 * dt)

        if self.alt <= 0.05:
            self.alt = 0.0
            self.armed = False
            self.flight_mode = "STABILIZE"
            self._groundspeed = 0.0
            self._vertical_rate = 0.0
            self._pitch = 0.0
            self._roll = 0.0
            self._state = MissionState.COMPLETE
            self._log_event("LANDED")

    # ---- battery ----

    def _update_battery(self, dt: float):
        if not self.armed:
            self._bat_current = 0.0
            return
        s = self._state
        if s in (MissionState.TAKEOFF,):
            draw = self.CLIMB_A
        elif s == MissionState.NAVIGATING and self._groundspeed > 5:
            draw = self.CRUISE_A
        else:
            draw = self.IDLE_A

        if "BATTERY_WARNING" in self._scenarios:
            draw *= 1.6
        if "BATTERY_CRITICAL" in self._scenarios:
            draw *= 2.8

        self._bat_current = round(draw, 1)
        self._bat_mah_used += draw * (dt / 3600) * 1000
        level = max(0.0, 100.0 - (self._bat_mah_used / self.BATTERY_MAH * 100))
        self._bat_level = round(level, 1)
        # Linear model: 16.8 V at 100%, 14.0 V at 0%
        self._bat_voltage = round(14.0 + (level / 100) * 2.8, 2)

    # ---- helpers ----

    def _expire_scenarios(self):
        now = time.time()
        expired = [k for k, v in self._scenarios.items() if v is not None and now > v]
        for k in expired:
            del self._scenarios[k]
            self._log_event("SCENARIO_EXPIRED", {"type": k})

    def _snapshot(self) -> dict:
        elapsed = round(time.time() - self._session_start, 1) if self._session_start else 0.0
        return {
            "timestamp": round(time.time(), 3),
            "elapsed_s": elapsed,
            "lat": round(self.lat, 7),
            "lon": round(self.lon, 7),
            "alt": round(self.alt, 2),
            "groundspeed": round(self._groundspeed, 2),
            "vertical_rate": round(self._vertical_rate, 2),
            "heading": round(self._heading, 1),
            "pitch": round(self._pitch, 2),
            "roll": round(self._roll, 2),
            "yaw": round(self._heading, 1),
            "battery_voltage": self._bat_voltage,
            "battery_current": self._bat_current,
            "battery_level": self._bat_level,
            "gps_fix_type": self._gps_fix,
            "satellites_visible": self._gps_sats,
            "flight_mode": self.flight_mode,
            "armed": self.armed,
            "current_waypoint": self._wp_idx,
            "total_waypoints": len(self._waypoints),
            "mission_state": self._state.value,
            "active_scenarios": list(self._scenarios.keys()),
            "cruise_speed_ms":  self._max_speed,
            "traffic":          [tf.to_dict() for tf in self._traffic],
            "proximity_alerts": list(self._proximity.values()),
            "collision":        self._collision_info,
        }

    def _log_event(self, event_type: str, data: Optional[dict] = None):
        elapsed = round(time.time() - self._session_start, 1) if self._session_start else 0.0
        self.event_log.append({
            "timestamp": round(time.time(), 3),
            "elapsed_s": elapsed,
            "type": event_type,
            "data": data or {},
        })
        logger.debug("[sim] %s %s", event_type, data or "")

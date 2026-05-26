"""
AI traffic aircraft for the BVLOS training simulator.

Three aircraft fly fixed routes that cross the Atlanta BVLOS corridor.
Each TrainingSession gets its own traffic instances (independent state,
randomised starting positions) so sessions don't share state.

Geo functions are inlined to avoid circular imports with flight_sim.py.
"""
import math
import random


# ---------------------------------------------------------------------------
# Inline geo helpers (mirrors flight_sim.py)
# ---------------------------------------------------------------------------

def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    x = math.sin(dl) * math.cos(p2)
    y = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def _move(lat: float, lon: float, brg_deg: float, dist_m: float):
    R = 6_371_000.0
    ad = dist_m / R
    brg = math.radians(brg_deg)
    lat_r, lon_r = math.radians(lat), math.radians(lon)
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
# Traffic aircraft
# ---------------------------------------------------------------------------

class TrafficAircraft:
    _ACCEPT_M = 80.0  # waypoint acceptance radius

    def __init__(self, callsign: str, route: list, speed_ms: float,
                 alt_m: float, start_wp: int = 0):
        self.callsign = callsign
        self._route   = route
        self._speed   = speed_ms
        self.alt      = alt_m          # fixed cruise altitude (AGL)
        self._wp_idx  = start_wp % len(route)
        self.lat, self.lon = route[self._wp_idx]
        self.heading  = 0.0

    def step(self, dt: float):
        wp_lat, wp_lon = self._route[self._wp_idx]
        if _haversine(self.lat, self.lon, wp_lat, wp_lon) < self._ACCEPT_M:
            self._wp_idx = (self._wp_idx + 1) % len(self._route)
            wp_lat, wp_lon = self._route[self._wp_idx]
        self.heading = _bearing(self.lat, self.lon, wp_lat, wp_lon)
        self.lat, self.lon = _move(self.lat, self.lon, self.heading, self._speed * dt)

    def to_dict(self) -> dict:
        return {
            "callsign": self.callsign,
            "lat":      round(self.lat, 6),
            "lon":      round(self.lon, 6),
            "alt":      self.alt,
            "heading":  round(self.heading, 1),
        }


# ---------------------------------------------------------------------------
# Pre-defined routes
#
# Routes are designed to cross the typical trainee corridor
# (Home 33.808,-84.374  →  LZ 33.856,-84.216) at different altitudes
# and headings, creating realistic encounter geometry.
# ---------------------------------------------------------------------------

_ROUTES = [
    {
        # Alpha: E-W shuttle at 75 m, crosses mid-corridor
        "callsign": "N471AX",
        "route":    [(33.832, -84.455), (33.832, -84.190), (33.832, -84.455)],
        "speed_ms": 48.0,
        "alt_m":    75.0,
    },
    {
        # Bravo: N-S shuttle at 58 m, cuts across the corridor
        "callsign": "N882BV",
        "route":    [(33.755, -84.305), (33.920, -84.305), (33.755, -84.305)],
        "speed_ms": 42.0,
        "alt_m":    58.0,
    },
    {
        # Charlie: diagonal NW→SE at 92 m, roughly parallels the main route
        # but offset — creates an overtake / crossing scenario
        "callsign": "N339CX",
        "route":    [(33.782, -84.438), (33.878, -84.170), (33.782, -84.438)],
        "speed_ms": 54.0,
        "alt_m":    92.0,
    },
]


def make_traffic() -> list:
    """Return fresh TrafficAircraft instances with randomised starting positions."""
    return [
        TrafficAircraft(
            callsign=cfg["callsign"],
            route=cfg["route"],
            speed_ms=cfg["speed_ms"],
            alt_m=cfg["alt_m"],
            start_wp=random.randint(0, len(cfg["route"]) - 1),
        )
        for cfg in _ROUTES
    ]

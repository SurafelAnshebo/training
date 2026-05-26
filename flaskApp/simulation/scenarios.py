from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ScenarioDefinition:
    name: str
    label: str
    description: str
    default_duration_s: Optional[int]  # None = permanent until cleared
    severity: str  # "info" | "warning" | "critical"
    icon: str


SCENARIOS: dict[str, ScenarioDefinition] = {
    "GPS_DEGRADED": ScenarioDefinition(
        name="GPS_DEGRADED",
        label="GPS Degraded",
        description="Signal quality drops — position noise increases, fewer satellites.",
        default_duration_s=60,
        severity="warning",
        icon="🛰️",
    ),
    "GPS_LOST": ScenarioDefinition(
        name="GPS_LOST",
        label="GPS Lost",
        description="Complete GPS loss — autonomous navigation unavailable. Trainee must initiate RTL.",
        default_duration_s=30,
        severity="critical",
        icon="📡",
    ),
    "WIND_SHEAR": ScenarioDefinition(
        name="WIND_SHEAR",
        label="Wind Shear",
        description="Strong wind shear encountered — groundspeed fluctuates unpredictably.",
        default_duration_s=90,
        severity="warning",
        icon="💨",
    ),
    "BATTERY_WARNING": ScenarioDefinition(
        name="BATTERY_WARNING",
        label="Battery Warning",
        description="Elevated power draw — accelerated battery drain simulates degraded cell.",
        default_duration_s=None,
        severity="warning",
        icon="🔋",
    ),
    "BATTERY_CRITICAL": ScenarioDefinition(
        name="BATTERY_CRITICAL",
        label="Battery Critical",
        description="Critical battery state — immediate landing required per BVLOS procedures.",
        default_duration_s=None,
        severity="critical",
        icon="⚡",
    ),
    "COMMS_DEGRADED": ScenarioDefinition(
        name="COMMS_DEGRADED",
        label="Comms Degraded",
        description="C2 link degraded — telemetry updates become sporadic.",
        default_duration_s=60,
        severity="warning",
        icon="📻",
    ),
    "TFR_POPUP": ScenarioDefinition(
        name="TFR_POPUP",
        label="TFR Activated",
        description="New Temporary Flight Restriction overlaps planned route — trainee must reroute.",
        default_duration_s=None,
        severity="critical",
        icon="🚫",
    ),
    "OBSTACLE_DETECTED": ScenarioDefinition(
        name="OBSTACLE_DETECTED",
        label="Obstacle Detected",
        description="Detect-and-avoid system reports obstacle on current heading.",
        default_duration_s=None,
        severity="critical",
        icon="⚠️",
    ),
}


def get_scenario_catalog() -> list[dict]:
    return [
        {
            "name": s.name,
            "label": s.label,
            "description": s.description,
            "default_duration_s": s.default_duration_s,
            "severity": s.severity,
            "icon": s.icon,
        }
        for s in SCENARIOS.values()
    ]

"""
Post-flight scoring engine.

Criteria (weighted total out of 100):
  30% Mission completion  — did they reach all waypoints?
  20% Altitude compliance — did they maintain planned altitude (±15%)?
  25% Emergency response  — how quickly did they act on injected scenarios?
  15% Battery management  — did they respond to critical battery?
  10% Landing accuracy    — how close to the planned landing point?
"""
import math
import logging
from typing import Optional

logger = logging.getLogger(__name__)

WEIGHTS = {
    "mission_completion": 30,
    "altitude_compliance": 20,
    "emergency_response": 25,
    "battery_management": 15,
    "landing_accuracy": 10,
}


def score_flight(
    flight_log: list[dict],
    event_log: list[dict],
    planned_waypoints: list[dict],
) -> dict:
    if not flight_log:
        return {"score": 0, "grade": "F", "criteria": {}, "summary": "No flight data."}

    criteria = {
        "mission_completion": _score_completion(flight_log, planned_waypoints),
        "altitude_compliance": _score_altitude(flight_log, planned_waypoints),
        "emergency_response": _score_emergency(event_log),
        "battery_management": _score_battery(flight_log, event_log),
        "landing_accuracy": _score_landing(flight_log, planned_waypoints),
    }

    total_weight = sum(WEIGHTS.values())
    score = sum(criteria[k]["points"] * WEIGHTS[k] / total_weight for k in criteria)
    score = round(score, 1)

    return {
        "score": score,
        "grade": _grade(score),
        "criteria": criteria,
        "weights": WEIGHTS,
        "flight_duration_s": flight_log[-1]["elapsed_s"],
        "waypoints_reached": criteria["mission_completion"].get("waypoints_reached", 0),
        "total_waypoints": len(planned_waypoints),
    }


def _grade(score: float) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"


def _score_completion(log: list[dict], waypoints: list[dict]) -> dict:
    final = log[-1]
    wp_reached = final.get("current_waypoint", 0)
    total = final.get("total_waypoints", len(waypoints))
    completed = final.get("mission_state") == "COMPLETE"

    if completed:
        points = 100
    elif total > 0:
        points = round((wp_reached / total) * 75)
    else:
        points = 0

    return {
        "points": points,
        "waypoints_reached": wp_reached,
        "total_waypoints": total,
        "completed": completed,
        "label": "Mission Completion",
    }


def _score_altitude(log: list[dict], waypoints: list[dict]) -> dict:
    if not waypoints:
        return {"points": 100, "label": "Altitude Compliance", "detail": "No waypoints"}

    violations = 0
    checks = 0
    for entry in log:
        if entry.get("mission_state") not in ("NAVIGATING", "TAKEOFF"):
            continue
        idx = min(entry.get("current_waypoint", 0), len(waypoints) - 1)
        target = float(waypoints[idx].get("altitude", 30))
        if target <= 0:
            continue
        err_pct = abs(entry["alt"] - target) / target
        if err_pct > 0.15:
            violations += 1
        checks += 1

    if checks == 0:
        return {"points": 100, "label": "Altitude Compliance", "detail": "No checks"}

    compliance = 1 - (violations / checks)
    return {
        "points": round(compliance * 100),
        "label": "Altitude Compliance",
        "violation_pct": round((violations / checks) * 100, 1),
        "total_checks": checks,
    }


def _score_emergency(events: list[dict]) -> dict:
    injections = [e for e in events if e["type"] == "SCENARIO_INJECTED"]
    if not injections:
        return {"points": 100, "label": "Emergency Response", "detail": "No scenarios injected"}

    response_actions = [e for e in events if e["type"] in ("HOVER", "LAND_COMMANDED", "RESUME")]
    response_times = []

    for inj in injections:
        t0 = inj["elapsed_s"]
        later = [r["elapsed_s"] for r in response_actions if r["elapsed_s"] > t0]
        if later:
            response_times.append(min(later) - t0)

    if not response_times:
        return {
            "points": 20,
            "label": "Emergency Response",
            "detail": "No response detected",
            "scenarios_injected": len(injections),
        }

    avg_rt = sum(response_times) / len(response_times)
    if avg_rt <= 10:
        points = 100
    elif avg_rt <= 30:
        points = round(100 - (avg_rt - 10) * 2.5)
    elif avg_rt <= 60:
        points = round(50 - (avg_rt - 30) * 0.83)
    else:
        points = max(0, 25)

    return {
        "points": points,
        "label": "Emergency Response",
        "scenarios_injected": len(injections),
        "responses_recorded": len(response_times),
        "avg_response_time_s": round(avg_rt, 1),
    }


def _score_battery(log: list[dict], events: list[dict]) -> dict:
    final = log[-1]
    final_level = final.get("battery_level", 100)

    critical_injections = [
        e for e in events
        if e["type"] == "SCENARIO_INJECTED" and e.get("data", {}).get("type") == "BATTERY_CRITICAL"
    ]
    land_events = [e for e in events if e["type"] == "LAND_COMMANDED"]

    if critical_injections and land_events:
        crit_t = critical_injections[0]["elapsed_s"]
        after_land = [e["elapsed_s"] for e in land_events if e["elapsed_s"] >= crit_t]
        if after_land:
            rt = min(after_land) - crit_t
            if rt <= 20:
                points = 100
            elif rt <= 120:
                points = round(100 - (rt / 120) * 60)
            else:
                points = 20
        else:
            points = 5
    elif critical_injections:
        points = 5  # critical battery and no land command
    else:
        if final_level >= 20:
            points = 100
        elif final_level >= 10:
            points = 70
        else:
            points = 40

    return {
        "points": points,
        "label": "Battery Management",
        "final_battery_level": final_level,
    }


def _score_landing(log: list[dict], waypoints: list[dict]) -> dict:
    if not waypoints or log[-1].get("mission_state") != "COMPLETE":
        return {"points": 0, "label": "Landing Accuracy", "detail": "Mission not completed"}

    last_wp = waypoints[-1]
    final = log[-1]
    dlat = (final["lat"] - float(last_wp["lat"])) * 111_320
    dlon = (final["lon"] - float(last_wp["lng"])) * 111_320 * math.cos(math.radians(final["lat"]))
    dist = math.sqrt(dlat ** 2 + dlon ** 2)

    if dist <= 5:
        points = 100
    elif dist <= 25:
        points = round(100 - (dist - 5) * 3.5)
    elif dist <= 60:
        points = round(30 - (dist - 25) * 0.5)
    else:
        points = 0

    return {
        "points": max(0, points),
        "label": "Landing Accuracy",
        "landing_error_m": round(dist, 1),
    }

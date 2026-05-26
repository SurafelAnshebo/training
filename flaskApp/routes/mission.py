import logging
from flask import Blueprint, request, jsonify, current_app
from flaskApp.session_manager import SessionManager
from flaskApp.simulation.curriculum import MISSIONS_BY_ID

logger = logging.getLogger(__name__)
bp = Blueprint("mission", __name__)


def _session_or_404(session_id: str):
    mgr: SessionManager = current_app.session_manager
    s = mgr.get(session_id)
    if s is None:
        return None, (jsonify({"error": "Session not found"}), 404)
    return s, None


@bp.route("/api/session", methods=["POST"])
def create_session():
    data = request.get_json(force=True) or {}
    name = (data.get("trainee_name") or "Trainee").strip()
    home_lat = float(data.get("home_lat", current_app.config["DEFAULT_HOME_LAT"]))
    home_lon = float(data.get("home_lon", current_app.config["DEFAULT_HOME_LON"]))
    try:
        mgr: SessionManager = current_app.session_manager
        session = mgr.create(name, home_lat, home_lon)
        return jsonify({"session_id": session.session_id, "trainee_name": name}), 201
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 503


@bp.route("/api/session/<session_id>", methods=["DELETE"])
def end_session(session_id: str):
    mgr: SessionManager = current_app.session_manager
    mgr.destroy(session_id)
    return jsonify({"message": "Session ended"}), 200


@bp.route("/api/session/<session_id>/waypoints", methods=["POST"])
def save_waypoints(session_id: str):
    session, err = _session_or_404(session_id)
    if err:
        return err
    waypoints = (request.get_json(force=True) or {}).get("coordinates", [])
    if not waypoints:
        return jsonify({"error": "No waypoints provided"}), 400
    session.planned_waypoints = waypoints
    return jsonify({"message": "Waypoints saved", "count": len(waypoints)}), 200


@bp.route("/api/session/<session_id>/launch", methods=["POST"])
def launch_mission(session_id: str):
    session, err = _session_or_404(session_id)
    if err:
        return err
    data = request.get_json(force=True) or {}
    waypoints = data.get("coordinates", [])
    if not waypoints:
        return jsonify({"error": "No waypoints"}), 400
    if any(float(wp.get("altitude", 0)) <= 0 for wp in waypoints[:-1]):
        return jsonify({"error": "All waypoints except the last must have altitude > 0"}), 400
    speed_ms = data.get("speed_ms")
    mission_id = data.get("mission_id")
    mission = MISSIONS_BY_ID.get(mission_id) if mission_id else None
    scenario_events = mission["events"] if mission else []

    try:
        session.planned_waypoints = waypoints
        session.mission_id = mission_id
        session.sim.arm()
        session.sim.start_mission(
            waypoints,
            speed_ms=float(speed_ms) if speed_ms else None,
            scenario_events=scenario_events,
        )
        return jsonify({"message": "Mission started", "cruise_speed_ms": session.sim._max_speed}), 200
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 409


@bp.route("/api/session/<session_id>/hover", methods=["POST"])
def hover(session_id: str):
    session, err = _session_or_404(session_id)
    if err:
        return err
    session.sim.hover()
    return jsonify({"message": "Hover engaged"}), 200


@bp.route("/api/session/<session_id>/resume", methods=["POST"])
def resume(session_id: str):
    session, err = _session_or_404(session_id)
    if err:
        return err
    session.sim.resume()
    return jsonify({"message": "Resumed"}), 200


@bp.route("/api/session/<session_id>/land", methods=["POST"])
def land(session_id: str):
    session, err = _session_or_404(session_id)
    if err:
        return err
    session.sim.land()
    return jsonify({"message": "Landing initiated"}), 200


@bp.route("/api/session/<session_id>/rtl", methods=["POST"])
def rtl(session_id: str):
    session, err = _session_or_404(session_id)
    if err:
        return err
    session.sim.rtl()
    return jsonify({"message": "RTL initiated"}), 200


@bp.route("/api/session/<session_id>/abort", methods=["POST"])
def abort(session_id: str):
    session, err = _session_or_404(session_id)
    if err:
        return err
    session.sim.abort()
    return jsonify({"message": "Mission aborted"}), 200


@bp.route("/api/session/<session_id>/telemetry", methods=["GET"])
def telemetry(session_id: str):
    session, err = _session_or_404(session_id)
    if err:
        return err
    return jsonify(session.sim.get_telemetry()), 200

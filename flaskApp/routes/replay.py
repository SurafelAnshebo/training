import logging
from flask import Blueprint, jsonify, current_app
from flaskApp.session_manager import SessionManager
from flaskApp.scoring.scorer import score_flight

logger = logging.getLogger(__name__)
bp = Blueprint("replay", __name__)


@bp.route("/api/session/<session_id>/debrief")
def debrief(session_id: str):
    mgr: SessionManager = current_app.session_manager
    session = mgr.get(session_id)
    if session is None:
        return jsonify({"error": "Session not found"}), 404

    score = score_flight(
        session.sim.flight_log,
        session.sim.event_log,
        session.planned_waypoints,
    )
    return jsonify({
        "score": score,
        "event_log": session.sim.event_log,
        "session": session.to_dict(),
    }), 200


@bp.route("/api/session/<session_id>/flight_log")
def flight_log(session_id: str):
    mgr: SessionManager = current_app.session_manager
    session = mgr.get(session_id)
    if session is None:
        return jsonify({"error": "Session not found"}), 404

    log = session.sim.flight_log
    # Downsample: keep every other record if large, for efficient replay
    replay = log[::2] if len(log) > 400 else log
    return jsonify({
        "flight_log": replay,
        "total_records": len(log),
        "planned_waypoints": session.planned_waypoints,
    }), 200

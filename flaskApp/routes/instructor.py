import logging
from flask import Blueprint, request, jsonify, render_template, current_app
from flaskApp.extensions import socketio
from flaskApp.session_manager import SessionManager
from flaskApp.simulation.scenarios import SCENARIOS, get_scenario_catalog

logger = logging.getLogger(__name__)
bp = Blueprint("instructor", __name__)


@bp.route("/instructor")
def dashboard():
    return render_template("instructor.html")


@bp.route("/instructor/sessions")
def list_sessions():
    mgr: SessionManager = current_app.session_manager
    return jsonify({"sessions": mgr.all_sessions()}), 200


@bp.route("/instructor/scenarios")
def scenario_catalog():
    return jsonify({"scenarios": get_scenario_catalog()}), 200


@bp.route("/instructor/session/<session_id>/inject", methods=["POST"])
def inject_scenario(session_id: str):
    mgr: SessionManager = current_app.session_manager
    session = mgr.get(session_id)
    if session is None:
        return jsonify({"error": "Session not found"}), 404

    data = request.get_json(force=True) or {}
    scenario_type = data.get("type")
    duration = data.get("duration_s")

    if scenario_type not in SCENARIOS:
        return jsonify({"error": f"Unknown scenario: {scenario_type}"}), 400

    session.sim.inject_scenario(scenario_type, float(duration) if duration else None)

    defn = SCENARIOS[scenario_type]
    socketio.emit(
        "scenario_injected",
        {
            "type": scenario_type,
            "label": defn.label,
            "description": defn.description,
            "severity": defn.severity,
            "icon": defn.icon,
            "duration_s": duration,
        },
        to=f"session:{session_id}",
    )
    logger.info("Scenario %s injected into session %s", scenario_type, session_id)
    return jsonify({"message": f"Scenario {scenario_type} injected"}), 200


@bp.route("/instructor/session/<session_id>/clear", methods=["POST"])
def clear_scenario(session_id: str):
    mgr: SessionManager = current_app.session_manager
    session = mgr.get(session_id)
    if session is None:
        return jsonify({"error": "Session not found"}), 404

    scenario_type = (request.get_json(force=True) or {}).get("type")
    if not scenario_type:
        return jsonify({"error": "type required"}), 400

    session.sim.clear_scenario(scenario_type)
    socketio.emit("scenario_cleared", {"type": scenario_type}, to=f"session:{session_id}")
    return jsonify({"message": "Scenario cleared"}), 200

"""
SocketIO event handlers.

Trainee flow:
  1. emit join_session {session_id}  → joins room "session:<id>"
  2. server starts pushing telemetry at TELEMETRY_HZ to that room

Instructor flow:
  1. emit join_instructor  → joins room "instructor"
  2. receives session_update every telemetry tick
"""
import time
import logging
from flask import request
from flask_socketio import join_room
from flaskApp.extensions import socketio
from flaskApp.simulation.scenarios import SCENARIOS

logger = logging.getLogger(__name__)

# Tracks which session rooms already have an active telemetry push
_active_pushes: set[str] = set()


@socketio.on("join_session")
def on_join_session(data):
    from flask import current_app
    session_id = (data or {}).get("session_id", "")
    mgr = current_app.session_manager
    session = mgr.get(session_id)
    if session is None:
        socketio.emit("error", {"message": "Session not found"}, to=request.sid)
        return

    room = f"session:{session_id}"
    join_room(room)
    socketio.emit("joined", {"session_id": session_id}, to=request.sid)

    if room not in _active_pushes:
        _active_pushes.add(room)
        app = current_app._get_current_object()
        socketio.start_background_task(_push_telemetry, app, session_id, room)
        logger.debug("Telemetry push started for %s", room)


@socketio.on("join_instructor")
def on_join_instructor():
    join_room("instructor")
    socketio.emit("joined", {"role": "instructor"}, to=request.sid)


@socketio.on("disconnect")
def on_disconnect():
    logger.debug("Client %s disconnected", request.sid)


def _push_telemetry(app, session_id: str, room: str):
    """Background task: push telemetry to room and overview to instructor.

    Also detects newly active scenarios (from auto-injection by the scenario
    script) and emits scenario_injected so the trainee receives the alert in
    real time — exactly as if the instructor had clicked the button.
    """
    hz = app.config.get("TELEMETRY_HZ", 2)
    interval = 1.0 / hz
    prev_scenarios: set[str] = set()

    with app.app_context():
        mgr = app.session_manager
        while True:
            session = mgr.get(session_id)
            if session is None:
                _active_pushes.discard(room)
                break

            telemetry = session.sim.get_telemetry()
            socketio.emit("telemetry", telemetry, to=room)
            socketio.emit("session_update", session.to_dict(), to="instructor")

            # Detect newly active scenarios and notify trainee
            current_scenarios = set(telemetry["active_scenarios"])
            for s_type in current_scenarios - prev_scenarios:
                defn = SCENARIOS.get(s_type)
                if defn:
                    socketio.emit("scenario_injected", {
                        "type": s_type,
                        "label": defn.label,
                        "description": defn.description,
                        "severity": defn.severity,
                        "icon": defn.icon,
                        "duration_s": None,
                        "auto": True,
                    }, to=room)
            prev_scenarios = current_scenarios

            if telemetry["mission_state"] == "CRASHED":
                socketio.emit("aircraft_crashed", telemetry, to=room)
                _active_pushes.discard(room)
                break

            if telemetry["mission_state"] in ("COMPLETE", "ABORTED"):
                socketio.emit("mission_complete", telemetry, to=room)
                _active_pushes.discard(room)
                break

            socketio.sleep(interval)

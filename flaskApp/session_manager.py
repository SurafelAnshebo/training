import uuid
import time
import logging
from typing import Optional
from flaskApp.simulation.flight_sim import FlightSimulator

logger = logging.getLogger(__name__)


class TrainingSession:
    def __init__(self, session_id: str, trainee_name: str, home_lat: float, home_lon: float):
        self.session_id = session_id
        self.trainee_name = trainee_name
        self.created_at = time.time()
        self.planned_waypoints: list[dict] = []

        self.mission_id: Optional[str] = None
        self.sim = FlightSimulator(home_lat, home_lon)
        self.sim.start()
        logger.info("Session %s started for %s", session_id, trainee_name)

    def to_dict(self) -> dict:
        t = self.sim.get_telemetry()
        return {
            "session_id": self.session_id,
            "trainee_name": self.trainee_name,
            "mission_id": self.mission_id,
            "created_at": round(self.created_at),
            "mission_state": t["mission_state"],
            "battery_level": t["battery_level"],
            "alt": t["alt"],
            "groundspeed": t["groundspeed"],
            "heading": t["heading"],
            "active_scenarios": t["active_scenarios"],
            "elapsed_s": t["elapsed_s"],
            "current_waypoint": t["current_waypoint"],
            "total_waypoints": t["total_waypoints"],
        }


class SessionManager:
    def __init__(self, max_sessions: int = 20):
        self._sessions: dict[str, TrainingSession] = {}
        self._max = max_sessions

    def create(self, trainee_name: str, home_lat: float, home_lon: float) -> TrainingSession:
        if len(self._sessions) >= self._max:
            raise RuntimeError("Maximum concurrent sessions reached")
        sid = str(uuid.uuid4())[:8].upper()
        session = TrainingSession(sid, trainee_name, home_lat, home_lon)
        self._sessions[sid] = session
        return session

    def get(self, session_id: str) -> Optional[TrainingSession]:
        return self._sessions.get(session_id)

    def destroy(self, session_id: str):
        session = self._sessions.pop(session_id, None)
        if session:
            session.sim.stop()
            logger.info("Session %s destroyed", session_id)

    def all_sessions(self) -> list[dict]:
        return [s.to_dict() for s in self._sessions.values()]

    def __len__(self) -> int:
        return len(self._sessions)

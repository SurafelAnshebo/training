"""
Application factory.

Usage:
    From BVLOS/:  python run.py
    With Flask:   FLASK_APP=flaskApp.app:create_app flask run
"""
import logging
from flask import Flask
from flaskApp.config import Config
from flaskApp.extensions import socketio
from flaskApp.session_manager import SessionManager


def create_app(config_class=Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)

    logging.basicConfig(
        level=getattr(logging, app.config.get("LOG_LEVEL", "INFO")),
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )

    # threading mode: no monkey-patching required, works with standard Python threads
    socketio.init_app(app, cors_allowed_origins="*", async_mode="threading")

    app.session_manager = SessionManager(app.config["MAX_SESSIONS"])

    # Blueprints
    from flaskApp.routes.main import bp as main_bp
    from flaskApp.routes.mission import bp as mission_bp
    from flaskApp.routes.instructor import bp as instructor_bp
    from flaskApp.routes.replay import bp as replay_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(mission_bp)
    app.register_blueprint(instructor_bp)
    app.register_blueprint(replay_bp)

    # SocketIO event handlers (import registers decorators)
    from flaskApp.socket_events import flight_events  # noqa: F401

    return app

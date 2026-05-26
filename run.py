"""
Entry point. Run from BVLOS/ with:
    python run.py
"""
from flaskApp.extensions import socketio
from flaskApp.app import create_app

app = create_app()

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=False, use_reloader=False,
                 allow_unsafe_werkzeug=True)

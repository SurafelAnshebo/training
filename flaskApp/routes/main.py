from flask import Blueprint, render_template, jsonify, current_app
from flaskApp.simulation.curriculum import get_catalog

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    cfg = current_app.config
    return render_template(
        "index.html",
        home_lat=cfg["DEFAULT_HOME_LAT"],
        home_lon=cfg["DEFAULT_HOME_LON"],
        landing_lat=cfg["DEFAULT_LANDING_LAT"],
        landing_lon=cfg["DEFAULT_LANDING_LON"],
    )


@bp.route("/api/curriculum")
def curriculum():
    return jsonify({"missions": get_catalog()}), 200

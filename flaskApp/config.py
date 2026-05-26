import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-change-in-production")
    MAX_SESSIONS = int(os.environ.get("MAX_SESSIONS", "20"))

    DEFAULT_HOME_LAT = float(os.environ.get("HOME_LAT", "33.807607"))
    DEFAULT_HOME_LON = float(os.environ.get("HOME_LON", "-84.373981"))
    DEFAULT_LANDING_LAT = float(os.environ.get("LANDING_LAT", "33.856192"))
    DEFAULT_LANDING_LON = float(os.environ.get("LANDING_LON", "-84.216326"))

    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    TELEMETRY_HZ = float(os.environ.get("TELEMETRY_HZ", "2"))

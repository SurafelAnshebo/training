"""
BVLOS Pilot Training Curriculum

Six progressive missions built around the core BVLOS competency framework:
  Situational Awareness · Emergency Response · Decision-Making Under Pressure

Each mission has:
  - A realistic operational narrative (context matters for training)
  - Specific learning objectives tied to BVLOS procedures
  - Scripted timed events that fire automatically during flight
  - A pre-flight checklist the pilot must acknowledge
  - A pass score threshold that unlocks the next mission

Progression: missions unlock sequentially. A pilot must score >= pass_score
before the next mission is accessible.
"""

MISSIONS: list[dict] = [

    {
        "id": "m01_basic",
        "title": "Mission 01",
        "subtitle": "Basic Navigation",
        "level": 1,
        "difficulty": "Introductory",
        "color": "#22c55e",
        "duration_est": "8–12 min",
        "pass_score": 60,

        "narrative": (
            "You are the Remote PIC for a routine infrastructure inspection along a "
            "linear corridor between two substations. Weather is clear, winds are calm, "
            "and no airspace conflicts are active. This is your opportunity to get "
            "comfortable with the ground control station, plan a safe route, and execute "
            "a textbook BVLOS flight."
        ),

        "objectives": [
            "Plan a safe route from the takeoff point to the landing zone",
            "Set appropriate altitude for each waypoint (recommend 60–100 m AGL)",
            "Execute the mission and land within the designated LZ",
            "Monitor telemetry throughout — altitude, speed, battery, and GPS",
        ],

        "weather": {
            "wind": "Calm (< 5 kt)",
            "visibility": "10 SM",
            "sky": "Clear",
            "temperature": "22 °C",
            "density_altitude": "Standard",
        },

        "notams": [
            "TFR active within 3 NM of stadium — avoid marked red circle on map",
            "Airport traffic pattern in effect — stay clear of airport markers",
        ],

        "checklist": [
            "Airspace reviewed — no conflicts on planned route",
            "Weather briefing obtained — conditions within limits",
            "Lost-link procedure reviewed and briefed",
            "Emergency landing sites identified along route",
            "Battery charged and voltage verified",
        ],

        # No auto-injected events — clean introduction flight
        "events": [],
    },

    {
        "id": "m02_wind",
        "title": "Mission 02",
        "subtitle": "Wind Shear Encounter",
        "level": 2,
        "difficulty": "Beginner",
        "color": "#3b82f6",
        "duration_est": "10–15 min",
        "pass_score": 65,

        "narrative": (
            "A cold front is moving through the Atlanta corridor. Surface winds are "
            "acceptable for launch but upper-level wind shear has been reported by "
            "manned aircraft in the area. You are cleared to proceed with the mission "
            "but must maintain heightened situational awareness. Expect groundspeed "
            "fluctuations and be prepared to adjust your ETA. Do NOT exceed your "
            "approved corridor."
        ),

        "objectives": [
            "Recognise wind shear onset from groundspeed telemetry",
            "Maintain situational awareness — track actual vs. planned groundspeed",
            "Do NOT command hover unless safety is threatened (score penalty)",
            "Complete the mission despite adverse wind conditions",
        ],

        "weather": {
            "wind": "Surface: 12 kt from 270° / Upper: Wind shear reported",
            "visibility": "7 SM",
            "sky": "Few 3,500 ft",
            "temperature": "18 °C",
            "density_altitude": "Near standard",
        },

        "notams": [
            "PIREPs report moderate wind shear 300–600 ft AGL",
            "TFR active within 3 NM of stadium",
        ],

        "checklist": [
            "Wind shear PIREP reviewed and acknowledged",
            "Groundspeed monitoring plan established",
            "Alternate route identified in case of RPA excursion",
            "Lost-link procedure reviewed",
            "Battery charged and voltage verified",
        ],

        "events": [
            {"at_s": 40,  "type": "WIND_SHEAR",   "duration_s": 70},
            {"at_s": 140, "type": "WIND_SHEAR",   "duration_s": 50},
        ],
    },

    {
        "id": "m03_gps",
        "title": "Mission 03",
        "subtitle": "GPS Anomaly",
        "level": 3,
        "difficulty": "Intermediate",
        "color": "#f59e0b",
        "duration_est": "10–15 min",
        "pass_score": 70,

        "narrative": (
            "GPS jamming has been reported in the area by other RPA operators. "
            "You are the Remote PIC and have accepted the mission after assessing "
            "the risk. Your aircraft is equipped with an inertial back-up, but "
            "position accuracy will degrade significantly during the event. "
            "Per your operations manual: if GPS fix drops to 2D or below, "
            "you must HOVER and assess before continuing. If GPS is lost entirely, "
            "initiate LAND immediately."
        ),

        "objectives": [
            "Detect GPS degradation from the satellite count and fix-type telemetry",
            "HOVER when fix drops to 2D — do not continue navigating blind",
            "LAND immediately if GPS is fully lost",
            "Resume flight only after GPS is confirmed restored (3D fix, ≥ 8 satellites)",
        ],

        "weather": {
            "wind": "8 kt from 220°",
            "visibility": "10 SM",
            "sky": "Scattered 5,000 ft",
            "temperature": "20 °C",
            "density_altitude": "Near standard",
        },

        "notams": [
            "GPS jamming reported by multiple operators in Atlanta corridor",
            "TFR active within 3 NM of stadium",
            "Recommend enhanced situational awareness procedures",
        ],

        "checklist": [
            "GPS jamming NOTAM reviewed and risk accepted",
            "GPS degraded / lost-link procedures reviewed",
            "Alternate navigation reference identified (visual landmarks)",
            "HOVER and LAND button locations confirmed on GCS",
            "Battery charged and voltage verified",
        ],

        "events": [
            {"at_s": 55,  "type": "GPS_DEGRADED", "duration_s": 40},
            {"at_s": 100, "type": "GPS_LOST",      "duration_s": 25},
            {"at_s": 130, "type": "GPS_DEGRADED", "duration_s": 30},
        ],
    },

    {
        "id": "m04_battery",
        "title": "Mission 04",
        "subtitle": "Battery Emergency",
        "level": 4,
        "difficulty": "Intermediate",
        "color": "#f59e0b",
        "duration_est": "12–18 min",
        "pass_score": 70,

        "narrative": (
            "En route, your battery management system reports a cell imbalance. "
            "Power draw is higher than expected. You will receive a BATTERY WARNING "
            "alert — at that point you have a decision: continue to the nearest "
            "pre-approved emergency landing site, or return to home. "
            "If a BATTERY CRITICAL alert fires, your operations manual is unambiguous: "
            "LAND IMMEDIATELY at the nearest safe location. There is no other option."
        ),

        "objectives": [
            "Monitor battery % and voltage continuously",
            "On BATTERY WARNING: assess remaining range vs. distance to LZ",
            "Make and communicate a land-or-continue decision within 20 seconds",
            "On BATTERY CRITICAL: initiate LAND within 15 seconds — no exceptions",
        ],

        "weather": {
            "wind": "10 kt from 250°",
            "visibility": "10 SM",
            "sky": "Clear",
            "temperature": "25 °C",
            "density_altitude": "Slightly elevated",
        },

        "notams": [
            "TFR active within 3 NM of stadium",
            "Designated emergency landing sites: home base and LZ only",
        ],

        "checklist": [
            "Battery fully charged — voltage verified at pre-flight",
            "Emergency landing site locations memorised",
            "Battery warning and critical thresholds reviewed",
            "LAND button location confirmed on GCS",
            "Decision criteria for land-vs-continue documented in flight plan",
        ],

        "events": [
            {"at_s": 75,  "type": "BATTERY_WARNING",  "duration_s": None},
            {"at_s": 150, "type": "BATTERY_CRITICAL",  "duration_s": None},
        ],
    },

    {
        "id": "m05_airspace",
        "title": "Mission 05",
        "subtitle": "Dynamic Airspace Conflict",
        "level": 5,
        "difficulty": "Advanced",
        "color": "#ef4444",
        "duration_est": "15–20 min",
        "pass_score": 75,

        "narrative": (
            "Mid-mission, ATC activates an emergency TFR that intersects your approved "
            "corridor. Simultaneously, your detect-and-avoid system reports an obstacle "
            "on your current heading. You cannot proceed on the planned route. "
            "You must HOVER, assess both conflicts, and make a rapid rerouting decision. "
            "Remember: you are the Remote PIC — ATC compliance and collision avoidance "
            "are your legal responsibility. Document every decision."
        ),

        "objectives": [
            "Immediately HOVER when the TFR is activated",
            "Assess the new TFR boundary and the obstacle location on the map",
            "Plan and execute a safe reroute that avoids both conflicts",
            "Resume and complete the mission or elect a safe abort with justification",
        ],

        "weather": {
            "wind": "12 kt from 280°",
            "visibility": "6 SM (haze)",
            "sky": "Broken 4,500 ft",
            "temperature": "28 °C",
            "density_altitude": "Elevated",
        },

        "notams": [
            "DYNAMIC TFR may be activated without notice — monitor ATC",
            "Obstacle reported at GPS corridor — exact position uncertain",
            "TFR active within 3 NM of stadium",
        ],

        "checklist": [
            "ATC frequencies monitored and current",
            "Rerouting authority pre-approved with flight operations manager",
            "Obstacle avoidance system (DAA) armed and tested",
            "HOVER procedure confirmed — know where the button is",
            "Abort criteria established — document in flight plan",
        ],

        "events": [
            {"at_s": 50,  "type": "TFR_POPUP",          "duration_s": None},
            {"at_s": 80,  "type": "OBSTACLE_DETECTED",  "duration_s": None},
            {"at_s": 120, "type": "WIND_SHEAR",          "duration_s": 60},
        ],
    },

    {
        "id": "m06_multi",
        "title": "Mission 06",
        "subtitle": "Multi-System Failure",
        "level": 6,
        "difficulty": "Expert",
        "color": "#7c3aed",
        "duration_est": "15–25 min",
        "pass_score": 80,

        "narrative": (
            "This is a high-fidelity stress exercise. Multiple systems will degrade "
            "in sequence. You will be under time pressure with degraded information. "
            "Real BVLOS incidents rarely involve a single failure — they are chains "
            "of events. Your job is not to prevent failures; it is to manage them "
            "correctly in sequence, prioritise the greatest threat, and bring the "
            "aircraft back safely. Speed matters. Hesitation costs score. "
            "Panic costs the aircraft."
        ),

        "objectives": [
            "Identify and prioritise multiple simultaneous emergencies",
            "Follow the correct procedure for each — in the correct order",
            "Battery Critical always supersedes all other actions",
            "Complete the mission or execute a safe controlled abort",
        ],

        "weather": {
            "wind": "15 kt gusting 22 kt from 260°",
            "visibility": "5 SM (rain)",
            "sky": "Overcast 3,000 ft",
            "temperature": "15 °C",
            "density_altitude": "Standard — but wet, gusty conditions",
        },

        "notams": [
            "Multiple PIREPs of wind shear and GPS anomaly in corridor",
            "TFR active within 3 NM of stadium",
            "All operators advised to have abort plans ready",
        ],

        "checklist": [
            "All emergency procedures reviewed in sequence",
            "Priority order memorised: Safety of aircraft → Airspace → Mission",
            "Abort criteria established — no hesitation if threshold crossed",
            "Comms plan confirmed — who to call and when",
            "Battery fully charged and verified — margin is critical today",
        ],

        "events": [
            {"at_s": 30,  "type": "COMMS_DEGRADED",  "duration_s": 60},
            {"at_s": 55,  "type": "WIND_SHEAR",       "duration_s": 80},
            {"at_s": 80,  "type": "GPS_DEGRADED",     "duration_s": 50},
            {"at_s": 110, "type": "BATTERY_WARNING",  "duration_s": None},
            {"at_s": 160, "type": "BATTERY_CRITICAL", "duration_s": None},
        ],
    },
]

# Fast lookup by id
MISSIONS_BY_ID: dict[str, dict] = {m["id"]: m for m in MISSIONS}


def get_catalog() -> list[dict]:
    """Serialisable list for the frontend — omits internal event details."""
    return [
        {
            "id": m["id"],
            "title": m["title"],
            "subtitle": m["subtitle"],
            "level": m["level"],
            "difficulty": m["difficulty"],
            "color": m["color"],
            "duration_est": m["duration_est"],
            "pass_score": m["pass_score"],
            "narrative": m["narrative"],
            "objectives": m["objectives"],
            "weather": m["weather"],
            "notams": m["notams"],
            "checklist": m["checklist"],
        }
        for m in MISSIONS
    ]

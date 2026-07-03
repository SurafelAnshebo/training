# BVLOS Flight Training Simulator

A browser-based Beyond Visual Line of Sight (BVLOS) drone flight training simulator for pilots. Plan missions on a live map, monitor real-time telemetry, respond to instructor-injected emergencies, and receive a scored debrief — all without any hardware or external flight software.

---

## Contents

- [Overview](#overview)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Detailed Setup](#detailed-setup)
- [Using the Simulator](#using-the-simulator)
  - [Trainee Workflow](#trainee-workflow)
  - [Instructor Workflow](#instructor-workflow)
- [Scenario Reference](#scenario-reference)
- [Scoring Criteria](#scoring-criteria)
- [Configuration](#configuration)
- [Project Structure](#project-structure)
- [Troubleshooting](#troubleshooting)

---

## Overview

This simulator is built for BVLOS procedure training. It replaces a physical drone and ArduPilot SITL with a lightweight Python kinematic flight model that runs entirely inside the web server — no hardware, no external processes, no 10-minute SITL build.

**Trainees** plan a multi-waypoint mission on a Leaflet map, launch the drone, and monitor live telemetry in the sidebar. During flight the **instructor** can inject realistic emergencies (GPS loss, battery critical, wind shear, TFRs) from a separate dashboard. After landing, both see a scored debrief.

Multiple trainees can fly simultaneously — each gets their own isolated simulation session.

---

## Features

| Feature | Description |
|---|---|
| Mission planning | Click the map to lay waypoints; set altitude per waypoint; path auto-connects to home and landing |
| Live telemetry | Altitude, groundspeed, heading, vertical rate, battery, GPS fix, attitude — updated 2×/s |
| Animated map | Drone icon tracks position in real time; animated weather overlay; TFR circles |
| Scenario injection | Instructor triggers 8 emergency types mid-flight; trainee receives browser alert + audio beep |
| Scoring | Automatic post-flight score (0–100, A–F) across 5 criteria |
| Mission replay | Flight path recorded at 2 Hz; play back on the map after landing |
| Multi-user | Up to 20 concurrent trainee sessions; each isolated in its own simulation thread |
| Instructor dashboard | Live session monitor, scenario panel, force hover/land, inline debrief with event timeline |

---

## Prerequisites

| Requirement | Version |
|---|---|
| Python | **3.10 or newer** (3.12 recommended) |
| pip | bundled with Python |
| A modern web browser | Chrome, Firefox, Edge (Safari works too) |
| Internet connection | to load map tiles and CDN libraries on first use |

No drone hardware, ArduPilot, or SITL required.

---

## Quick Start

```bash
# 1. Clone the repository
git clone <repo-url>
cd BVLOS

# 2. Install dependencies
pip install -r flaskApp/requirements.txt

# 3. Run
python run.py
```

Open **http://localhost:5000** in your browser.

> **Instructor dashboard:** http://localhost:5000/instructor

---

## Detailed Setup

### 1. Clone

```bash
git clone <repo-url>
cd BVLOS
```

### 2. (Recommended) Create a virtual environment

```bash
python -m venv venv

# macOS / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r flaskApp/requirements.txt
```

The dependency list is minimal:

```
flask
flask-socketio
python-socketio
python-engineio
python-dotenv
```

### 4. (Optional) Configure environment

Copy the example environment file and edit as needed:

```bash
cp flaskApp/.env.example flaskApp/.env   # if the example exists, or create .env manually
```

See the [Configuration](#configuration) section for all available variables.

### 5. Run

```bash
python run.py
```

You should see:

```
INFO     werkzeug: * Running on http://0.0.0.0:5000
```

Open `http://localhost:5000` to begin.

---

## Using the Simulator

### Trainee Workflow

#### Step 1 — Start a session
When the page loads a dialog asks for your name. Enter it and click **Begin Session**. A unique 8-character session ID is assigned and stored in your browser tab. If you refresh the page your session reconnects automatically.

#### Step 2 — Plan your mission
Click anywhere on the map to place waypoints. Each waypoint appears as a numbered blue circle.

**Setting altitude:** Click a waypoint marker → a popup appears → enter altitude in metres AGL → click **Set Altitude**.

> All waypoints except the last (the landing zone) must have altitude > 0. The landing zone is fixed and pre-set to 0 m.

The total mission distance is shown in the status bar at the bottom.

#### Step 3 — Save waypoints
Click **Save WPs** in the left sidebar. This locks the waypoints and sends them to the server. The map click handler is disabled — you can no longer add points.

#### Step 4 — Launch
Click **Launch**. The simulator will:
1. Arm the vehicle
2. Climb to the altitude of the first waypoint
3. Fly each waypoint in sequence
4. Descend and land at the landing zone

Watch the blue **✈** icon move on the map. Monitor telemetry in the left panel.

#### Step 5 — In-flight controls

| Button | What it does |
|---|---|
| **Hover** | Pauses navigation; holds current position |
| **Resume** | Continues to the next waypoint |
| **Land** | Initiates immediate descent and landing |
| **Clear Map** | Resets markers (only works before waypoints are saved) |

#### Step 6 — Respond to scenarios
During flight the instructor may inject emergency scenarios. You will see a red/yellow alert card appear in the sidebar and hear a brief audio beep. Respond according to BVLOS procedures — for example:
- **Battery Critical** → initiate landing immediately
- **GPS Lost** → switch to LAND mode
- **TFR Activated** → hover and request reroute approval

Your response time is measured and affects your score.

#### Step 7 — Debrief
When the drone lands a score banner appears on the map. Click **View Full Debrief** for a criterion-by-criterion breakdown. Click **Replay Flight** in the sidebar to play back the flight path on the map.

---

### Instructor Workflow

Open **http://localhost:5000/instructor** in a separate browser tab or a different machine on the same network.

#### Session panel (left)
Lists all active trainee sessions with their name, session ID, current mission state, battery level, and any active scenarios. Click a session card to select it.

#### Scenario injection (centre panel)
After selecting a session, the centre panel shows 8 scenario buttons. Click any to inject it into that trainee's simulation instantly. The trainee receives a real-time alert.

**Active scenarios** lists what is currently running on that session. Click **Clear** next to any scenario to remove it.

#### Live telemetry & map (right panel)
The map shows the trainee's drone position in real time. The telemetry overlay shows altitude, speed, heading, battery, GPS, and flight mode.

#### Force actions
| Button | Effect |
|---|---|
| **Force Hover** | Commands the trainee's drone to hover |
| **Force Land** | Commands immediate landing |
| **View Debrief** | Opens the full scored debrief for that session |

#### Debrief panel
Displays score, grade, per-criterion breakdown, and a timestamped event timeline showing every waypoint reached, scenario injected, and pilot action taken.

---

## Scenario Reference

| Scenario | Severity | Default Duration | What it simulates |
|---|---|---|---|
| GPS Degraded | ⚠ Warning | 60 s | Position noise increases; satellites drop to 4–7; fix degrades to 2D |
| GPS Lost | 🔴 Critical | 30 s | No GPS — autonomous navigation unavailable |
| Wind Shear | ⚠ Warning | 90 s | Groundspeed fluctuates ±4 m/s randomly |
| Battery Warning | ⚠ Warning | Permanent | Power draw increases 1.6× — accelerated drain |
| Battery Critical | 🔴 Critical | Permanent | Power draw increases 2.8× — immediate landing required |
| Comms Degraded | ⚠ Warning | 60 s | Telemetry updates become sporadic (visual only) |
| TFR Activated | 🔴 Critical | Permanent | New Temporary Flight Restriction appears on route |
| Obstacle Detected | 🔴 Critical | Permanent | Detect-and-avoid alert — trainee must reroute |

> Permanent scenarios stay active until the instructor clicks **Clear**.

---

## Scoring Criteria

The post-flight score is a weighted average out of 100 points:

| Criterion | Weight | What is measured |
|---|---|---|
| Mission Completion | 30% | Fraction of waypoints reached; 100 pts if all complete |
| Altitude Compliance | 20% | Percentage of flight time within ±15% of planned altitude |
| Emergency Response | 25% | Average time from scenario injection to pilot action (hover/land/resume). ≤10 s = 100 pts, ≥60 s = 0 pts |
| Battery Management | 15% | Landing with ≥20% battery remaining (100 pts), or prompt landing after Battery Critical injection. **If the battery reaches 0% before landing, the aircraft loses power and crashes** — mission ends immediately with 0 points for this criterion. |
| Landing Accuracy | 10% | Distance from planned landing point. ≤5 m = 100 pts, ≥60 m = 0 pts |

**Grade scale:** A ≥ 90 · B ≥ 80 · C ≥ 70 · D ≥ 60 · F < 60

---

## Configuration

Create a file at `flaskApp/.env` to override defaults:

```dotenv
# Number of metres above ground
HOME_LAT=33.807607
HOME_LON=-84.373981
LANDING_LAT=33.856192
LANDING_LON=-84.216326

# Max simultaneous sessions
MAX_SESSIONS=20

# Telemetry push rate (Hz) — 1-4 recommended
TELEMETRY_HZ=2

# Logging level: DEBUG | INFO | WARNING
LOG_LEVEL=INFO

# Flask secret key — change in production
SECRET_KEY=change-this-in-production
```

To change the default takeoff and landing coordinates, update `HOME_LAT`/`HOME_LON` and `LANDING_LAT`/`LANDING_LON`. The map will centre on the new home location.

---

## Project Structure

```
BVLOS/
├── run.py                        # Entry point — run this
└── flaskApp/
    ├── app.py                    # Flask app factory (blueprints + SocketIO)
    ├── config.py                 # Configuration class
    ├── extensions.py             # SocketIO singleton
    ├── session_manager.py        # Multi-session lifecycle management
    │
    ├── simulation/
    │   ├── flight_sim.py         # Kinematic flight physics (10 Hz), telemetry recorder
    │   └── scenarios.py          # Scenario definitions
    │
    ├── scoring/
    │   └── scorer.py             # Post-flight scoring engine
    │
    ├── routes/
    │   ├── main.py               # GET / (trainee view)
    │   ├── mission.py            # /api/session/* (session + flight control)
    │   ├── instructor.py         # /instructor/* (dashboard + scenario injection)
    │   └── replay.py             # /api/session/<id>/debrief, /flight_log
    │
    ├── socket_events/
    │   └── flight_events.py      # SocketIO handlers + telemetry push loop
    │
    ├── templates/
    │   ├── base.html             # Shared styles and layout
    │   ├── index.html            # Trainee view
    │   └── instructor.html       # Instructor dashboard
    │
    ├── static/
    │   ├── logo.png
    │   ├── weather.png           # Weather overlay image
    │   └── Airport.geojson       # Airport locations (Atlanta area)
    │
    └── requirements.txt
```

### Key API endpoints

| Method | URL | Description |
|---|---|---|
| `POST` | `/api/session` | Create a new training session |
| `POST` | `/api/session/<id>/launch` | Arm vehicle and start mission |
| `POST` | `/api/session/<id>/hover` | Command hover |
| `POST` | `/api/session/<id>/resume` | Resume navigation |
| `POST` | `/api/session/<id>/land` | Initiate landing |
| `GET`  | `/api/session/<id>/debrief` | Retrieve scored debrief JSON |
| `GET`  | `/api/session/<id>/flight_log` | Retrieve recorded telemetry for replay |
| `POST` | `/instructor/session/<id>/inject` | Inject a scenario (instructor only) |
| `POST` | `/instructor/session/<id>/clear` | Clear a scenario |
| `GET`  | `/instructor/sessions` | List all active sessions |

---

## Troubleshooting

### `ModuleNotFoundError: No module named 'flask_socketio'`

You are either not in the virtual environment or the install step was skipped.

```bash
pip install -r flaskApp/requirements.txt
```

### Page loads but map does not appear

This is usually an internet connection issue — map tiles and CDN libraries (Leaflet, Socket.IO) load from external URLs. Make sure the machine has internet access, or configure local copies.

### "Maximum concurrent sessions reached"

The default limit is 20. Increase it in `.env`:

```dotenv
MAX_SESSIONS=40
```

### Launch button does nothing / returns error

Make sure **all intermediate waypoints** (every waypoint except the last landing point) have altitude > 0. Click a waypoint marker and set its altitude before launching.

### Session disappears on page refresh

Sessions are stored in `sessionStorage` (browser tab memory). If you open a new tab you need to start a new session. If you refresh the same tab the session reconnects automatically as long as the server is still running.

### Port 5000 is already in use

```bash
# Linux / macOS — find what is using it
lsof -i :5000

# Or change the port in run.py:
socketio.run(app, host="0.0.0.0", port=5001, ...)
```

### Multiple students on the same network

Run `python run.py` on one machine. Students on the same network connect to `http://<server-ip>:5000`. Find the server IP with:

```bash
# Linux / macOS
ip addr show | grep "inet "

# Windows
ipconfig
```

---

## Notes for Instructors

- Open `/instructor` **before** trainees connect — the page auto-refreshes every 2 seconds.
- You can monitor multiple sessions simultaneously; click any session card to switch the map and telemetry view.
- Scenarios persist until cleared — use this to simulate prolonged emergencies.
- The debrief event timeline shows exact timestamps of every scenario injection and pilot action, useful for a post-exercise group review.
- Sessions are **not** persisted to disk — restarting the server clears all sessions and flight logs. If you need to retain records, save the JSON from `GET /api/session/<id>/debrief` before stopping the server.

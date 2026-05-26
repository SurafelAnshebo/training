@echo off
:: BVLOS Flask App — local setup script (Windows)
:: Requires Python 3.10 or 3.11  (dronekit breaks on 3.12+)
:: Run this once before starting the app.

where python3 >nul 2>&1
if %errorlevel%==0 (
    set PYTHON=python3
) else (
    set PYTHON=python
)

echo Using: %PYTHON%
%PYTHON% --version

echo.
echo Creating virtual environment...
%PYTHON% -m venv venv

echo Activating and installing dependencies...
call venv\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt

echo.
echo Setup complete. To start the app:
echo   venv\Scripts\activate.bat
echo   python app.py
echo.
echo NOTE: ArduPilot SITL is Linux-only.
echo   Start SITL manually inside WSL2:
echo   cd /path/to/ardupilot
echo   python3 Tools/autotest/sim_vehicle.py -v ArduCopter -L Atl --out=udp:127.0.0.1:14550
echo   Then run this Flask app on Windows.

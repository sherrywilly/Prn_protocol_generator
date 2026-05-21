@echo off
setlocal EnableExtensions

REM Run from this script's directory
cd /d "%~dp0"

echo ==========================================
echo   MAR Resident Portal - Windows Launcher
echo ==========================================
echo.

REM Ensure Python is available
where py >nul 2>&1
if %errorlevel%==0 (
    set "PY_CMD=py -3"
) else (
    where python >nul 2>&1
    if %errorlevel%==0 (
        set "PY_CMD=python"
    ) else (
        echo ERROR: Python was not found in PATH.
        echo Install Python 3 and try again.
        pause
        exit /b 1
    )
)

REM Create virtual environment if missing
if not exist ".venv\Scripts\python.exe" (
    echo [1/6] Creating virtual environment in .venv ...
    %PY_CMD% -m venv .venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
) else (
    echo [1/6] Virtual environment already exists.
)

REM Activate virtual environment
call ".venv\Scripts\activate.bat"
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment.
    pause
    exit /b 1
)

REM Upgrade pip
echo [2/6] Upgrading pip ...
python -m pip install --upgrade pip
if errorlevel 1 (
    echo ERROR: Failed to upgrade pip.
    pause
    exit /b 1
)

REM Install dependencies
echo [3/6] Installing requirements ...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install requirements.
    pause
    exit /b 1
)

REM Ensure .env exists
if not exist ".env" (
    if exist ".env.example" (
        echo [4/6] Creating .env from .env.example ...
        copy /Y ".env.example" ".env" >nul
    ) else (
        echo [4/6] No .env.example found. Skipping .env creation.
    )
) else (
    echo [4/6] .env already exists.
)

REM Run migrations
echo [5/6] Running migrations ...
python manage.py migrate
if errorlevel 1 (
    echo ERROR: Migration failed.
    pause
    exit /b 1
)

REM Optional superuser creation
echo.
set /p CREATE_SUPERUSER=Do you want to create/update a superuser now? (y/N): 
if /I "%CREATE_SUPERUSER%"=="y" (
    python manage.py createsuperuser
)

REM Run development server
echo [6/6] Starting Django dev server on http://127.0.0.1:8000/
echo Press Ctrl+C to stop.
python manage.py runserver

endlocal

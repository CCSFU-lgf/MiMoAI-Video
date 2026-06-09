@echo off
echo ========================================
echo   MiMo ASR - Video Subtitle ^& Auto Editor
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

REM Check if dependencies are installed
echo Checking dependencies...
pip install -q openai streamlit tomli 2>nul

REM Check if FFmpeg is installed
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo.
    echo WARNING: FFmpeg is not installed or not in PATH
    echo.
    echo Please install FFmpeg:
    echo   1. Download from https://ffmpeg.org/download.html
    echo   2. Extract and add the 'bin' folder to your PATH
    echo.
    echo The app may not work properly without FFmpeg.
    echo.
)

REM Check if config.toml exists
if not exist "config\config.toml" (
    echo.
    echo WARNING: config.toml not found in config directory
    echo Please configure your MiMo API key:
    echo   1. Create config/config.toml in the project root
    echo   2. Add: api_key = "your-api-key"
    echo.
)

REM Start the app
echo.
echo Starting MiMo ASR...
echo.
echo The app will open in your browser at http://localhost:8501
echo.
echo Press Ctrl+C to stop the server
echo.

streamlit run src\app.py --server.port 8501

pause

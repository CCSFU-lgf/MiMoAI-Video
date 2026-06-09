#!/bin/bash

echo "========================================"
echo "  MiMo ASR - Video Subtitle & Auto Editor"
echo "========================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Please install Python 3.8+ from your package manager"
    exit 1
fi

# Check if dependencies are installed
echo "Checking dependencies..."
pip3 install -q openai streamlit tomli 2>/dev/null

# Check if FFmpeg is installed
if ! command -v ffmpeg &> /dev/null; then
    echo ""
    echo "WARNING: FFmpeg is not installed"
    echo ""
    echo "Please install FFmpeg:"
    echo "  MacOS: brew install ffmpeg"
    echo "  Linux: sudo apt install ffmpeg"
    echo ""
    echo "The app may not work properly without FFmpeg."
    echo ""
fi

# Check if config.toml exists
if [ ! -f "config/config.toml" ]; then
    echo ""
    echo "WARNING: config.toml not found in config directory"
    echo "Please configure your MiMo API key:"
    echo "  1. Create config/config.toml in the project root"
    echo "  2. Add: api_key = \"your-api-key\""
    echo ""
fi

# Start the app
echo ""
echo "Starting MiMo ASR..."
echo ""
echo "The app will open in your browser at http://localhost:8501"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

streamlit run src/app.py --server.port 8501

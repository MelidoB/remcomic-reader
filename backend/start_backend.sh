#!/bin/bash
echo "🗨️ Comic Reader - Starting Backend API Server"
echo "=========================================="
echo "🔌 API will be available at: http://0.0.0.0:5000"
echo "✅ Make sure the frontend is configured with your PC's IP address."
echo "🔄 Press Ctrl+C to stop the server"
echo ""
# Adjust the PYTHONPATH if your project is in a different location
export PYTHONPATH=$PYTHONPATH:$(pwd)
source venv/bin/activate
pip install -r requirements.txt
python3 server.py
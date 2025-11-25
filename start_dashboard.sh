#!/bin/bash

echo "🚀 Starting Crypto EMA Scanner Dashboard"
echo "========================================"
echo ""

# Check if in correct directory
if [ ! -f "api_server.py" ]; then
    echo "❌ Error: api_server.py not found"
    echo "Please run this script from the project root directory"
    exit 1
fi

# Check if Flask is installed
python3 -c "import flask" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "📦 Installing Flask..."
    pip install flask flask-cors --break-system-packages
fi

# Check if dashboard exists
if [ ! -d "crypto-scanner-dashboard" ]; then
    echo "❌ Error: crypto-scanner-dashboard directory not found"
    exit 1
fi

# Check if node_modules exists
if [ ! -d "crypto-scanner-dashboard/node_modules" ]; then
    echo "📦 Installing npm dependencies..."
    cd crypto-scanner-dashboard
    npm install
    cd ..
fi

echo ""
echo "✅ All dependencies ready!"
echo ""
echo "Starting servers..."
echo ""

# Start API server in background
echo "📡 Starting API Server on http://localhost:5000"
python3 api_server.py > /dev/null 2>&1 &
API_PID=$!

# Wait for API to start
sleep 2

# Start frontend
echo "🎨 Starting Dashboard on http://localhost:5173"
echo ""
echo "========================================"
echo "✨ Dashboard is ready!"
echo "========================================"
echo ""
echo "📱 Open your browser to: http://localhost:5173"
echo ""
echo "💡 Quick Start:"
echo "   1. Click 'DEMO MODE' to see simulated data"
echo "   2. Or click 'RUN SCAN' for real data"
echo ""
echo "⚠️  Press Ctrl+C to stop all servers"
echo ""

cd crypto-scanner-dashboard
npm run dev

# Cleanup on exit
trap "echo ''; echo '🛑 Stopping servers...'; kill $API_PID 2>/dev/null; exit" INT TERM
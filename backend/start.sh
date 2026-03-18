#!/bin/zsh

# ─── SmartPre Startup Script ───
# Automates environment checks and server startup.

echo "🚀 Starting SmartPre AI Trading Agent..."

# Ensure we're in the backend directory
if [[ ! -f "main.py" ]]; then
    if [[ -d "backend" ]]; then
        cd backend
    fi
fi

# 1. Environment Check
if [[ ! -d "venv" ]]; then
    echo "⚠️  Venv not found. Creating..."
    python3 -m venv venv
fi

# 2. Dependencies
echo "📦 Checking dependencies..."
./venv/bin/python3 -m pip install --upgrade pip
./venv/bin/python3 -m pip install -r requirements.txt

# 3. ML check
./venv/bin/python3 -c "import torch" 2>/dev/null
if [[ $? -ne 0 ]]; then
    echo "🧠 Installing Torch for ML..."
    ./venv/bin/python3 -m pip install torch torchvision
fi

# 4. Start Server
echo "⚡ Starting Backend..."
./venv/bin/python3 main.py

#!/bin/zsh

# ─── SmartPre Training Script ───
# Downloads historical data and trains AI models.

if [[ ! -f "train_models.py" ]]; then
    if [[ -d "backend" ]]; then
        cd backend
    fi
fi

if [[ ! -d "venv" ]]; then echo "❌ Venv not found."; exit 1; fi

echo "🧠 Starting AI Model Training..."
./venv/bin/python3 train_models.py

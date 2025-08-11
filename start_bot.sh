#!/bin/bash

echo "🚀 Starting Solana Trading Bot..."
echo "📱 Bot: @PredatonSolana_bot"
echo "💬 Send /start to begin"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run setup first."
    exit 1
fi

# Activate virtual environment and run bot
source venv/bin/activate

# Check if main.py exists
if [ ! -f "main.py" ]; then
    echo "❌ main.py not found!"
    exit 1
fi

echo "✅ Starting bot..."
python main.py 
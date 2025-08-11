#!/bin/bash

# Solana Trading Bot Restart Script with Network Checks

echo "🔄 Restarting Solana Trading Bot..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run setup first."
    exit 1
fi

# Clean up any existing processes and locks
echo "🧹 Cleaning up existing processes..."
./cleanup_locks.sh

# Activate virtual environment
source venv/bin/activate

# Test network connectivity first
echo "🔍 Testing network connectivity..."
python test_network.py

if [ $? -ne 0 ]; then
    echo "⚠️  Network issues detected. Bot may not work properly."
    echo "💡 Check your internet connection and try again."
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Aborted restart."
        exit 1
    fi
fi

# Start the bot
echo "🚀 Starting Solana Trading Bot..."
python main.py 
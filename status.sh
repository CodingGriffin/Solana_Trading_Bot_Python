#!/bin/bash

# Solana Trading Bot Status Check

echo "🤖 Solana Trading Bot Status"
echo "=============================="

# Check if bot is running
if pgrep -f "python main.py" > /dev/null; then
    echo "✅ Bot Status: RUNNING"
    echo "📊 Process Info:"
    ps aux | grep "python main.py" | grep -v grep
else
    echo "❌ Bot Status: NOT RUNNING"
fi

echo ""
echo "🌐 Network Status:"

# Test network connectivity
if [ -d "venv" ]; then
    source venv/bin/activate
    python test_network.py
else
    echo "❌ Virtual environment not found"
fi

echo ""
echo "📁 Bot Files:"
if [ -f "main.py" ]; then
    echo "✅ main.py - Found"
else
    echo "❌ main.py - Missing"
fi

if [ -f "config/settings.py" ]; then
    echo "✅ config/settings.py - Found"
else
    echo "❌ config/settings.py - Missing"
fi

if [ -f ".env" ]; then
    echo "✅ .env - Found"
else
    echo "❌ .env - Missing"
fi

echo ""
echo "💡 Quick Commands:"
echo "  ./restart_bot.sh  - Restart the bot"
echo "  ./status.sh       - Check this status again"
echo "  python main.py    - Start bot manually" 
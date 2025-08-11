#!/bin/bash

# Cleanup script for Solana Trading Bot
# Removes lock files and stops all bot processes

echo "🧹 Cleaning up Solana Trading Bot..."

# Stop all bot processes
echo "🛑 Stopping all bot processes..."
pkill -f "python main.py" || true
sleep 2

# Force kill any remaining processes
echo "🔨 Force stopping any remaining processes..."
pkill -9 -f "python main.py" || true

# Remove lock files
echo "🗑️  Removing lock files..."
rm -f /tmp/solana_trading_bot.lock || true

# Check if any processes are still running
echo "🔍 Checking for remaining processes..."
if pgrep -f "python main.py" > /dev/null; then
    echo "⚠️  Some processes are still running. You may need to restart your system."
else
    echo "✅ All processes stopped successfully"
fi

echo "✨ Cleanup completed!"
echo ""
echo "💡 You can now start the bot with:"
echo "   python main.py"
echo "   or"
echo "   ./restart_bot.sh" 
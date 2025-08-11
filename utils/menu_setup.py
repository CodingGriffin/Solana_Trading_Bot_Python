#!/usr/bin/env python3
"""
Telegram Bot Menu Button Setup
"""

import asyncio
import os
from dotenv import load_dotenv
import aiohttp
from telegram import Bot

load_dotenv()

async def setup_bot_commands():
    """Set up bot commands menu"""
    bot_token = os.getenv("BOT_TOKEN")
    
    if not bot_token:
        print("❌ No bot token found in .env file")
        return False
    
    # Define bot commands
    commands = [
        ("start", "🚀 Start the bot and see main menu"),
        ("help", "❓ Get help and see available commands"),
        ("wallet", "💼 Wallet operations and monitoring"),
        ("trade", "⚡ Trading operations and orders"),
        ("analyze", "📊 Analysis tools and insights"),
        ("settings", "⚙️ Bot settings and configuration"),
        ("admin", "🔧 Admin panel (admin only)")
    ]
    
    try:
        # Create bot instance
        bot = Bot(bot_token)
        
        # Set commands
        await bot.set_my_commands(commands)
        
        print("✅ Bot menu commands set successfully!")
        print("\n📋 Available Commands:")
        for cmd, description in commands:
            print(f"  /{cmd} - {description}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error setting bot commands: {e}")
        return False

async def test_bot_connection():
    """Test bot connection before setting commands"""
    bot_token = os.getenv("BOT_TOKEN")
    
    if not bot_token:
        print("❌ No bot token found in .env file")
        return False
    
    url = f"https://api.telegram.org/bot{bot_token}/getMe"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('ok'):
                        bot_info = data.get('result', {})
                        print(f"✅ Bot connection successful!")
                        print(f"🤖 Bot Name: {bot_info.get('first_name', 'Unknown')}")
                        print(f"👤 Username: @{bot_info.get('username', 'Unknown')}")
                        return True
                    else:
                        print(f"❌ API Error: {data.get('description', 'Unknown error')}")
                        return False
                else:
                    print(f"❌ HTTP Error: {response.status}")
                    return False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

async def main():
    """Main function"""
    print("🔧 Setting up Telegram Bot Menu")
    print("=" * 40)
    
    # Test connection first
    if not await test_bot_connection():
        return
    
    print()
    
    # Set up commands
    if await setup_bot_commands():
        print("\n🎉 Menu setup completed successfully!")
        print("\n💡 Users will now see these commands when they tap the menu button.")
        print("📱 The menu button appears in the bottom-left corner of the chat.")
    else:
        print("\n❌ Menu setup failed!")

if __name__ == "__main__":
    asyncio.run(main()) 
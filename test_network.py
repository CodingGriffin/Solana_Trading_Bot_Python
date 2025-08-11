#!/usr/bin/env python3
"""
Network connectivity test script for Solana Trading Bot
"""

import asyncio
import aiohttp
import logging
from config.settings import TELEGRAM_TIMEOUT

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_telegram_api():
    """Test Telegram API connectivity"""
    print("🔍 Testing Telegram API connectivity...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                'https://api.telegram.org', 
                timeout=aiohttp.ClientTimeout(total=TELEGRAM_TIMEOUT)
            ) as response:
                if response.status == 200:
                    print("✅ Telegram API is accessible")
                    return True
                else:
                    print(f"❌ Telegram API returned status {response.status}")
                    return False
    except asyncio.TimeoutError:
        print("❌ Telegram API timeout")
        return False
    except Exception as e:
        print(f"❌ Telegram API error: {e}")
        return False

async def test_solana_rpc():
    """Test Solana RPC connectivity"""
    print("🔍 Testing Solana RPC connectivity...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                'https://api.mainnet-beta.solana.com',
                json={"jsonrpc": "2.0", "id": 1, "method": "getHealth"},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("result") == "ok":
                        print("✅ Solana RPC is accessible")
                        return True
                    else:
                        print(f"❌ Solana RPC health check failed: {data}")
                        return False
                else:
                    print(f"❌ Solana RPC returned status {response.status}")
                    return False
    except asyncio.TimeoutError:
        print("❌ Solana RPC timeout")
        return False
    except Exception as e:
        print(f"❌ Solana RPC error: {e}")
        return False

async def main():
    """Run network tests"""
    print("🌐 Network Connectivity Test")
    print("=" * 40)
    
    telegram_ok = await test_telegram_api()
    solana_ok = await test_solana_rpc()
    
    print("\n📊 Test Results:")
    print(f"Telegram API: {'✅ OK' if telegram_ok else '❌ FAILED'}")
    print(f"Solana RPC: {'✅ OK' if solana_ok else '❌ FAILED'}")
    
    if telegram_ok and solana_ok:
        print("\n🎉 All tests passed! Your bot should work properly.")
    else:
        print("\n⚠️  Some tests failed. Check your internet connection and try again.")
        if not telegram_ok:
            print("💡 Telegram API issues might be due to:")
            print("   - Internet connectivity problems")
            print("   - Firewall blocking Telegram")
            print("   - DNS resolution issues")
        if not solana_ok:
            print("💡 Solana RPC issues might be due to:")
            print("   - Internet connectivity problems")
            print("   - Solana network issues")
            print("   - RPC endpoint problems")

if __name__ == "__main__":
    asyncio.run(main()) 
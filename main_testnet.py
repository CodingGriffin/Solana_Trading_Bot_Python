"""
Solana Trading Bot - Testnet Version
Use this for safe testing before mainnet deployment
"""

import asyncio
import logging
import os
import sys
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.database import DatabaseManager
from services.solana_service import SolanaService
from services.wallet_analyzer import WalletAnalyzer
from services.trading_engine import TradingEngine
from services.payment_service import PaymentService
from handlers.bot_handlers import BotHandlers
from utils.logger import setup_logger

# Import testnet settings
from config.testnet_settings import *

# Setup logging for testnet
setup_logger()
logger = logging.getLogger(__name__)

class SolanaTradingBotTestnet:
    def __init__(self):
        self.app = None
        
    async def setup(self):
        """Initialize bot services for testnet"""
        logger.info("🚀 Starting Solana Trading Bot (TESTNET MODE)")
        logger.info("🧪 TESTNET CONFIGURATION ACTIVE")
        
        # Initialize database manager with testnet database
        self.db_manager = DatabaseManager(TESTNET_DATABASE_URL)
        await self.db_manager.connect()
        logger.info("✅ Testnet database connected successfully")
        
        # Initialize Solana service with testnet RPC
        self.solana_service = SolanaService()
        await self.solana_service.connect()
        logger.info("✅ Solana testnet service connected successfully")
        
        # Initialize wallet analyzer
        self.wallet_analyzer = WalletAnalyzer(self.db_manager, self.solana_service)
        
        # Initialize payment service
        self.payment_service = PaymentService(self.db_manager, self.solana_service)
        
        # Initialize trading engine
        self.trading_engine = TradingEngine(self.solana_service, self.db_manager, self.payment_service)
        
        # Start payment service monitoring
        await self.payment_service.start_monitoring()
        
        # Initialize handlers with testnet admin configuration
        admin_chat_ids = []
        admin_chat_id = TESTNET_ADMIN_CHAT_ID
        if admin_chat_id:
            try:
                admin_chat_ids = [int(admin_chat_id)]
            except ValueError:
                logger.warning(f"Invalid TESTNET_ADMIN_CHAT_ID: {admin_chat_id}")
        
        self.handlers = BotHandlers(
            self.db_manager, 
            self.solana_service, 
            self.wallet_analyzer, 
            self.trading_engine,
            self.payment_service,
            admin_chat_ids=admin_chat_ids
        )
        
        # Initialize Telegram application
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not bot_token:
            logger.error("❌ TELEGRAM_BOT_TOKEN not found in environment variables")
            return False
            
        self.app = Application.builder().token(bot_token).build()
        
        # Register handlers
        self.app.add_handler(CommandHandler("start", self.handlers.start_command))
        self.app.add_handler(CommandHandler("help", self.handlers.help_command))
        self.app.add_handler(CommandHandler("wallet", self.handlers.wallet_command))
        self.app.add_handler(CommandHandler("trade", self.handlers.trade_command))
        self.app.add_handler(CommandHandler("analyze", self.handlers.analyze_command))
        self.app.add_handler(CommandHandler("settings", self.handlers.settings_command))
        self.app.add_handler(CommandHandler("admin", self.handlers.admin_command))
        
        # Register callback query handler
        self.app.add_handler(CallbackQueryHandler(self.handlers.handle_callback))
        
        # Register message handler for wallet addresses and other inputs
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handlers.handle_message))
        
        logger.info("✅ Testnet bot handlers registered successfully")
        return True
        
    async def start(self):
        """Start the testnet bot"""
        logger.info("🧪 Starting Solana Trading Bot in TESTNET MODE")
        logger.info("📱 Find your bot on Telegram: @PredatonSolana_bot")
        logger.info("💬 Send /start to begin")
        logger.info("⏹️  Press Ctrl+C to stop")
        logger.info("🔗 Connecting to Telegram API...")
        
        try:
            await self.app.initialize()
            await self.app.start()
            await self.app.updater.start_polling()
            
            logger.info("✅ Connected to Telegram API successfully!")
            logger.info("🧪 TESTNET MODE: All transactions will use testnet SOL")
            logger.info("💰 TESTNET FEES: 0.05% trading fees, 0.01 SOL Premium, 0.05 SOL Pro")
            logger.info("🔒 TESTNET SECURITY: All features tested safely")
            
            # Keep the bot running
            await asyncio.Event().wait()
            
        except KeyboardInterrupt:
            logger.info("🛑 Shutting down testnet bot...")
        except Exception as e:
            logger.error(f"❌ Error starting testnet bot: {e}")
        finally:
            await self.cleanup()
            
    async def cleanup(self):
        """Cleanup resources"""
        try:
            if self.app:
                await self.app.stop()
                await self.app.shutdown()
            if self.db_manager:
                await self.db_manager.close()
            logger.info("✅ Testnet bot shutdown complete")
        except Exception as e:
            logger.error(f"❌ Error during testnet bot cleanup: {e}")

async def main():
    """Main function for testnet bot"""
    bot = SolanaTradingBotTestnet()
    if await bot.setup():
        await bot.start()
    else:
        logger.error("❌ Failed to setup testnet bot")

if __name__ == "__main__":
    # Set testnet environment
    os.environ["SOLANA_RPC_URL"] = "https://api.testnet.solana.com"
    os.environ["SOLANA_WS_URL"] = "wss://api.testnet.solana.com"
    
    # Run the testnet bot
    asyncio.run(main()) 
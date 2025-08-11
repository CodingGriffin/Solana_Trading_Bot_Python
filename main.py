"""
Solana Trading & Wallet Analysis Telegram Bot
Main entry point with modular architecture
"""

import asyncio
import logging
import signal
import sys
import os
import fcntl
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from telegram.request import HTTPXRequest
from config.settings import BOT_TOKEN, DATABASE_URL, TELEGRAM_TIMEOUT, TELEGRAM_CONNECT_TIMEOUT, TELEGRAM_READ_TIMEOUT
from handlers.bot_handlers import BotHandlers
from services.database import DatabaseManager
from services.solana_service import SolanaService
from services.wallet_analyzer import WalletAnalyzer
from services.trading_engine import TradingEngine
from services.payment_service import PaymentService
from utils.logger import setup_logger

# Setup logging
setup_logger()
logger = logging.getLogger(__name__)

class SolanaTradingBot:
    def __init__(self):
        self.app = None
        self.db_manager = None
        self.solana_service = None
        self.wallet_analyzer = None
        self.trading_engine = None
        self.payment_service = None
        self.handlers = None
        self.running = False
        self.lock_file = None
        self.lock_fd = None
        
    def _acquire_lock(self):
        """Acquire a process lock to prevent multiple instances"""
        lock_file_path = "/tmp/solana_trading_bot.lock"
        try:
            self.lock_fd = open(lock_file_path, 'w')
            fcntl.flock(self.lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.lock_file = lock_file_path
            logger.info("Process lock acquired successfully")
            return True
        except (IOError, OSError) as e:
            logger.error(f"Failed to acquire process lock: {e}")
            logger.error("Another bot instance is already running!")
            return False
            
    def _release_lock(self):
        """Release the process lock"""
        if self.lock_fd:
            try:
                fcntl.flock(self.lock_fd.fileno(), fcntl.LOCK_UN)
                self.lock_fd.close()
                if self.lock_file and os.path.exists(self.lock_file):
                    os.unlink(self.lock_file)
                logger.info("Process lock released")
            except Exception as e:
                logger.error(f"Error releasing process lock: {e}")
        
    async def setup(self):
        """Initialize all services"""
        # Initialize database
        self.db_manager = DatabaseManager(DATABASE_URL)
        await self.db_manager.connect()
        logger.info("Database connected successfully")
        
        # Initialize Solana service
        self.solana_service = SolanaService()
        await self.solana_service.connect()
        logger.info("Solana service connected successfully")
        
        # Initialize wallet analyzer
        self.wallet_analyzer = WalletAnalyzer(self.db_manager, self.solana_service)
        
        # Initialize trading engine
        self.trading_engine = TradingEngine(self.solana_service, self.db_manager, self.payment_service)
        
        # Initialize payment service
        self.payment_service = PaymentService(self.db_manager, self.solana_service)
        
        # Start payment service monitoring
        await self.payment_service.start_monitoring()
        
        # Initialize handlers with admin configuration
        admin_chat_ids = []
        admin_chat_id = os.getenv("ADMIN_CHAT_ID")
        if admin_chat_id:
            try:
                admin_chat_ids = [int(admin_chat_id)]
            except ValueError:
                logger.warning(f"Invalid ADMIN_CHAT_ID: {admin_chat_id}")
        
        self.handlers = BotHandlers(
            self.db_manager, 
            self.solana_service, 
            self.wallet_analyzer, 
            self.trading_engine,
            self.payment_service,
            admin_chat_ids=admin_chat_ids
        )
        
        # Initialize bot application with network resilience
        request = HTTPXRequest(
            connection_pool_size=8,
            connect_timeout=TELEGRAM_CONNECT_TIMEOUT,
            read_timeout=TELEGRAM_READ_TIMEOUT,
            write_timeout=TELEGRAM_TIMEOUT
        )
        self.app = Application.builder().token(BOT_TOKEN).request(request).build()
        
        # Configure request settings for better network resilience
        # Note: Timeout settings are configured through the Application builder
        # The individual timeout properties are read-only
        
        # Set up bot commands menu
        await self._setup_bot_commands()
        
        logger.info("Bot services initialized successfully")
        
    def register_handlers(self):
        """Register all bot handlers"""
        # Command handlers
        self.app.add_handler(CommandHandler("start", self.handlers.start_command))
        self.app.add_handler(CommandHandler("help", self.handlers.help_command))
        self.app.add_handler(CommandHandler("wallet", self.handlers.wallet_command))
        self.app.add_handler(CommandHandler("trade", self.handlers.trade_command))
        self.app.add_handler(CommandHandler("analyze", self.handlers.analyze_command))
        self.app.add_handler(CommandHandler("settings", self.handlers.settings_command))
        self.app.add_handler(CommandHandler("admin", self.handlers.admin_command))
        
        # Callback query handlers
        self.app.add_handler(CallbackQueryHandler(self.handlers.handle_callback))
        
        # Message handlers
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handlers.handle_message))
        
        # Add error handler for network issues
        self.app.add_error_handler(self._error_handler)
    
    async def check_network_health(self):
        """Check network connectivity"""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get('https://api.telegram.org', timeout=10) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"Network health check failed: {e}")
            return False
            
    async def _error_handler(self, update, context):
        """Handle errors gracefully"""
        try:
            # Log the error
            logger.error(f"Exception while handling an update: {context.error}")
            
            # Handle specific error types
            if "TimedOut" in str(context.error) or "ReadTimeout" in str(context.error):
                logger.warning("Network timeout detected, continuing operation...")
                return
                
            if "Query is too old" in str(context.error):
                logger.warning("Callback query expired, ignoring...")
                return
                
            # For other errors, try to notify the user if possible
            if update and update.effective_chat:
                try:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text="⚠️ An error occurred. Please try again in a moment."
                    )
                except Exception as e:
                    logger.error(f"Failed to send error message: {e}")
                    
        except Exception as e:
            logger.error(f"Error in error handler: {e}")
    
    async def _setup_bot_commands(self):
        """Set up bot commands menu"""
        try:
            commands = [
                ("start", "🚀 Start the bot and see main menu"),
                ("help", "❓ Get help and see available commands"),
                ("wallet", "💼 Wallet operations and monitoring"),
                ("trade", "⚡ Trading operations and orders"),
                ("analyze", "📊 Analysis tools and insights"),
                ("settings", "⚙️ Bot settings and configuration"),
                ("admin", "🔧 Admin panel (admin only)")
            ]
            
            await self.app.bot.set_my_commands(commands)
            logger.info("Bot commands menu set successfully")
            
        except Exception as e:
            logger.warning(f"Failed to set bot commands: {e}")
    
    async def start_background_tasks(self):
        """Start background monitoring tasks"""
        # Start network health monitoring
        asyncio.create_task(self._network_health_monitor())
        
    async def _network_health_monitor(self):
        """Monitor network health periodically"""
        while self.running:
            try:
                is_healthy = await self.check_network_health()
                if not is_healthy:
                    logger.warning("Network health check failed")
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Network health monitor error: {e}")
                await asyncio.sleep(60)
        
    async def run(self):
        """Run the bot"""
        try:
            # Check for process lock first
            if not self._acquire_lock():
                print("❌ Another bot instance is already running!")
                print("💡 Use 'pkill -f \"python main.py\"' to stop all instances")
                return
                
            await self.setup()
            self.register_handlers()
            await self.start_background_tasks()
            
            self.running = True
            logger.info("Starting Solana Trading Bot...")
            print("🚀 Bot is starting...")
            print("📱 Find your bot on Telegram: @PredatonSolana_bot")
            print("💬 Send /start to begin")
            print("⏹️  Press Ctrl+C to stop")
            
            # Run the bot using a more robust approach with network resilience
            print("🔗 Connecting to Telegram API...")
            
            # Configure the updater with better network settings
            # Note: These settings are configured through the Application builder
            
            try:
                logger.info("Initializing Telegram application...")
                await asyncio.wait_for(self.app.initialize(), timeout=60.0)
                logger.info("Starting Telegram application...")
                await asyncio.wait_for(self.app.start(), timeout=60.0)
                logger.info("Starting polling for updates...")
                await asyncio.wait_for(self.app.updater.start_polling(
                    drop_pending_updates=True,
                    bootstrap_retries=10,
                    timeout=30
                ), timeout=60.0)
                print("✅ Connected to Telegram API successfully!")
                logger.info("Telegram API connection successful!")
                
                # Keep the bot running
                logger.info("Bot is now running and listening for updates...")
                while self.running:
                    try:
                        await asyncio.sleep(1)
                    except Exception as e:
                        logger.warning(f"Network monitoring warning: {e}")
                        continue
                    
            except asyncio.TimeoutError:
                logger.error("Timeout connecting to Telegram API")
                print("❌ Timeout connecting to Telegram API. Please check your internet connection.")
                # Retry connection after a delay
                await asyncio.sleep(5)
                logger.info("Retrying connection to Telegram API...")
                raise
            except Exception as e:
                logger.error(f"Error connecting to Telegram API: {e}")
                print(f"❌ Error connecting to Telegram API: {e}")
                # Retry connection after a delay
                await asyncio.sleep(5)
                logger.info("Retrying connection to Telegram API...")
                raise
            
        except Exception as e:
            logger.error(f"Error running bot: {e}")
            print(f"❌ Error: {e}")
        finally:
            await self.cleanup()
            
    async def cleanup(self):
        """Cleanup resources"""
        try:
            self.running = False
            
            if self.app and self.app.updater:
                await self.app.updater.stop()
            if self.app:
                await self.app.stop()
                await self.app.shutdown()
                
            if self.wallet_analyzer:
                await self.wallet_analyzer.stop_monitoring()
            if self.trading_engine:
                await self.trading_engine.stop_monitoring()
            if self.payment_service:
                await self.payment_service.stop_monitoring()
            if self.solana_service:
                await self.solana_service.disconnect()
            if self.db_manager:
                await self.db_manager.disconnect()
                
            # Release process lock
            self._release_lock()
                
            logger.info("Bot cleanup completed")
        except Exception as e:
            logger.error(f"Error in cleanup: {e}")

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    print("\n🛑 Shutting down bot...")
    # Clean up any existing lock files
    try:
        if os.path.exists("/tmp/solana_trading_bot.lock"):
            os.unlink("/tmp/solana_trading_bot.lock")
    except Exception as e:
        print(f"Warning: Could not clean up lock file: {e}")
    sys.exit(0)

async def main():
    """Main function"""
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    bot = SolanaTradingBot()
    await bot.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        logger.error(f"Main error: {e}")

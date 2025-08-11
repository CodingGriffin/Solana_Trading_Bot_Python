"""
Telegram bot handlers with smart button interface and security features
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.helpers import escape_markdown
from telegram.ext import ContextTypes
from services.database import DatabaseManager
from services.solana_service import SolanaService
from services.wallet_analyzer import WalletAnalyzer
from services.trading_engine import TradingEngine
from services.payment_service import PaymentService
from utils.keyboards import create_main_menu, create_wallet_menu, create_trade_menu
from utils.formatters import format_wallet_info, format_trade_info, format_analysis_result
from utils.security import SecurityManager
from config.settings import MAX_REQUESTS_PER_MINUTE, RATE_LIMIT_WINDOW, WALLET_CREATION_FEE, SUBSCRIPTION_TIERS, SUBSCRIPTION_FEE_PERCENTAGE

logger = logging.getLogger(__name__)

class BotHandlers:
    def __init__(self, db_manager: DatabaseManager, solana_service: SolanaService, 
                 wallet_analyzer: WalletAnalyzer, trading_engine: TradingEngine,
                 payment_service: PaymentService, admin_chat_ids: List[int] = None):
        self.db = db_manager
        self.solana = solana_service
        self.analyzer = wallet_analyzer
        self.trading = trading_engine
        self.payment = payment_service
        self.user_states: Dict[int, Dict[str, Any]] = {}
        
        # Initialize security manager
        self.security = SecurityManager(
            max_requests=MAX_REQUESTS_PER_MINUTE,
            window_seconds=RATE_LIMIT_WINDOW,
            admin_chat_ids=admin_chat_ids or []
        )
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user_id = update.effective_user.id
        username = update.effective_user.username or "Unknown"
        
        # Rate limiting check
        rate_ok, rate_msg = self.security.check_rate_limit(user_id)
        if not rate_ok:
            await update.message.reply_text(f"⚠️ {rate_msg}")
            return
        
        # Initialize user in database
        await self.db.create_user(user_id, username)
        
        # Show user ID for admin setup
        user_info = f"👤 *Your Info:*\n🆔 User ID: `{user_id}`\n👤 Username: @{username}\n\n"
        
        welcome_text = (
            "🚀 *Welcome to Solana Trading Bot!*\n\n"
            f"{user_info}"
            "Your advanced Solana wallet analyzer and trading assistant.\n\n"
            "*Features:*\n"
            "📊 Real-time wallet analysis\n"
            "🐋 Whale tracking\n"
            "⚡ Auto-trading & sniping\n"
            "📈 Copy trading\n"
            "🔔 Smart alerts\n\n"
            "Choose an option below to get started:"
        )
        
        keyboard = create_main_menu()
        await update.message.reply_text(
            welcome_text, 
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = (
            "🤖 *Solana Trading Bot Help*\n\n"
            "*Commands:*\n"
            "/start - Start the bot\n"
            "/wallet - Wallet operations\n"
            "/trade - Trading operations\n"
            "/analyze - Analysis tools\n"
            "/settings - Bot settings\n\n"
            "*Features:*\n"
            "• Monitor Solana wallets in real-time\n"
            "• Track whale movements\n"
            "• Execute trades automatically\n"
            "• Copy successful traders\n"
            "• Set custom alerts\n\n"
            "*Support:* @YourSupportBot"
        )
        
        keyboard = create_main_menu()
        await update.message.reply_text(
            help_text,
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        
    async def wallet_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /wallet command"""
        user_id = update.effective_user.id
        
        # Rate limiting check
        rate_ok, rate_msg = self.security.check_rate_limit(user_id)
        if not rate_ok:
            await update.message.reply_text(f"⚠️ {rate_msg}")
            return
        
        # Show wallet operations menu
        keyboard = create_wallet_menu()
        await update.message.reply_text(
            "💼 *Wallet Operations*\n\nChoose an action:",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        
    async def trade_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /trade command"""
        keyboard = create_trade_menu()
        await update.message.reply_text(
            "⚡ *Trading Operations*\n\nChoose an action:",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        
    async def analyze_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /analyze command"""
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔍 Analyze Wallet", callback_data="analyze_wallet")],
            [InlineKeyboardButton("📊 Token Analysis", callback_data="analyze_token")],
            [InlineKeyboardButton("🐋 Whale Tracker", callback_data="whale_tracker")],
            [InlineKeyboardButton("📈 Market Trends", callback_data="market_trends")],
            [InlineKeyboardButton("🔙 Back to Main", callback_data="main_menu")]
        ])
        
        await update.message.reply_text(
            "🔬 *Analysis Tools*\n\nChoose analysis type:",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        
    async def settings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /settings command"""
        user_id = update.effective_user.id
        user_settings = await self.db.get_user_settings(user_id)
        
        settings_text = (
            f"⚙️ *Your Settings*\n\n"
            f"📊 Subscription: {user_settings.get('tier', 'free').title()}\n"
            f"💰 Max Trade Amount: {user_settings.get('max_trade_amount', 1.0)} SOL\n"
            f"📉 Stop Loss: {user_settings.get('stop_loss', 10)}%\n"
            f"🎯 Slippage: {user_settings.get('slippage', 0.5)}%\n"
            f"🔔 Alerts: {'✅' if user_settings.get('alerts_enabled', True) else '❌'}\n"
        )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💎 Upgrade Plan", callback_data="upgrade_plan")],
            [InlineKeyboardButton("⚙️ Trading Settings", callback_data="trading_settings")],
            [InlineKeyboardButton("🔔 Alert Settings", callback_data="alert_settings")],
            [InlineKeyboardButton("🔙 Back to Main", callback_data="main_menu")]
        ])
        
        await update.message.reply_text(
            settings_text,
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        
    async def admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /admin command"""
        user_id = update.effective_user.id
        
        # Check admin privileges
        admin_ok, admin_msg = self.security.require_admin(user_id)
        if not admin_ok:
            await update.message.reply_text(f"❌ {admin_msg}")
            return
        
        # Show admin panel
        await self._show_admin_panel(update.callback_query or update)
        

        
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries"""
        query = update.callback_query
        user_id = query.from_user.id
        
        # Debug logging
        logger.info(f"Callback received: user_id={user_id}, data='{query.data}'")
        
        # Rate limiting check
        rate_ok, rate_msg = self.security.check_rate_limit(user_id)
        if not rate_ok:
            try:
                await query.answer(f"⚠️ {rate_msg}", show_alert=True)
            except Exception as e:
                logger.warning(f"Failed to answer rate limit callback: {e}")
            return
        
        # Answer the callback query immediately to prevent timeout
        try:
            await query.answer()
        except Exception as e:
            logger.warning(f"Failed to answer callback query: {e}")
            # Continue processing even if answer fails
        
        data = query.data
        
        try:
            if data == "main_menu":
                await self._show_main_menu(query)
            elif data == "wallet_operations":
                await self._show_wallet_operations(query)
            elif data == "trading_operations":
                await self._show_trading_operations(query)
            elif data == "add_wallet":
                await self._handle_add_wallet(query, user_id)
            elif data == "monitor_wallets":
                await self._handle_monitor_wallets(query, user_id)
            elif data == "portfolio_view":
                await self._handle_portfolio_view(query, user_id)
            elif data == "whale_alerts":
                await self._handle_whale_alerts(query, user_id)
            elif data == "quick_buy":
                await self._handle_quick_buy(query, user_id)
            elif data == "quick_sell":
                await self._handle_quick_sell(query, user_id)
            elif data == "limit_order":
                await self._handle_limit_order(query, user_id)
            elif data == "copy_trading":
                await self._handle_copy_trading(query, user_id)
            elif data == "analyze_wallet":
                await self._handle_analyze_wallet(query, user_id)
            elif data == "analyze_token":
                await self._handle_analyze_token(query, user_id)
            elif data == "whale_tracker":
                await self._handle_whale_tracker(query, user_id)
            elif data.startswith("wallet_"):
                await self._handle_wallet_action(query, user_id, data)
            elif data == "trade_history":
                await self._handle_trade_history(query, user_id)
            elif data.startswith("trade_"):
                await self._handle_trade_action(query, user_id, data)
            elif data == "help":
                await self._show_help_menu(query)
            elif data == "analysis_tools":
                await self._show_analysis_menu(query)
            elif data == "settings":
                await self._show_settings_menu(query)
            elif data == "upgrade_plan":
                await self._handle_upgrade_plan(query, user_id)
            elif data == "trading_settings":
                await self._handle_trading_settings(query, user_id)
            elif data == "alert_settings":
                await self._handle_alert_settings(query, user_id)
            elif data == "copy_settings":
                await self._handle_copy_settings(query, user_id)
            elif data == "account_stats":
                await self._handle_account_stats(query, user_id)
            elif data.startswith("admin_"):
                await self._handle_admin_action(query, user_id, data)
            elif data == "admin_panel":
                await self._show_admin_panel(query)
            elif data == "sniping_bot":
                await self._handle_sniping_bot(query, user_id)
            elif data == "create_wallet":
                await self._handle_create_wallet_callback(query, user_id)
            elif data == "import_wallet":
                await self._handle_import_wallet_callback(query, user_id)
            elif data == "view_wallets":
                await self._handle_view_wallets_callback(query, user_id)

            elif data == "cancel_import":
                await self._handle_cancel_import(query, user_id)
            elif data == "upgrade_premium":
                await self._handle_upgrade_subscription(query, user_id, "premium")
            elif data == "upgrade_pro":
                await self._handle_upgrade_subscription(query, user_id, "pro")
            elif data == "trade_menu":
                await self._show_trading_operations(query)
            elif data.startswith("confirm_upgrade_"):
                tier = data.replace("confirm_upgrade_", "")
                await self._handle_confirm_upgrade(query, user_id, tier)
            elif data == "connect_trading_wallet":
                await self._handle_connect_trading_wallet(query, user_id)
            elif data == "disconnect_trading_wallet":
                await self._handle_disconnect_trading_wallet(query, user_id)
            elif data == "replace_trading_wallet":
                await self._handle_replace_trading_wallet(query, user_id)
            elif data == "confirm_disconnect_trading_wallet":
                await self._handle_confirm_disconnect_trading_wallet(query, user_id)
            else:
                await query.answer("❌ Unknown command", show_alert=True)
                
        except Exception as e:
            logger.error(f"Error handling callback {data}: {e}")
            try:
                await query.edit_message_text("❌ An error occurred. Please try again.")
            except Exception as edit_error:
                logger.error(f"Failed to edit message after error: {edit_error}")
                # Try to send a new message instead
                try:
                    await context.bot.send_message(
                        chat_id=query.message.chat_id,
                        text="❌ An error occurred. Please try again."
                    )
                except Exception as send_error:
                    logger.error(f"Failed to send error message: {send_error}")

    async def _show_admin_panel(self, query):
        """Show admin panel"""
        admin_text = (
            "🔧 *Admin Panel*\n\n"
            "**System Status:**\n"
            "• Database: ✅ Connected\n"
            "• Solana RPC: ✅ Connected\n"
            "• Trading Engine: ✅ Active\n\n"
            "**Admin Commands:**\n"
            "• /admin status - System health\n"
            "• /admin users - User statistics\n"
            "• /admin restart - Restart services\n"
            "• /admin backup - Create backup\n\n"
            "**Quick Actions:**"
        )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 System Status", callback_data="admin_status")],
            [InlineKeyboardButton("👥 User Stats", callback_data="admin_users")],
            [InlineKeyboardButton("🔄 Restart Services", callback_data="admin_restart")],
            [InlineKeyboardButton("💾 Create Backup", callback_data="admin_backup")]
        ])
        
        await query.edit_message_text(
            admin_text,
            parse_mode='Markdown',
            reply_markup=keyboard
        )
            
    async def _handle_admin_action(self, query, user_id, data):
        """Handle admin actions"""
        logger.info(f"Admin action: user_id={user_id}, data='{data}'")
        
        # Check admin privileges
        admin_ok, admin_msg = self.security.require_admin(user_id)
        if not admin_ok:
            await query.answer(f"❌ {admin_msg}", show_alert=True)
            return
        
        action = data.replace("admin_", "")
        logger.info(f"Processing admin action: '{action}'")
        
        if action == "status":
            await self._show_admin_status(query)
        elif action == "users":
            await self._show_admin_users(query)
        elif action == "restart":
            await self._handle_admin_restart(query)
        elif action == "backup":
            await self._handle_admin_backup(query)
        elif action == "panel":
            await self._show_admin_panel(query)
        else:
            await query.answer("❌ Unknown admin action", show_alert=True)
            

            
    async def _show_admin_status(self, query):
        """Show system status to admin"""
        try:
            # Get basic system info
            status_text = "📊 *System Status*\n\n"
            
            # Database status
            try:
                await self.db.db.command('ping')
                status_text += "🗄️ Database: ✅ Connected\n"
            except:
                status_text += "🗄️ Database: ❌ Disconnected\n"
            
            # Solana status
            try:
                # Simple connection test - just check if client exists and is connected
                if self.solana.rpc_client and hasattr(self.solana.rpc_client, '_provider'):
                    status_text += "🔗 Solana RPC: ✅ Connected\n"
                else:
                    status_text += "🔗 Solana RPC: ❌ Disconnected\n"
            except Exception as e:
                logger.warning(f"Solana RPC check failed: {e}")
                status_text += "🔗 Solana RPC: ❌ Disconnected\n"
            
            # Trading engine status
            if self.trading.is_running:
                status_text += "⚡ Trading Engine: ✅ Active\n"
            else:
                status_text += "⚡ Trading Engine: ❌ Inactive\n"
            
            status_text += "\n**Active Users:** " + str(len(self.user_states))
            status_text += "\n**Monitored Wallets:** " + str(len(self.analyzer.monitored_wallets))
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Refresh", callback_data="admin_status")],
                [InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]
            ])
            
            await query.edit_message_text(
                status_text,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            
        except Exception as e:
            if "Message is not modified" in str(e):
                # Message content is the same, just answer the callback
                await query.answer("✅ Status is current")
            else:
                logger.error(f"Error showing admin status: {e}")
                await query.answer("❌ Error getting status", show_alert=True)
            
    async def _show_admin_users(self, query):
        """Show user statistics to admin"""
        try:
            # Get user count from database
            user_count = await self.db.db.users.count_documents({})
            
            stats_text = "👥 *User Statistics*\n\n"
            stats_text += f"**Total Users:** {user_count}\n"
            stats_text += f"**Active Sessions:** {len(self.user_states)}\n"
            stats_text += f"**Monitored Wallets:** {len(self.analyzer.monitored_wallets)}\n"
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Refresh", callback_data="admin_users")],
                [InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]
            ])
            
            await query.edit_message_text(
                stats_text,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            
        except Exception as e:
            if "Message is not modified" in str(e):
                # Message content is the same, just answer the callback
                await query.answer("✅ User stats are current")
            else:
                logger.error(f"Error showing admin users: {e}")
                await query.answer("❌ Error getting user stats", show_alert=True)
            
    async def _handle_admin_restart(self, query):
        """Handle admin restart request"""
        try:
            await query.answer("🔄 Restarting services...", show_alert=True)
            
            # Restart monitoring services
            await self.analyzer.stop_monitoring()
            await self.trading.stop_monitoring()
            
            await asyncio.sleep(2)
            
            await self.analyzer.start_monitoring()
            await self.trading.start_monitoring()
            
            await query.edit_message_text(
                "✅ *Services Restarted Successfully*\n\n"
                "• Wallet monitoring restarted\n"
                "• Trading engine restarted\n"
                "• All services are now active",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_panel")]
                ])
            )
            
        except Exception as e:
            logger.error(f"Error restarting services: {e}")
            await query.answer("❌ Error restarting services", show_alert=True)
            
    async def _handle_admin_backup(self, query):
        """Handle admin backup request"""
        try:
            await query.answer("💾 Creating backup...", show_alert=True)
            
            # Create backup timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"solana_bot_backup_{timestamp}"
            
            # Create comprehensive backup
            backup_data = await self._create_backup_data()
            
            # Save backup to database
            backup_id = await self.db.store_backup(backup_name, backup_data)
            
            if backup_id:
                # Create backup summary
                summary = self._create_backup_summary(backup_data)
                
                await query.edit_message_text(
                    f"✅ *Backup Created Successfully*\n\n"
                    f"**Backup Name:** {backup_name}\n"
                    f"**Backup ID:** {backup_id}\n"
                    f"**Status:** Completed\n\n"
                    f"**Backup Summary:**\n{summary}\n\n"
                    f"*Backup data has been stored securely in the database.*",
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📊 View Backups", callback_data="admin_backups")],
                        [InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_panel")]
                    ])
                )
            else:
                await query.edit_message_text(
                    "❌ *Backup Failed*\n\n"
                    "Failed to create backup. Please try again.",
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_panel")]
                    ])
                )
            
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            await query.answer("❌ Error creating backup", show_alert=True)
            
    async def _create_backup_data(self) -> Dict[str, Any]:
        """Create comprehensive backup data"""
        try:
            backup_data = {
                'timestamp': datetime.utcnow(),
                'version': '1.0',
                'database_stats': {},
                'system_stats': {},
                'user_stats': {},
                'trading_stats': {}
            }
            
            # Database statistics
            backup_data['database_stats'] = {
                'total_users': await self.db.db.users.count_documents({}),
                'total_trades': await self.db.db.trades.count_documents({}),
                'total_wallets': await self.db.db.wallets.count_documents({}),
                'total_transactions': await self.db.db.transactions.count_documents({}),
                'total_alerts': await self.db.db.alerts.count_documents({})
            }
            
            # System statistics
            backup_data['system_stats'] = {
                'monitored_wallets': len(self.analyzer.monitored_wallets),
                'active_orders': len(self.trading.active_orders),
                'copy_trading_subscriptions': len(self.trading.copy_trading_subscriptions)
            }
            
            # User statistics
            user_stats = await self.db.get_user_statistics()
            backup_data['user_stats'] = user_stats
            
            # Trading statistics
            trading_stats = await self.db.get_trading_statistics()
            backup_data['trading_stats'] = trading_stats
            
            return backup_data
            
        except Exception as e:
            logger.error(f"Error creating backup data: {e}")
            return {'error': str(e)}
            
    def _create_backup_summary(self, backup_data: Dict[str, Any]) -> str:
        """Create human-readable backup summary"""
        try:
            db_stats = backup_data.get('database_stats', {})
            sys_stats = backup_data.get('system_stats', {})
            
            summary = (
                f"• Users: {db_stats.get('total_users', 0)}\n"
                f"• Trades: {db_stats.get('total_trades', 0)}\n"
                f"• Wallets: {db_stats.get('total_wallets', 0)}\n"
                f"• Transactions: {db_stats.get('total_transactions', 0)}\n"
                f"• Monitored Wallets: {sys_stats.get('monitored_wallets', 0)}\n"
                f"• Active Orders: {sys_stats.get('active_orders', 0)}\n"
                f"• Copy Trading Subscriptions: {sys_stats.get('copy_trading_subscriptions', 0)}"
            )
            
            return summary
            
        except Exception as e:
            logger.error(f"Error creating backup summary: {e}")
            return "Error creating summary"

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages based on user state"""
        user_id = update.effective_user.id
        message_text = update.message.text
        
        # Rate limiting check
        rate_ok, rate_msg = self.security.check_rate_limit(user_id)
        if not rate_ok:
            await update.message.reply_text(f"⚠️ {rate_msg}")
            return
        
        # Sanitize user input
        message_text = self.security.sanitize_user_input(message_text)
        

        
        user_state = self.user_states.get(user_id, {})
        current_state = user_state.get('state')
        
        if current_state == 'waiting_wallet_address':
            await self._process_wallet_address(update, user_id, message_text)
        elif current_state == 'waiting_token_address':
            await self._process_token_address(update, user_id, message_text)
        elif current_state == 'waiting_trade_amount':
            await self._process_trade_amount(update, user_id, message_text)
        elif current_state in ['waiting_for_private_key', 'waiting_wallet_amount', 'waiting_upgrade_amount', 'waiting_for_trading_wallet_key']:
            # Handle wallet-related messages
            await self.handle_wallet_message(update, user_id, message_text)
        else:
            # Default response
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")],
                [InlineKeyboardButton("❓ Help", callback_data="help")]
            ])
            await update.message.reply_text(
                "🤖 *Solana Trading Bot*\n\nPlease use the menu buttons below or type /start to begin:",
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            
    async def _show_main_menu(self, query):
        """Show main menu"""
        # Clear user state when returning to main menu
        user_id = query.from_user.id
        if user_id in self.user_states:
            del self.user_states[user_id]
            
        keyboard = create_main_menu()
        welcome_text = (
            "🚀 *Welcome to Solana Trading Bot!*\n\n"
            "Your advanced Solana wallet analyzer and trading assistant.\n\n"
            "*Features:*\n"
            "📊 Real-time wallet analysis\n"
            "🐋 Whale tracking\n"
            "⚡ Auto-trading & sniping\n"
            "📈 Copy trading\n"
            "🔔 Smart alerts\n\n"
            "Choose an option below to get started:"
        )
        await query.edit_message_text(
            welcome_text,
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        
    async def _show_wallet_operations(self, query):
        """Show wallet operations menu"""
        # Clear user state when returning to wallet operations
        user_id = query.from_user.id
        if user_id in self.user_states:
            del self.user_states[user_id]
            
        keyboard = create_wallet_menu()
        await query.edit_message_text(
            "💼 *Wallet Operations*\n\nChoose an action:",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        
    async def _show_trading_operations(self, query):
        """Show trading operations menu"""
        # Clear user state when returning to trading operations
        user_id = query.from_user.id
        if user_id in self.user_states:
            del self.user_states[user_id]
            
        keyboard = create_trade_menu()
        await query.edit_message_text(
            "⚡ *Trading Operations*\n\nChoose an action:",
            parse_mode='Markdown',
            reply_markup=keyboard
        )

    async def _show_help_menu(self, query):
        """Show help menu"""
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
        ])
        await query.edit_message_text(
            "❓ *Help & Support*\n\n"
            "*Commands:*\n"
            "/start - Start the bot\n"
            "/help - Show this help\n"
            "/wallet - Wallet operations\n"
            "/trade - Trading operations\n"
            "/analyze - Analysis tools\n"
            "/settings - Bot settings\n\n"
            "*Features:*\n"
            "• Monitor Solana wallets in real-time\n"
            "• Track whale movements\n"
            "• Execute trades automatically\n"
            "• Copy successful traders\n"
            "• Set custom alerts\n\n"
            "*Support:* @YourSupportBot",
            parse_mode='Markdown',
            reply_markup=keyboard
        )

    async def _show_analysis_menu(self, query):
        """Show analysis tools menu"""
        # Clear user state when returning to analysis menu
        user_id = query.from_user.id
        if user_id in self.user_states:
            del self.user_states[user_id]
            
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔍 Analyze Wallet", callback_data="analyze_wallet")],
            [InlineKeyboardButton("📊 Token Analysis", callback_data="analyze_token")],
            [InlineKeyboardButton("🐋 Whale Tracker", callback_data="whale_tracker")],
            [InlineKeyboardButton("📈 Market Trends", callback_data="market_trends")],
            [InlineKeyboardButton("🎯 Top Performers", callback_data="top_performers")],
            [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
        ])
        await query.edit_message_text(
            "🔬 *Analysis Tools*\n\nChoose analysis type:",
            parse_mode='Markdown',
            reply_markup=keyboard
        )

    async def _show_settings_menu(self, query):
        """Show settings menu"""
        user_id = query.from_user.id
        user_settings = await self.db.get_user_settings(user_id)
        
        settings_text = (
            f"⚙️ *Your Settings*\n\n"
            f"📊 Subscription: {user_settings.get('tier', 'free').title()}\n"
            f"💰 Max Trade Amount: {user_settings.get('max_trade_amount', 1.0)} SOL\n"
            f"📉 Stop Loss: {user_settings.get('stop_loss', 10)}%\n"
            f"🎯 Slippage: {user_settings.get('slippage', 0.5)}%\n"
            f"🔔 Alerts: {'✅' if user_settings.get('alerts_enabled', True) else '❌'}\n"
        )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💎 Upgrade Plan", callback_data="upgrade_plan")],
            [InlineKeyboardButton("⚙️ Trading Settings", callback_data="trading_settings")],
            [InlineKeyboardButton("🔔 Alert Settings", callback_data="alert_settings")],
            [InlineKeyboardButton("🔄 Copy Trading Settings", callback_data="copy_settings")],
            [InlineKeyboardButton("📊 Account Stats", callback_data="account_stats")],
            [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
        ])
        
        await query.edit_message_text(
            settings_text,
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        
    async def _handle_add_wallet(self, query, user_id):
        """Handle add wallet request"""
        self.user_states[user_id] = {'state': 'waiting_wallet_address'}
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="wallet_operations")]
        ])
        await query.edit_message_text(
            "📝 *Add Wallet to Monitor*\n\n"
            "Please send the Solana wallet address you want to monitor:\n\n"
            "Example: `DRpbCBMxVnDK7maPM5tGv6MvB3v1sRMC86PZ8okm21hy`",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        
    async def _handle_monitor_wallets(self, query, user_id):
        """Show monitored wallets"""
        wallets = await self.db.get_user_wallets(user_id)
        
        if not wallets:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Add Wallet", callback_data="add_wallet")],
                [InlineKeyboardButton("🔙 Back", callback_data="wallet_operations")]
            ])
            await query.edit_message_text(
                "📭 *No Wallets Monitored*\n\n"
                "You haven't added any wallets to monitor yet.",
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            return
            
        wallet_text = "📊 *Monitored Wallets*\n\n"
        buttons = []
        
        for i, wallet in enumerate(wallets[:10]):  # Show max 10
            wallet_info = await self.analyzer.get_wallet_summary(wallet['address'])
            wallet_text += f"{i+1}. `{wallet['address'][:8]}...{wallet['address'][-8:]}`\n"
            wallet_text += f"   💰 Balance: {wallet_info.get('sol_balance', 0):.2f} SOL\n"
            wallet_text += f"   📈 24h Change: {wallet_info.get('change_24h', 0):+.2f}%\n\n"
            
            buttons.append([InlineKeyboardButton(
                f"📊 {wallet['address'][:8]}...", 
                callback_data=f"wallet_details_{wallet['address']}"
            )])
            
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="wallet_operations")])
        keyboard = InlineKeyboardMarkup(buttons)
        
        await query.edit_message_text(
            wallet_text,
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        
    async def _handle_portfolio_view(self, query, user_id):
        """Show portfolio view"""
        try:
            # Get user's monitored wallets
            wallets = await self.db.get_user_wallets(user_id)
            
            if not wallets:
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("➕ Add Wallet", callback_data="add_wallet")],
                    [InlineKeyboardButton("🔙 Back", callback_data="wallet_operations")]
                ])
                await query.edit_message_text(
                    "📭 *No Portfolio Data*\n\n"
                    "You haven't added any wallets to monitor yet.\n"
                    "Add wallets to see your portfolio overview.",
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
                return
            
            # Calculate portfolio summary
            total_sol_balance = 0
            total_usd_value = 0
            portfolio_text = "📈 *Portfolio Overview*\n\n"
            
            for i, wallet in enumerate(wallets[:10], 1):  # Show max 10
                try:
                    wallet_info = await self.analyzer.get_wallet_summary(wallet['address'])
                    sol_balance = wallet_info.get('sol_balance', 0)
                    usd_value = wallet_info.get('total_usd_value', 0)
                    
                    total_sol_balance += sol_balance
                    total_usd_value += usd_value
                    
                    portfolio_text += f"{i}. `{wallet['address'][:8]}...{wallet['address'][-8:]}`\n"
                    portfolio_text += f"   💰 {sol_balance:.4f} SOL (${usd_value:,.2f})\n"
                    
                    # Add 24h change if available
                    change_24h = wallet_info.get('change_24h', 0)
                    if change_24h != 0:
                        change_emoji = "📈" if change_24h > 0 else "📉"
                        portfolio_text += f"   {change_emoji} 24h: {change_24h:+.2f}%\n"
                    
                    portfolio_text += "\n"
                    
                except Exception as e:
                    logger.error(f"Error getting wallet info for {wallet['address']}: {e}")
                    portfolio_text += f"{i}. `{wallet['address'][:8]}...{wallet['address'][-8:]}`\n"
                    portfolio_text += f"   ❌ Error loading data\n\n"
            
            # Add portfolio summary
            portfolio_text += f"📊 *Portfolio Summary*\n"
            portfolio_text += f"💰 Total SOL: {total_sol_balance:.4f} SOL\n"
            portfolio_text += f"💵 Total Value: ${total_usd_value:,.2f}\n"
            portfolio_text += f"📋 Wallets: {len(wallets)}\n"
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Refresh", callback_data="portfolio_view")],
                [InlineKeyboardButton("📊 Detailed View", callback_data="portfolio_detailed")],
                [InlineKeyboardButton("🔙 Back", callback_data="wallet_operations")]
            ])
            
            await query.edit_message_text(
                portfolio_text,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            
        except Exception as e:
            logger.error(f"Error in portfolio view: {e}")
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="wallet_operations")]
            ])
            await query.edit_message_text(
                "❌ Error loading portfolio data. Please try again.",
                parse_mode='Markdown',
                reply_markup=keyboard
            )
        
    async def _handle_whale_alerts(self, query, user_id):
        """Show whale alerts"""
        recent_whales = await self.analyzer.get_recent_whale_activity(limit=5)
        
        if not recent_whales:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Refresh", callback_data="whale_alerts")],
                [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
            ])
            await query.edit_message_text(
                "🐋 *Whale Activity*\n\n"
                "No recent whale activity detected.",
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            return
            
        whale_text = "🐋 *Recent Whale Activity*\n\n"
        
        for whale in recent_whales:
            whale_text += f"💰 **{whale['amount']:.2f} SOL**\n"
            whale_text += f"📍 `{whale['wallet'][:8]}...{whale['wallet'][-8:]}`\n"
            whale_text += f"🎯 {whale['action'].title()}: {whale['token_symbol']}\n"
            whale_text += f"⏰ {whale['timestamp']}\n\n"
            
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Refresh", callback_data="whale_alerts")],
            [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
        ])
        
        await query.edit_message_text(
            whale_text,
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        
    async def _process_wallet_address(self, update, user_id, address):
        """Process wallet address input"""
        try:
            # Security validation
            valid, error_msg = self.security.validate_wallet_address(address)
            if not valid:
                await update.message.reply_text(f"❌ {error_msg}")
                return
            
            # Additional Solana validation
            if not await self.solana.validate_address(address):
                await update.message.reply_text(
                    "❌ Invalid Solana address. Please try again."
                )
                return
                
            # Add wallet to monitoring
            await self.db.add_user_wallet(user_id, address)
            
            # Start monitoring
            await self.analyzer.add_wallet_monitor(address, user_id)
            
            # Clear user state
            if user_id in self.user_states:
                del self.user_states[user_id]
                
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📊 View Wallet", callback_data=f"wallet_details_{address}")],
                [InlineKeyboardButton("➕ Add Another", callback_data="add_wallet")],
                [InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]
            ])
            
            await update.message.reply_text(
                f"✅ *Wallet Added Successfully!*\n\n"
                f"📍 Address: `{address}`\n"
                f"🔔 You'll receive alerts for this wallet's activity.",
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            
        except Exception as e:
            logger.error(f"Error processing wallet address: {e}")
            await update.message.reply_text(
                "❌ Error adding wallet. Please try again."
            )

    async def _handle_quick_buy(self, query, user_id):
        """Handle quick buy request"""
        # Set user state to waiting for token address
        self.user_states[user_id] = {'state': 'waiting_token_address', 'action': 'quick_buy'}
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="trading_operations")]
        ])
        await query.edit_message_text(
            "🟢 *Quick Buy*\n\n"
            "Please enter the token address you want to buy:\n\n"
            "Example: `EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v`\n\n"
            "Or send the token address in the next message.",
            parse_mode='Markdown',
            reply_markup=keyboard
        )

    async def _handle_quick_sell(self, query, user_id):
        """Handle quick sell request"""
        # Set user state to waiting for token address
        self.user_states[user_id] = {'state': 'waiting_token_address', 'action': 'quick_sell'}
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="trading_operations")]
        ])
        await query.edit_message_text(
            "🔴 *Quick Sell*\n\n"
            "Please enter the token address you want to sell:\n\n"
            "Example: `EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v`\n\n"
            "Or send the token address in the next message.",
            parse_mode='Markdown',
            reply_markup=keyboard
        )

    async def _handle_limit_order(self, query, user_id):
        """Handle limit order request"""
        # Set user state to waiting for token address
        self.user_states[user_id] = {'state': 'waiting_token_address', 'action': 'limit_order'}
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="trading_operations")]
        ])
        await query.edit_message_text(
            "📋 *Limit Orders*\n\n"
            "Please enter the token address for your limit order:\n\n"
            "Example: `EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v`\n\n"
            "Or send the token address in the next message.",
            parse_mode='Markdown',
            reply_markup=keyboard
        )

    async def _handle_copy_trading(self, query, user_id):
        """Handle copy trading request"""
        try:
            # Get user's copy trading settings
            user_settings = await self.db.get_user_settings(user_id)
            copy_settings = user_settings.get('copy_trading', {})
            
            # Get active copy trading wallets
            copy_wallets = copy_settings.get('active_wallets', [])
            
            # Get copy trading statistics
            copy_stats = await self.db.get_user_copy_stats(user_id)
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Add Trader", callback_data="add_copy_trader")],
                [InlineKeyboardButton("📊 Copy Stats", callback_data="copy_stats")],
                [InlineKeyboardButton("⚙️ Settings", callback_data="copy_settings")],
                [InlineKeyboardButton("🔙 Back", callback_data="trading_operations")]
            ])
            
            status = "🟢 Active" if copy_settings.get('enabled', False) else "🔴 Inactive"
            
            await query.edit_message_text(
                f"🔄 *Copy Trading*\n\n"
                f"**Status:** {status}\n"
                f"**Active Traders:** {len(copy_wallets)}\n"
                f"**Total Copied Trades:** {copy_stats.get('total_trades', 0)}\n"
                f"**Success Rate:** {copy_stats.get('success_rate', 0):.1f}%\n"
                f"**Total Profit:** {copy_stats.get('total_profit', 0):.4f} SOL\n\n"
                f"Choose an option below:",
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            
        except Exception as e:
            logger.error(f"Error in copy trading menu: {e}")
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="trading_operations")]
            ])
            await query.edit_message_text(
                "❌ Error loading copy trading menu. Please try again.",
                reply_markup=keyboard
            )

    async def _handle_analyze_wallet(self, query, user_id):
        """Handle wallet analysis request"""
        # Set user state to waiting for wallet address
        self.user_states[user_id] = {'state': 'waiting_wallet_address', 'action': 'analyze'}
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="wallet_operations")]
        ])
        await query.edit_message_text(
            "🔍 *Wallet Analysis*\n\n"
            "Please enter the wallet address you want to analyze:\n\n"
            "Example: `9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM`\n\n"
            "Or send the wallet address in the next message.",
            parse_mode='Markdown',
            reply_markup=keyboard
        )

    async def _handle_analyze_token(self, query, user_id):
        """Handle token analysis request"""
        # Set user state to waiting for token address
        self.user_states[user_id] = {'state': 'waiting_token_address', 'action': 'analyze_token'}
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="analysis_tools")]
        ])
        await query.edit_message_text(
            "📊 *Token Analysis*\n\n"
            "Please enter the token address you want to analyze:\n\n"
            "Example: `EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v`\n\n"
            "Or send the token address in the next message.",
            parse_mode='Markdown',
            reply_markup=keyboard
        )

    async def _handle_whale_tracker(self, query, user_id):
        """Handle whale tracker request"""
        try:
            # Get recent whale activity
            whale_activity = await self.db.get_recent_whale_activity(limit=10)
            
            # Get whale statistics
            whale_stats = await self.db.get_whale_statistics()
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📊 Whale Stats", callback_data="whale_stats")],
                [InlineKeyboardButton("🔔 Whale Alerts", callback_data="whale_alerts")],
                [InlineKeyboardButton("⚙️ Settings", callback_data="whale_settings")],
                [InlineKeyboardButton("🔙 Back", callback_data="analysis_tools")]
            ])
            
            # Format recent whale activity
            activity_text = ""
            for i, activity in enumerate(whale_activity[:5], 1):
                wallet = activity.get('wallet_address', 'Unknown')[:8] + "..."
                amount = activity.get('amount', 0)
                activity_text += f"{i}. `{wallet}` - {amount:.2f} SOL\n"
            
            if not activity_text:
                activity_text = "No recent whale activity detected."
            
            await query.edit_message_text(
                f"🐋 *Whale Tracker*\n\n"
                f"**Recent Whale Activity:**\n{activity_text}\n"
                f"**Total Whales Tracked:** {whale_stats.get('total_whales', 0)}\n"
                f"**Large Transactions Today:** {whale_stats.get('today_transactions', 0)}\n"
                f"**Average Transaction Size:** {whale_stats.get('avg_transaction_size', 0):.2f} SOL\n\n"
                f"Choose an option below:",
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            
        except Exception as e:
            logger.error(f"Error in whale tracker: {e}")
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="analysis_tools")]
            ])
            await query.edit_message_text(
                "❌ Error loading whale tracker. Please try again.",
                reply_markup=keyboard
            )

    async def _handle_wallet_action(self, query, user_id, data):
        """Handle wallet-specific actions"""
        try:
            # Extract wallet address from callback data
            if data.startswith("wallet_details_"):
                wallet_address = data.replace("wallet_details_", "")
                
                # Get detailed wallet information
                wallet_info = await self.analyzer.get_wallet_summary(wallet_address)
                
                # Get recent transactions
                recent_transactions = await self.solana.get_wallet_transactions(wallet_address, limit=10)
                
                # Format wallet details
                wallet_text = f"💼 *Wallet Details*\n\n"
                wallet_text += f"📍 Address: `{wallet_address}`\n"
                wallet_text += f"💰 SOL Balance: {wallet_info.get('sol_balance', 0):.4f} SOL\n"
                wallet_text += f"💵 Total Value: ${wallet_info.get('total_usd_value', 0):,.2f}\n"
                
                if wallet_info.get('is_whale'):
                    wallet_text += f"🐋 Status: **WHALE WALLET**\n"
                
                # Add analysis scores if available
                risk_score = wallet_info.get('risk_score', 0)
                profit_score = wallet_info.get('profit_score', 0)
                if risk_score > 0 or profit_score > 0:
                    wallet_text += f"\n📊 *Analysis Scores*\n"
                    wallet_text += f"⚠️ Risk Score: {risk_score}/100\n"
                    wallet_text += f"📈 Profit Score: {profit_score}/100\n"
                
                # Add recent transactions
                if recent_transactions:
                    wallet_text += f"\n📋 *Recent Transactions*\n"
                    for i, tx in enumerate(recent_transactions[:5], 1):
                        tx_type = tx.get('type', 'unknown').title()
                        amount = tx.get('amount', 0)
                        timestamp = tx.get('block_time', 0)
                        
                        if timestamp:
                            tx_time = datetime.fromtimestamp(timestamp).strftime('%H:%M')
                        else:
                            tx_time = "Unknown"
                        
                        wallet_text += f"{i}. {tx_type}: {amount:.4f} SOL ({tx_time})\n"
                
                # Create action buttons
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("📊 Full Analysis", callback_data=f"analyze_wallet_{wallet_address}")],
                    [InlineKeyboardButton("📋 All Transactions", callback_data=f"transactions_{wallet_address}")],
                    [InlineKeyboardButton("🔔 Set Alerts", callback_data=f"alerts_{wallet_address}")],
                    [InlineKeyboardButton("❌ Remove Monitor", callback_data=f"remove_wallet_{wallet_address}")],
                    [InlineKeyboardButton("🔙 Back to Wallets", callback_data="monitor_wallets")]
                ])
                
                await query.edit_message_text(
                    wallet_text,
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
                
            elif data.startswith("analyze_wallet_"):
                wallet_address = data.replace("analyze_wallet_", "")
                await self._show_wallet_analysis(query, user_id, wallet_address)
                
            elif data.startswith("transactions_"):
                wallet_address = data.replace("transactions_", "")
                await self._show_wallet_transactions(query, user_id, wallet_address)
                
            elif data.startswith("alerts_"):
                wallet_address = data.replace("alerts_", "")
                await self._show_wallet_alerts(query, user_id, wallet_address)
                
            elif data.startswith("remove_wallet_"):
                wallet_address = data.replace("remove_wallet_", "")
                await self._remove_wallet_monitor(query, user_id, wallet_address)
                
            elif data.startswith("copy_wallet_"):
                wallet_address = data.replace("copy_wallet_", "")
                await self._handle_copy_wallet_setup(query, user_id, wallet_address)
                
            elif data.startswith("whale_activity_"):
                wallet_address = data.replace("whale_activity_", "")
                await self._show_whale_activity(query, user_id, wallet_address)
                
            else:
                # Generic wallet action
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data="wallet_operations")]
                ])
                await query.edit_message_text(
                    f"💼 *Wallet Action*\n\n"
                    f"Action: {data}\n"
                    f"Feature coming soon!",
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
                
        except Exception as e:
            logger.error(f"Error handling wallet action {data}: {e}")
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="monitor_wallets")]
            ])
            await query.edit_message_text(
                "❌ Error loading wallet details. Please try again.",
                reply_markup=keyboard
            )

    async def _handle_trade_action(self, query, user_id, data):
        """Handle trade-specific actions"""
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="trading_operations")]
        ])
        await query.edit_message_text(
            f"⚡ *Trade Action*\n\n"
            f"Action: {data}\n"
            f"Feature coming soon!",
            parse_mode='Markdown',
            reply_markup=keyboard
        )

    async def _process_token_address(self, update, user_id, address):
        """Process token address input"""
        try:
            user_state = self.user_states.get(user_id, {})
            action = user_state.get('action', 'analyze_token')
            
            # Security validation
            valid, error_msg = self.security.validate_wallet_address(address)
            if not valid:
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data="trading_operations")]
                ])
                await update.message.reply_text(f"❌ {error_msg}", reply_markup=keyboard)
                return
            
            # Additional Solana validation
            if not self.solana.is_valid_address(address):
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data="trading_operations")]
                ])
                await update.message.reply_text(
                    "❌ Invalid token address. Please enter a valid Solana token address.",
                    reply_markup=keyboard
                )
                return
            
            if action == 'analyze_token':
                await self._analyze_token_address(update, user_id, address)
            elif action == 'quick_buy':
                await self._process_quick_buy(update, user_id, address)
            elif action == 'quick_sell':
                await self._process_quick_sell(update, user_id, address)
            elif action == 'limit_order':
                await self._process_limit_order(update, user_id, address)
            else:
                await self._analyze_token_address(update, user_id, address)
                
        except Exception as e:
            logger.error(f"Error processing token address: {e}")
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="trading_operations")]
            ])
            await update.message.reply_text(
                "❌ Error processing token address. Please try again.",
                reply_markup=keyboard
            )
        finally:
            # Clear user state
            self.user_states.pop(user_id, None)

    async def _process_trade_amount(self, update, user_id, amount):
        """Process trade amount input"""
        try:
            user_state = self.user_states.get(user_id, {})
            action = user_state.get('action', 'trade')
            token_address = user_state.get('token_address')
            
            # Security validation
            try:
                amount_float = float(amount)
                valid, error_msg = self.security.validate_trade_params(amount_float, 1.0)  # Default slippage
                if not valid:
                    keyboard = InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Back", callback_data="trading_operations")]
                    ])
                    await update.message.reply_text(f"❌ {error_msg}", reply_markup=keyboard)
                    return
            except ValueError:
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data="trading_operations")]
                ])
                await update.message.reply_text(
                    "❌ Invalid amount. Please enter a valid positive number.",
                    reply_markup=keyboard
                )
                return
            
            if action == 'quick_buy':
                await self._execute_quick_buy(update, user_id, token_address, amount_float)
            elif action == 'quick_sell':
                await self._execute_quick_sell(update, user_id, token_address, amount_float)
            elif action == 'limit_order':
                await self._execute_limit_order(update, user_id, token_address, amount_float)
            else:
                await self._execute_trade(update, user_id, token_address, amount_float)
                
        except Exception as e:
            logger.error(f"Error processing trade amount: {e}")
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="trading_operations")]
            ])
            await update.message.reply_text(
                "❌ Error processing trade amount. Please try again.",
                reply_markup=keyboard
            )
        finally:
            # Clear user state
            self.user_states.pop(user_id, None)

    async def _handle_upgrade_plan(self, query, user_id):
        """Handle upgrade plan callback"""
        try:
            # Get user subscription
            user = await self.db.get_user(user_id)
            current_tier = user.get('subscription_tier', 'free')
            
            upgrade_text = "💎 *Monthly Subscription Plans*\n\n"
            
            for tier_name, tier_data in SUBSCRIPTION_TIERS.items():
                if tier_name == current_tier:
                    upgrade_text += f"✅ **{tier_name.upper()}** (Current Plan)\n"
                else:
                    upgrade_text += f"🔹 **{tier_name.upper()}**\n"
                
                upgrade_text += f"💰 {tier_data['monthly_fee']} SOL/month\n"
                upgrade_text += f"📊 {tier_data['max_wallets']} wallets\n"
                upgrade_text += f"🔔 {tier_data['max_alerts']} alerts\n"
                upgrade_text += f"✨ {', '.join(tier_data['features'])}\n\n"
            
            upgrade_text += "💡 *All plans include automatic fee deduction from your wallet balance.*"
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("💎 Upgrade to Premium", callback_data="upgrade_premium")],
                [InlineKeyboardButton("💎 Upgrade to Pro", callback_data="upgrade_pro")],
                [InlineKeyboardButton("🔙 Back", callback_data="settings")]
            ])
            
            await query.edit_message_text(
                upgrade_text,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            
        except Exception as e:
            logger.error(f"Error in upgrade plan callback: {e}")
            await query.edit_message_text(
                "❌ *Error*\n\nAn error occurred. Please try again.",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data="settings")]
                ])
            )

    async def _handle_confirm_upgrade(self, query, user_id, tier):
        """Handle confirm upgrade callback"""
        try:
            # Get user subscription
            user = await self.db.get_user(user_id)
            current_tier = user.get('subscription_tier', 'free')
            
            if current_tier == tier:
                await query.edit_message_text(
                    f"✅ *Already {tier.upper()}*\n\n"
                    f"You are already subscribed to the {tier} plan.",
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Back", callback_data="upgrade_plan")]
                    ])
                )
                return
            
            # Get subscription tier info
            tier_data = SUBSCRIPTION_TIERS[tier]
            monthly_fee = tier_data['monthly_fee']
            
            if monthly_fee == 0:
                # Free tier - just upgrade
                success, message = await self.payment.process_subscription_payment(user_id, tier)
                
                if success:
                    success_text = (
                        f"✅ *Upgraded to {tier.upper()}!*\n\n"
                        f"Your subscription has been upgraded successfully.\n\n"
                        f"✨ **New Features:**\n"
                        f"• {tier_data['max_wallets']} wallets\n"
                        f"• {tier_data['max_alerts']} alerts\n"
                        f"• {', '.join(tier_data['features'])}\n\n"
                        f"Enjoy your new features!"
                    )
                    
                    keyboard = InlineKeyboardMarkup([
                        [InlineKeyboardButton("💼 View Wallets", callback_data="view_wallets")],
                        [InlineKeyboardButton("⚡ Start Trading", callback_data="trading_operations")],
                        [InlineKeyboardButton("🔙 Back", callback_data="settings")]
                    ])
                    
                    await query.edit_message_text(
                        success_text,
                        parse_mode='Markdown',
                        reply_markup=keyboard
                    )
                else:
                    await query.edit_message_text(
                        f"❌ *Upgrade Failed*\n\n{message}",
                        parse_mode='Markdown',
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🔄 Try Again", callback_data=f"upgrade_{tier}")],
                            [InlineKeyboardButton("🔙 Back", callback_data="upgrade_plan")]
                        ])
                    )
                return
            
            # Check user's wallet balance
            user_wallet = await self.db.get_user_primary_wallet(user_id)
            if not user_wallet:
                await query.edit_message_text(
                    "❌ *No Wallet Found*\n\n"
                    "You need to create or import a wallet first to upgrade your subscription.",
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("💼 Create Wallet", callback_data="create_wallet")],
                        [InlineKeyboardButton("🔙 Back", callback_data="upgrade_plan")]
                    ])
                )
                return
            
            # Get wallet balance
            balance = await self.solana.get_wallet_balance(user_wallet['address'])
            sol_balance = balance.get('sol_balance', 0)
            
            # Calculate total payment needed
            transaction_fee = monthly_fee * (SUBSCRIPTION_FEE_PERCENTAGE / 100)
            total_payment = monthly_fee + transaction_fee
            
            if sol_balance < total_payment:
                await query.edit_message_text(
                    f"❌ *Insufficient Balance*\n\n"
                    f"You need at least {total_payment:.4f} SOL to upgrade to {tier.upper()}.\n\n"
                    f"💰 **Breakdown:**\n"
                    f"• Monthly fee: {monthly_fee:.4f} SOL\n"
                    f"• Transaction fee: {transaction_fee:.4f} SOL\n"
                    f"• Total: {total_payment:.4f} SOL\n\n"
                    f"Current balance: {sol_balance:.4f} SOL",
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("💼 View Wallets", callback_data="view_wallets")],
                        [InlineKeyboardButton("🔙 Back", callback_data="upgrade_plan")]
                    ])
                )
                return
            
            # Show confirmation with fee details
            confirm_text = (
                f"💎 *Confirm {tier.upper()} Upgrade*\n\n"
                f"**Monthly Fee:** {monthly_fee} SOL\n"
                f"**Transaction Fee:** {transaction_fee:.4f} SOL\n"
                f"**Total Payment:** {total_payment:.4f} SOL\n\n"
                f"**Features:**\n"
                f"• {tier_data['max_wallets']} wallets\n"
                f"• {tier_data['max_alerts']} alerts\n"
                f"• {', '.join(tier_data['features'])}\n\n"
                f"💡 *Fee will be automatically deducted from your wallet.*"
            )
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("💎 Confirm Upgrade", callback_data=f"confirm_upgrade_{tier}")],
                [InlineKeyboardButton("🔙 Back", callback_data="upgrade_plan")]
            ])
            
            await query.edit_message_text(
                confirm_text,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            
        except Exception as e:
            logger.error(f"Error in confirm upgrade callback: {e}")
            await query.edit_message_text(
                "❌ *Error*\n\nAn error occurred while processing your upgrade. Please try again.",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Try Again", callback_data=f"upgrade_{tier}")],
                    [InlineKeyboardButton("🔙 Back", callback_data="upgrade_plan")]
                ])
            )

    async def _handle_trading_settings(self, query, user_id):
        """Handle trading settings request"""
        try:
            # Get user's trading settings
            user_settings = await self.db.get_user_settings(user_id)
            trading_settings = user_settings.get('trading', {})
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("💰 Max Trade Amount", callback_data="set_max_amount")],
                [InlineKeyboardButton("🛑 Stop Loss", callback_data="set_stop_loss")],
                [InlineKeyboardButton("📊 Slippage", callback_data="set_slippage")],
                [InlineKeyboardButton("⚡ Auto Trading", callback_data="toggle_auto_trading")],
                [InlineKeyboardButton("🔙 Back", callback_data="settings")]
            ])
            
            auto_trading_status = "🟢 Enabled" if trading_settings.get('auto_trading', False) else "🔴 Disabled"
            
            await query.edit_message_text(
                f"⚙️ *Trading Settings*\n\n"
                f"**Current Settings:**\n"
                f"• Max Trade Amount: {trading_settings.get('max_amount', 1.0)} SOL\n"
                f"• Stop Loss: {trading_settings.get('stop_loss', 10.0)}%\n"
                f"• Slippage: {trading_settings.get('slippage', 0.5)}%\n"
                f"• Auto Trading: {auto_trading_status}\n\n"
                f"**Available Options:**\n"
                f"• Adjust trade limits\n"
                f"• Set risk parameters\n"
                f"• Configure auto-trading\n\n"
                f"Choose an option below:",
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            
        except Exception as e:
            logger.error(f"Error in trading settings: {e}")
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="settings")]
            ])
            await query.edit_message_text(
                "❌ Error loading trading settings. Please try again.",
                reply_markup=keyboard
            )

    async def _handle_alert_settings(self, query, user_id):
        """Handle alert settings request"""
        try:
            # Get user's alert settings
            user_settings = await self.db.get_user_settings(user_id)
            alert_settings = user_settings.get('alerts', {})
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("💰 Large Transactions", callback_data="toggle_large_tx")],
                [InlineKeyboardButton("🐋 Whale Activity", callback_data="toggle_whale_alerts")],
                [InlineKeyboardButton("🪙 New Tokens", callback_data="toggle_new_tokens")],
                [InlineKeyboardButton("📈 Price Changes", callback_data="toggle_price_alerts")],
                [InlineKeyboardButton("⚙️ Thresholds", callback_data="alert_thresholds")],
                [InlineKeyboardButton("🔙 Back", callback_data="settings")]
            ])
            
            # Get alert status
            large_tx = "✅" if alert_settings.get('large_transactions', True) else "❌"
            whale = "✅" if alert_settings.get('whale_activity', True) else "❌"
            new_tokens = "✅" if alert_settings.get('new_tokens', True) else "❌"
            price = "✅" if alert_settings.get('price_changes', True) else "❌"
            
            await query.edit_message_text(
                f"🔔 *Alert Settings*\n\n"
                f"**Current Alerts:**\n"
                f"• Large transactions: {large_tx}\n"
                f"• Whale activity: {whale}\n"
                f"• New tokens: {new_tokens}\n"
                f"• Price changes: {price}\n\n"
                f"**Thresholds:**\n"
                f"• Large TX: {alert_settings.get('large_tx_threshold', 1.0)} SOL\n"
                f"• Whale: {alert_settings.get('whale_threshold', 1000)} SOL\n"
                f"• Price Change: {alert_settings.get('price_change_threshold', 5)}%\n\n"
                f"Choose an option below:",
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            
        except Exception as e:
            logger.error(f"Error in alert settings: {e}")
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="settings")]
            ])
            await query.edit_message_text(
                "❌ Error loading alert settings. Please try again.",
                reply_markup=keyboard
            )

    async def _handle_copy_settings(self, query, user_id):
        """Handle copy trading settings request"""
        try:
            # Get user's copy trading settings
            user_settings = await self.db.get_user_settings(user_id)
            copy_settings = user_settings.get('copy_trading', {})
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Add Trader", callback_data="add_copy_trader")],
                [InlineKeyboardButton("📊 Copy Percentage", callback_data="set_copy_percentage")],
                [InlineKeyboardButton("💰 Max Copy Amount", callback_data="set_max_copy_amount")],
                [InlineKeyboardButton("⏱️ Copy Delay", callback_data="set_copy_delay")],
                [InlineKeyboardButton("🔙 Back", callback_data="settings")]
            ])
            
            # Get current settings
            enabled = "🟢 Enabled" if copy_settings.get('enabled', False) else "🔴 Disabled"
            copy_percentage = copy_settings.get('copy_percentage', 100)
            max_amount = copy_settings.get('max_copy_amount', 1.0)
            copy_delay = copy_settings.get('copy_delay', 0)
            
            await query.edit_message_text(
                f"🔄 *Copy Trading Settings*\n\n"
                f"**Status:** {enabled}\n"
                f"**Copy Percentage:** {copy_percentage}%\n"
                f"**Max Copy Amount:** {max_amount} SOL\n"
                f"**Copy Delay:** {copy_delay} seconds\n\n"
                f"**Active Traders:** {len(copy_settings.get('active_wallets', []))}\n\n"
                f"**Available Options:**\n"
                f"• Select traders to follow\n"
                f"• Set copy percentages\n"
                f"• Configure risk limits\n\n"
                f"Choose an option below:",
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            
        except Exception as e:
            logger.error(f"Error in copy settings: {e}")
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="settings")]
            ])
            await query.edit_message_text(
                "❌ Error loading copy trading settings. Please try again.",
                reply_markup=keyboard
            )

    async def _handle_account_stats(self, query, user_id):
        """Handle account stats request"""
        try:
            user = await self.db.get_user(user_id)
            user_stats = user.get('stats', {}) if user else {}
            
            stats_text = (
                "📊 *Account Statistics*\n\n"
                f"**Trading Stats:**\n"
                f"• Total Trades: {user_stats.get('total_trades', 0)}\n"
                f"• Successful Trades: {user_stats.get('successful_trades', 0)}\n"
                f"• Total P&L: {user_stats.get('total_profit_loss', 0.0):.2f} SOL\n"
                f"• Wallets Monitored: {user_stats.get('wallets_monitored', 0)}\n\n"
                f"**Account Info:**\n"
                f"• Subscription: {user.get('subscription_tier', 'free').title()}\n"
                f"• Member Since: {user.get('created_at', 'Unknown')}\n"
                f"• Last Active: {user.get('last_active', 'Unknown')}\n"
            )
        except Exception as e:
            logger.error(f"Error getting account stats: {e}")
            stats_text = (
                "📊 *Account Statistics*\n\n"
                "❌ Error loading statistics.\n"
                "Please try again later."
            )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="settings")]
        ])
        
        await query.edit_message_text(
            stats_text,
            parse_mode='Markdown',
            reply_markup=keyboard
        )

    async def _show_wallet_analysis(self, query, user_id, wallet_address):
        """Show detailed wallet analysis"""
        try:
            # Get comprehensive wallet analysis
            wallet_data = await self.solana.get_wallet_balance(wallet_address)
            transactions = await self.solana.get_wallet_transactions(wallet_address, limit=50)
            
            # Perform analysis
            analysis = await self.analyzer._perform_wallet_analysis(wallet_address, wallet_data, transactions)
            
            analysis_text = f"🔍 *Wallet Analysis*\n\n"
            analysis_text += f"📍 Address: `{wallet_address}`\n\n"
            
            # Basic stats
            analysis_text += f"📊 *Basic Statistics*\n"
            analysis_text += f"• Total Value: ${analysis.get('total_value_usd', 0):,.2f}\n"
            analysis_text += f"• SOL Balance: {analysis.get('sol_balance', 0):.4f} SOL\n"
            analysis_text += f"• Token Diversity: {analysis.get('token_diversity', 0)} tokens\n"
            analysis_text += f"• Total Transactions: {analysis.get('transaction_count', 0)}\n\n"
            
            # Activity analysis
            if analysis.get('activity_score', 0) > 0:
                analysis_text += f"📈 *Activity Analysis*\n"
                analysis_text += f"• Activity Score: {analysis.get('activity_score', 0):.1f}/100\n"
                analysis_text += f"• Avg Time Between TX: {analysis.get('avg_time_between_tx', 0):.1f} hours\n"
                analysis_text += f"• Most Recent TX: {analysis.get('most_recent_tx', 0):.1f} hours ago\n\n"
            
            # Risk and profit scores
            analysis_text += f"🎯 *Performance Scores*\n"
            analysis_text += f"• Risk Score: {analysis.get('risk_score', 0):.1f}/100\n"
            analysis_text += f"• Profit Score: {analysis.get('profit_score', 0):.1f}/100\n\n"
            
            # Patterns and characteristics
            if analysis.get('patterns'):
                analysis_text += f"🔍 *Detected Patterns*\n"
                for pattern in analysis.get('patterns', [])[:3]:
                    analysis_text += f"• {pattern}\n"
                analysis_text += "\n"
            
            if analysis.get('characteristics'):
                analysis_text += f"🎭 *Wallet Characteristics*\n"
                for char in analysis.get('characteristics', [])[:3]:
                    analysis_text += f"• {char}\n"
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 View Transactions", callback_data=f"transactions_{wallet_address}")],
                [InlineKeyboardButton("🔔 Set Alerts", callback_data=f"alerts_{wallet_address}")],
                [InlineKeyboardButton("🔙 Back to Wallet", callback_data=f"wallet_details_{wallet_address}")]
            ])
            
            await query.edit_message_text(
                analysis_text,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            
        except Exception as e:
            logger.error(f"Error showing wallet analysis: {e}")
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data=f"wallet_details_{wallet_address}")]
            ])
            await query.edit_message_text(
                "❌ Error loading wallet analysis. Please try again.",
                reply_markup=keyboard
            )

    async def _show_wallet_transactions(self, query, user_id, wallet_address):
        """Show wallet transaction history"""
        try:
            transactions = await self.solana.get_wallet_transactions(wallet_address, limit=20)
            
            if not transactions:
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data=f"wallet_details_{wallet_address}")]
                ])
                await query.edit_message_text(
                    "📋 *Transaction History*\n\n"
                    "No transactions found for this wallet.",
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
                return
            
            tx_text = f"📋 *Transaction History*\n\n"
            tx_text += f"📍 Wallet: `{wallet_address[:8]}...{wallet_address[-8:]}`\n\n"
            
            for i, tx in enumerate(transactions[:15], 1):  # Show max 15 transactions
                tx_type = tx.get('type', 'unknown').title()
                amount = tx.get('amount', 0)
                timestamp = tx.get('block_time', 0)
                success = tx.get('success', True)
                
                if timestamp:
                    tx_time = datetime.fromtimestamp(timestamp).strftime('%m/%d %H:%M')
                else:
                    tx_time = "Unknown"
                
                status_emoji = "✅" if success else "❌"
                amount_str = f"{amount:.4f} SOL" if amount > 0 else "N/A"
                
                tx_text += f"{i}. {status_emoji} {tx_type}: {amount_str} ({tx_time})\n"
            
            if len(transactions) > 15:
                tx_text += f"\n... and {len(transactions) - 15} more transactions"
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📊 Full Analysis", callback_data=f"analyze_wallet_{wallet_address}")],
                [InlineKeyboardButton("🔙 Back to Wallet", callback_data=f"wallet_details_{wallet_address}")]
            ])
            
            await query.edit_message_text(
                tx_text,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            
        except Exception as e:
            logger.error(f"Error showing wallet transactions: {e}")
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data=f"wallet_details_{wallet_address}")]
            ])
            await query.edit_message_text(
                "❌ Error loading transactions. Please try again.",
                reply_markup=keyboard
            )

    async def _show_wallet_alerts(self, query, user_id, wallet_address):
        """Show wallet alert settings"""
        try:
            # Get current alert settings
            wallet_doc = await self.db.db.wallets.find_one({
                'address': wallet_address,
                'user_id': user_id
            })
            
            alert_settings = wallet_doc.get('alert_settings', {}) if wallet_doc else {
                'large_transactions': True,
                'new_tokens': True,
                'whale_activity': True,
                'balance_changes': True
            }
            
            alert_text = f"🔔 *Alert Settings*\n\n"
            alert_text += f"📍 Wallet: `{wallet_address[:8]}...{wallet_address[-8:]}`\n\n"
            
            alert_text += f"**Current Alerts:**\n"
            alert_text += f"• Large Transactions: {'✅' if alert_settings.get('large_transactions') else '❌'}\n"
            alert_text += f"• New Tokens: {'✅' if alert_settings.get('new_tokens') else '❌'}\n"
            alert_text += f"• Whale Activity: {'✅' if alert_settings.get('whale_activity') else '❌'}\n"
            alert_text += f"• Balance Changes: {'✅' if alert_settings.get('balance_changes') else '❌'}\n\n"
            
            alert_text += f"**Alert Thresholds:**\n"
            alert_text += f"• Large TX: {alert_settings.get('large_tx_threshold', 1.0)} SOL\n"
            alert_text += f"• Balance Change: {alert_settings.get('balance_change_threshold', 0.1)} SOL\n"
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("⚙️ Configure Alerts", callback_data=f"configure_alerts_{wallet_address}")],
                [InlineKeyboardButton("🔙 Back to Wallet", callback_data=f"wallet_details_{wallet_address}")]
            ])
            
            await query.edit_message_text(
                alert_text,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            
        except Exception as e:
            logger.error(f"Error showing wallet alerts: {e}")
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data=f"wallet_details_{wallet_address}")]
            ])
            await query.edit_message_text(
                "❌ Error loading alert settings. Please try again.",
                reply_markup=keyboard
            )

    async def _remove_wallet_monitor(self, query, user_id, wallet_address):
        """Remove wallet from monitoring"""
        try:
            # Update wallet status in database
            await self.db.update_wallet_data(wallet_address, {'is_active': False})
            
            # Remove from analyzer monitoring
            await self.analyzer.remove_wallet_monitor(wallet_address)
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Add Another Wallet", callback_data="add_wallet")],
                [InlineKeyboardButton("🔙 Back to Wallets", callback_data="monitor_wallets")]
            ])
            
            await query.edit_message_text(
                f"✅ *Wallet Removed*\n\n"
                f"Wallet `{wallet_address[:8]}...{wallet_address[-8:]}` has been removed from monitoring.\n\n"
                f"You will no longer receive alerts for this wallet.",
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            
        except Exception as e:
            logger.error(f"Error removing wallet monitor: {e}")
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data=f"wallet_details_{wallet_address}")]
            ])
            await query.edit_message_text(
                "❌ Error removing wallet from monitoring. Please try again.",
                reply_markup=keyboard
            )

    # Trading helper methods
    async def _analyze_token_address(self, update, user_id, token_address):
        """Analyze a token address"""
        try:
            # Get token information
            token_info = await self.solana.get_token_info(token_address)
            
            # Get token price and market data
            price_data = await self.solana.get_token_price(token_address)
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🟢 Quick Buy", callback_data=f"quick_buy_{token_address}")],
                [InlineKeyboardButton("🔴 Quick Sell", callback_data=f"quick_sell_{token_address}")],
                [InlineKeyboardButton("📋 Set Limit Order", callback_data=f"limit_order_{token_address}")],
                [InlineKeyboardButton("🔙 Back", callback_data="analysis_tools")]
            ])
            
            # Escape special characters in token data
            token_name = escape_markdown(token_info.get('name', 'Unknown'), version=2)
            token_symbol = escape_markdown(token_info.get('symbol', 'Unknown'), version=2)
            token_address_escaped = escape_markdown(token_address, version=2)
            
            analysis_text = f"📊 *Token Analysis*\n\n"
            analysis_text += f"🪙 Token: `{token_address_escaped}`\n"
            analysis_text += f"📝 Name: {token_name}\n"
            analysis_text += f"💎 Symbol: {token_symbol}\n"
            analysis_text += f"🔢 Decimals: {token_info.get('decimals', 9)}\n\n"
            
            if price_data:
                analysis_text += f"💰 *Market Data*\n"
                analysis_text += f"• Price: ${price_data.get('price', 0):.6f}\n"
                analysis_text += f"• 24h Change: {price_data.get('change_24h', 0):.2f}%\n"
                analysis_text += f"• Volume: ${price_data.get('volume_24h', 0):,.0f}\n"
                analysis_text += f"• Market Cap: ${price_data.get('market_cap', 0):,.0f}\n\n"
            
            analysis_text += f"Choose an action below:"
            
            await update.message.reply_text(
                analysis_text,
                parse_mode='MarkdownV2',
                reply_markup=keyboard
            )
            
        except Exception as e:
            logger.error(f"Error analyzing token: {e}")
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="analysis_tools")]
            ])
            await update.message.reply_text(
                "❌ Error analyzing token. Please try again.",
                reply_markup=keyboard
            )

    async def _process_quick_buy(self, update, user_id, token_address):
        """Process quick buy - ask for amount"""
        try:
            # Set user state to waiting for amount
            self.user_states[user_id] = {
                'state': 'waiting_trade_amount',
                'action': 'quick_buy',
                'token_address': token_address
            }
            
            # Get token info for display
            token_info = await self.solana.get_token_info(token_address)
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="trading_operations")]
            ])
            
            # Escape token symbol
            token_symbol = escape_markdown(token_info.get('symbol', 'Unknown'), version=2)
            token_address_short = escape_markdown(token_address[:8], version=2)
            
            await update.message.reply_text(
                f"🟢 *Quick Buy*\n\n"
                f"Token: {token_symbol} \\(`{token_address_short}\\.\\.\\.`\\)\n\n"
                f"Please enter the amount of SOL you want to spend:\n\n"
                f"Example: `0\\.1` for 0\\.1 SOL",
                parse_mode='MarkdownV2',
                reply_markup=keyboard
            )
            
        except Exception as e:
            logger.error(f"Error processing quick buy: {e}")
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="trading_operations")]
            ])
            await update.message.reply_text(
                "❌ Error processing quick buy. Please try again.",
                reply_markup=keyboard
            )

    async def _process_quick_sell(self, update, user_id, token_address):
        """Process quick sell - ask for amount"""
        try:
            # Set user state to waiting for amount
            self.user_states[user_id] = {
                'state': 'waiting_trade_amount',
                'action': 'quick_sell',
                'token_address': token_address
            }
            
            # Get token info for display
            token_info = await self.solana.get_token_info(token_address)
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="trading_operations")]
            ])
            
            # Escape token symbol
            token_symbol = escape_markdown(token_info.get('symbol', 'Unknown'), version=2)
            token_address_short = escape_markdown(token_address[:8], version=2)
            
            await update.message.reply_text(
                f"🔴 *Quick Sell*\n\n"
                f"Token: {token_symbol} \\(`{token_address_short}\\.\\.\\.`\\)\n\n"
                f"Please enter the amount of tokens you want to sell:\n\n"
                f"Example: `1000` for 1000 tokens",
                parse_mode='MarkdownV2',
                reply_markup=keyboard
            )
            
        except Exception as e:
            logger.error(f"Error processing quick sell: {e}")
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="trading_operations")]
            ])
            await update.message.reply_text(
                "❌ Error processing quick sell. Please try again.",
                reply_markup=keyboard
            )

    async def _process_limit_order(self, update, user_id, token_address):
        """Process limit order - ask for amount"""
        try:
            # Set user state to waiting for amount
            self.user_states[user_id] = {
                'state': 'waiting_trade_amount',
                'action': 'limit_order',
                'token_address': token_address
            }
            
            # Get token info for display
            token_info = await self.solana.get_token_info(token_address)
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="trading_operations")]
            ])
            
            # Escape token symbol
            token_symbol = escape_markdown(token_info.get('symbol', 'Unknown'), version=2)
            token_address_short = escape_markdown(token_address[:8], version=2)
            
            await update.message.reply_text(
                f"📋 *Limit Order*\n\n"
                f"Token: {token_symbol} \\(`{token_address_short}\\.\\.\\.`\\)\n\n"
                f"Please enter the amount for your limit order:\n\n"
                f"Example: `0\\.1` for 0\\.1 SOL",
                parse_mode='MarkdownV2',
                reply_markup=keyboard
            )
            
        except Exception as e:
            logger.error(f"Error processing limit order: {e}")
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="trading_operations")]
            ])
            await update.message.reply_text(
                "❌ Error processing limit order. Please try again.",
                reply_markup=keyboard
            )

    async def _execute_quick_buy(self, update, user_id, token_address, amount):
        """Execute quick buy trade"""
        try:
            # Get user settings
            user_settings = await self.db.get_user_settings(user_id)
            max_amount = user_settings.get('trading', {}).get('max_amount', 1.0)
            
            if amount > max_amount:
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data="trading_operations")]
                ])
                await update.message.reply_text(
                    f"❌ Amount exceeds maximum trade limit of {max_amount} SOL.\n\n"
                    f"Please enter a smaller amount.",
                    reply_markup=keyboard
                )
                return
            
            # Execute trade through trading engine
            trade_result = await self.trading_engine.execute_market_buy(
                user_id, token_address, amount
            )
            
            if trade_result.get('success'):
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("📊 View Trade", callback_data=f"trade_details_{trade_result['trade_id']}")],
                    [InlineKeyboardButton("🟢 Another Buy", callback_data="quick_buy")],
                    [InlineKeyboardButton("🔙 Back", callback_data="trading_operations")]
                ])
                
                # Escape special characters in trade result data
                token_symbol = escape_markdown(trade_result.get('token_symbol', 'Unknown'), version=2)
                signature = escape_markdown(trade_result.get('signature', 'Unknown'), version=2)
                
                await update.message.reply_text(
                    f"✅ *Quick Buy Executed*\n\n"
                    f"🪙 Token: {token_symbol}\n"
                    f"💰 Amount: {amount} SOL\n"
                    f"📊 Tokens Received: {trade_result.get('tokens_received', 0):,.0f}\n"
                    f"🔗 Transaction: `{signature}`\n\n"
                    f"Trade completed successfully\\!",
                    parse_mode='MarkdownV2',
                    reply_markup=keyboard
                )
            else:
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data="trading_operations")]
                ])
                await update.message.reply_text(
                    f"❌ *Trade Failed*\n\n"
                    f"Error: {trade_result.get('error', 'Unknown error')}\n\n"
                    f"Please try again or contact support.",
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
                
        except Exception as e:
            logger.error(f"Error executing quick buy: {e}")
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="trading_operations")]
            ])
            await update.message.reply_text(
                "❌ Error executing trade. Please try again.",
                reply_markup=keyboard
            )

    async def _execute_quick_sell(self, update, user_id, token_address, amount):
        """Execute quick sell trade"""
        try:
            # Execute trade through trading engine
            trade_result = await self.trading_engine.execute_market_sell(
                user_id, token_address, amount
            )
            
            if trade_result.get('success'):
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("📊 View Trade", callback_data=f"trade_details_{trade_result['trade_id']}")],
                    [InlineKeyboardButton("🔴 Another Sell", callback_data="quick_sell")],
                    [InlineKeyboardButton("🔙 Back", callback_data="trading_operations")]
                ])
                
                # Escape special characters in trade result data
                token_symbol = escape_markdown(trade_result.get('token_symbol', 'Unknown'), version=2)
                signature = escape_markdown(trade_result.get('signature', 'Unknown'), version=2)
                
                await update.message.reply_text(
                    f"✅ *Quick Sell Executed*\n\n"
                    f"🪙 Token: {token_symbol}\n"
                    f"💰 Amount: {amount} tokens\n"
                    f"📊 SOL Received: {trade_result.get('sol_received', 0):.4f} SOL\n"
                    f"🔗 Transaction: `{signature}`\n\n"
                    f"Trade completed successfully\\!",
                    parse_mode='MarkdownV2',
                    reply_markup=keyboard
                )
            else:
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data="trading_operations")]
                ])
                await update.message.reply_text(
                    f"❌ *Trade Failed*\n\n"
                    f"Error: {trade_result.get('error', 'Unknown error')}\n\n"
                    f"Please try again or contact support.",
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
                
        except Exception as e:
            logger.error(f"Error executing quick sell: {e}")
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="trading_operations")]
            ])
            await update.message.reply_text(
                "❌ Error executing trade. Please try again.",
                reply_markup=keyboard
            )

    async def _execute_limit_order(self, update, user_id, token_address, amount):
        """Execute limit order"""
        try:
            # For now, we'll create a limit order (not execute immediately)
            order_result = await self.trading_engine.create_limit_order(
                user_id, token_address, amount
            )
            
            if order_result.get('success'):
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("📋 View Orders", callback_data="view_orders")],
                    [InlineKeyboardButton("📋 Another Order", callback_data="limit_order")],
                    [InlineKeyboardButton("🔙 Back", callback_data="trading_operations")]
                ])
                
                # Escape special characters in order result data
                token_symbol = escape_markdown(order_result.get('token_symbol', 'Unknown'), version=2)
                order_id = escape_markdown(order_result.get('order_id', 'Unknown'), version=2)
                
                await update.message.reply_text(
                    f"✅ *Limit Order Created*\n\n"
                    f"🪙 Token: {token_symbol}\n"
                    f"💰 Amount: {amount} SOL\n"
                    f"📊 Order ID: `{order_id}`\n"
                    f"⏰ Status: Pending\n\n"
                    f"Order has been placed and will execute when conditions are met\\.",
                    parse_mode='MarkdownV2',
                    reply_markup=keyboard
                )
            else:
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data="trading_operations")]
                ])
                await update.message.reply_text(
                    f"❌ *Order Failed*\n\n"
                    f"Error: {order_result.get('error', 'Unknown error')}\n\n"
                    f"Please try again or contact support.",
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
                
        except Exception as e:
            logger.error(f"Error executing limit order: {e}")
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="trading_operations")]
            ])
            await update.message.reply_text(
                "❌ Error creating limit order. Please try again.",
                reply_markup=keyboard
            )

    async def _execute_trade(self, update, user_id, token_address, amount):
        """Execute generic trade"""
        try:
            # Default to market buy
            trade_result = await self.trading_engine.execute_market_buy(
                user_id, token_address, amount
            )
            
            if trade_result.get('success'):
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("📊 View Trade", callback_data=f"trade_details_{trade_result['trade_id']}")],
                    [InlineKeyboardButton("🔙 Back", callback_data="trading_operations")]
                ])
                
                await update.message.reply_text(
                    f"✅ *Trade Executed*\n\n"
                    f"🪙 Token: {trade_result.get('token_symbol', 'Unknown')}\n"
                    f"💰 Amount: {amount} SOL\n"
                    f"📊 Tokens Received: {trade_result.get('tokens_received', 0):,.0f}\n"
                    f"🔗 Transaction: `{trade_result.get('signature', 'Unknown')}`\n\n"
                    f"Trade completed successfully!",
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
            else:
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data="trading_operations")]
                ])
                await update.message.reply_text(
                    f"❌ *Trade Failed*\n\n"
                    f"Error: {trade_result.get('error', 'Unknown error')}\n\n"
                    f"Please try again or contact support.",
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
                
        except Exception as e:
            logger.error(f"Error executing trade: {e}")
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="trading_operations")]
            ])
            await update.message.reply_text(
                "❌ Error executing trade. Please try again.",
                reply_markup=keyboard
            )

    async def _handle_sniping_bot(self, query, user_id):
        """Show sniping bot interface"""
        try:
            # Get user's sniping settings
            user_settings = await self.db.get_user_settings(user_id)
            sniping_settings = user_settings.get('sniping', {})
            
            # Get active snipe orders
            active_snipes = await self.trading.get_user_snipe_orders(user_id)
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🎯 Create Snipe Order", callback_data="create_snipe")],
                [InlineKeyboardButton("📊 Active Snipes", callback_data="active_snipes")],
                [InlineKeyboardButton("⚙️ Snipe Settings", callback_data="snipe_settings")],
                [InlineKeyboardButton("📈 Snipe History", callback_data="snipe_history")],
                [InlineKeyboardButton("🔙 Back", callback_data="trading_operations")]
            ])
            
            # Format status
            status = "🟢 Active" if sniping_settings.get('enabled', False) else "🔴 Inactive"
            auto_snipe = "✅" if sniping_settings.get('auto_snipe', False) else "❌"
            
            sniping_text = (
                f"🎯 *Sniping Bot*\n\n"
                f"**Status:** {status}\n"
                f"**Auto Snipe:** {auto_snipe}\n"
                f"**Active Orders:** {len(active_snipes)}\n"
                f"**Max Snipe Amount:** {sniping_settings.get('max_snipe_amount', 0.1)} SOL\n"
                f"**Slippage:** {sniping_settings.get('snipe_slippage', 5)}%\n\n"
                f"**Features:**\n"
                f"• New token detection\n"
                f"• Instant buy execution\n"
                f"• Take profit/stop loss\n"
                f"• MEV protection\n\n"
                f"Choose an option below:"
            )
            
            await query.edit_message_text(
                sniping_text,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            
        except Exception as e:
            logger.error(f"Error in sniping bot menu: {e}")
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="trading_operations")]
            ])
            await query.edit_message_text(
                "❌ Error loading sniping bot. Please try again.",
                reply_markup=keyboard
            )

    async def _handle_trade_history(self, query, user_id):
        """Show trade history"""
        try:
            # Get user's trade history
            
            trade_history = await self.trading.get_user_trade_history(user_id, limit=20)
            
            if not trade_history:
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data="trading_operations")]
                ])
                await query.edit_message_text(
                    "📊 *Trade History*\n\n"
                    "No trades found yet\\.\n\n"
                    "Start trading to see your history here\\!",
                    parse_mode='MarkdownV2',
                    reply_markup=keyboard
                )
                return
            
            # Format trade history
            history_text = "📊 *Trade History*\n\n"
            
            for i, trade in enumerate(trade_history[:15], 1):  # Show max 15 trades
                # Escape special characters in trade data
                trade_type = escape_markdown(trade.get('type', 'Unknown'), version=2)
                token_symbol = escape_markdown(trade.get('token_symbol', 'Unknown'), version=2)
                amount = trade.get('amount', 0)
                price = trade.get('price', 0)
                timestamp = trade.get('created_at', 'Unknown')
                status = trade.get('status', 'Unknown')
                
                # Format timestamp
                if isinstance(timestamp, str):
                    try:
                        # Try to parse and format the timestamp
                        from datetime import datetime
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        formatted_time = dt.strftime('%m/%d %H:%M')
                        # Escape the formatted timestamp
                        formatted_time = escape_markdown(formatted_time, version=2)
                    except:
                        formatted_time = escape_markdown("Unknown", version=2)
                else:
                    formatted_time = escape_markdown("Unknown", version=2)
                
                # Status emoji
                status_emoji = "✅" if status == "completed" else "⏳" if status == "pending" else "❌"
                
                # Trade type emoji
                type_emoji = "🟢" if "buy" in trade_type.lower() else "🔴" if "sell" in trade_type.lower() else "📋"
                
                history_text += f"{i}\\. {status_emoji} {type_emoji} {trade_type}\n"
                history_text += f"   🪙 {token_symbol}\n"
                history_text += f"   💰 {amount:.4f} SOL\n"
                if price > 0:
                    history_text += f"   💵 ${price:.6f}\n"
                history_text += f"   ⏰ {formatted_time}\n\n"
            
            if len(trade_history) > 15:
                history_text += f"\n\\.\\.\\. and {len(trade_history) - 15} more trades"
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Refresh", callback_data="trade_history")],
                [InlineKeyboardButton("📊 Statistics", callback_data="trade_stats")],
                [InlineKeyboardButton("🔙 Back", callback_data="trading_operations")]
            ])
            
            await query.edit_message_text(
                history_text,
                parse_mode='MarkdownV2',
                reply_markup=keyboard
            )
            
        except Exception as e:
            logger.error(f"Error handling trade history: {e}")
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="trading_operations")]
            ])
            await query.edit_message_text(
                "❌ Error loading trade history\\. Please try again\\.",
                parse_mode='MarkdownV2',
                reply_markup=keyboard
            )

    async def _handle_copy_wallet_setup(self, query, user_id, wallet_address):
        """Handle copy wallet setup"""
        try:
            # Check if user already has copy trading subscription for this wallet
            existing_subscriptions = await self.trading.get_copy_trading_subscriptions(user_id)
            is_subscribed = any(sub['wallet_address'] == wallet_address for sub in existing_subscriptions)
            
            if is_subscribed:
                # Show current settings
                subscription = next(sub for sub in existing_subscriptions if sub['wallet_address'] == wallet_address)
                settings = subscription.get('copy_settings', {})
                
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("⚙️ Update Settings", callback_data=f"update_copy_{wallet_address}")],
                    [InlineKeyboardButton("❌ Unsubscribe", callback_data=f"unsubscribe_copy_{wallet_address}")],
                    [InlineKeyboardButton("🔙 Back", callback_data=f"wallet_{wallet_address}")]
                ])
                
                status = "🟢 Active" if settings.get('enabled', False) else "🔴 Inactive"
                copy_percentage = settings.get('copy_percentage', 100)
                max_amount = settings.get('max_copy_amount', 1.0)
                
                await query.edit_message_text(
                    f"🔄 *Copy Trading Setup*\n\n"
                    f"📍 Wallet: `{wallet_address[:8]}...`\n"
                    f"📊 Status: {status}\n"
                    f"📈 Copy Percentage: {copy_percentage}%\n"
                    f"💰 Max Amount: {max_amount} SOL\n\n"
                    f"Choose an action:",
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
            else:
                # Show setup options
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Subscribe", callback_data=f"subscribe_copy_{wallet_address}")],
                    [InlineKeyboardButton("🔙 Back", callback_data=f"wallet_{wallet_address}")]
                ])
                
                await query.edit_message_text(
                    f"🔄 *Copy Trading Setup*\n\n"
                    f"📍 Wallet: `{wallet_address[:8]}...`\n\n"
                    f"Copy trading allows you to automatically copy trades from this wallet.\n\n"
                    f"**Features:**\n"
                    f"• Automatic trade execution\n"
                    f"• Configurable copy percentage\n"
                    f"• Risk management limits\n"
                    f"• Real-time notifications\n\n"
                    f"Would you like to subscribe to copy trading for this wallet?",
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
                
        except Exception as e:
            logger.error(f"Error in copy wallet setup: {e}")
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="wallet_operations")]
            ])
            await query.edit_message_text(
                "❌ Error loading copy trading setup. Please try again.",
                reply_markup=keyboard
            )
            
    async def _show_whale_activity(self, query, user_id, wallet_address):
        """Show whale activity for a specific wallet"""
        try:
            # Get recent large transactions for this wallet
            transactions = await self.solana.get_wallet_transactions(wallet_address, limit=20)
            
            # Filter for significant transactions (> 10 SOL equivalent)
            whale_transactions = []
            for tx in transactions:
                if tx.get('amount_usd', 0) > 1000:  # $1000+ transactions
                    whale_transactions.append(tx)
            
            if whale_transactions:
                # Format recent whale activity
                activity_text = f"🐋 *Whale Activity*\n\n"
                activity_text += f"📍 Wallet: `{wallet_address[:8]}...`\n\n"
                
                for i, tx in enumerate(whale_transactions[:5], 1):
                    amount = tx.get('amount', 0)
                    token_symbol = tx.get('token_symbol', 'Unknown')
                    timestamp = datetime.fromtimestamp(tx.get('block_time', 0)).strftime('%m/%d %H:%M')
                    
                    activity_text += f"{i}. **{amount:.2f} {token_symbol}**\n"
                    activity_text += f"   📅 {timestamp} | 💰 ${tx.get('amount_usd', 0):,.0f}\n\n"
                
                if len(whale_transactions) > 5:
                    activity_text += f"... and {len(whale_transactions) - 5} more transactions\n\n"
                    
            else:
                activity_text = (
                    f"🐋 *Whale Activity*\n\n"
                    f"📍 Wallet: `{wallet_address[:8]}...`\n\n"
                    f"No significant whale activity detected in recent transactions.\n\n"
                    f"This wallet may not be a whale or hasn't made large trades recently."
                )
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📊 Full Analysis", callback_data=f"analyze_wallet_{wallet_address}")],
                [InlineKeyboardButton("📋 All Transactions", callback_data=f"transactions_{wallet_address}")],
                [InlineKeyboardButton("🔙 Back", callback_data=f"wallet_{wallet_address}")]
            ])
            
            await query.edit_message_text(
                activity_text,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            
        except Exception as e:
            logger.error(f"Error showing whale activity: {e}")
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="wallet_operations")]
            ])
            await query.edit_message_text(
                "❌ Error loading whale activity. Please try again.",
                reply_markup=keyboard
            )

    async def _handle_create_wallet_callback(self, query, user_id):
        """Handle create wallet callback - fully button-based with automatic fee deduction"""
        try:
            # Check if user already has a wallet
            existing_wallet = await self.db.get_user_primary_wallet(user_id)
            if existing_wallet:
                await query.edit_message_text(
                    "❌ *Wallet Already Exists*\n\n"
                    "You already have a wallet created. Use the 'My Wallets' button to manage your wallets.",
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("💼 My Wallets", callback_data="view_wallets")],
                        [InlineKeyboardButton("🔙 Back", callback_data="wallet_operations")]
                    ])
                )
                return
            
            # Check if user has sufficient balance for automatic fee deduction
            user_wallet = await self.db.get_user_primary_wallet(user_id)
            if user_wallet:
                balance = await self.solana.get_wallet_balance(user_wallet['address'])
                sol_balance = balance.get('sol_balance', 0)
                
                if sol_balance >= WALLET_CREATION_FEE:
                    # Automatically deduct fee and create wallet
                    fee_success = await self.payment.check_and_deduct_wallet_creation_fee(user_id)
                    
                    if fee_success:
                        # Create wallet after fee deduction
                        success, message, wallet_data = await self.payment.create_user_wallet(user_id)
                        
                        if success:
                            wallet_text = (
                                f"✅ *Wallet Created Successfully!*\n\n"
                                f"📍 **Address:** `{wallet_data['address']}`\n"
                                f"🔑 **Private Key:** `{wallet_data['private_key']}`\n\n"
                                f"⚠️ **IMPORTANT:** Save your private key securely!\n"
                                f"🔒 Keep it safe - you'll need it to access your wallet.\n\n"
                                f"💰 **Balance:** 0 SOL\n"
                                f"💳 **Fee Deducted:** {WALLET_CREATION_FEE} SOL\n\n"
                                f"Your wallet is ready for trading!"
                            )
                            
                            keyboard = InlineKeyboardMarkup([
                                [InlineKeyboardButton("💼 View Wallets", callback_data="view_wallets")],
                                [InlineKeyboardButton("⚡ Start Trading", callback_data="trading_operations")],
                                [InlineKeyboardButton("🔙 Back", callback_data="wallet_operations")]
                            ])
                            
                            await query.edit_message_text(
                                wallet_text,
                                parse_mode='Markdown',
                                reply_markup=keyboard
                            )
                        else:
                            await query.edit_message_text(
                                f"❌ *Wallet Creation Failed*\n\n{message}",
                                parse_mode='Markdown',
                                reply_markup=InlineKeyboardMarkup([
                                    [InlineKeyboardButton("🔄 Try Again", callback_data="create_wallet")],
                                    [InlineKeyboardButton("🔙 Back", callback_data="wallet_operations")]
                                ])
                            )
                    else:
                        await query.edit_message_text(
                            f"❌ *Insufficient Balance*\n\n"
                            f"You need at least {WALLET_CREATION_FEE} SOL in your wallet to create a new wallet.\n\n"
                            f"Current balance: {sol_balance:.4f} SOL",
                            parse_mode='Markdown',
                            reply_markup=InlineKeyboardMarkup([
                                [InlineKeyboardButton("💼 View Wallets", callback_data="view_wallets")],
                                [InlineKeyboardButton("🔙 Back", callback_data="wallet_operations")]
                            ])
                        )
                else:
                    await query.edit_message_text(
                        f"❌ *Insufficient Balance*\n\n"
                        f"You need at least {WALLET_CREATION_FEE} SOL in your wallet to create a new wallet.\n\n"
                        f"Current balance: {sol_balance:.4f} SOL",
                        parse_mode='Markdown',
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("💼 View Wallets", callback_data="view_wallets")],
                            [InlineKeyboardButton("🔙 Back", callback_data="wallet_operations")]
                        ])
                    )
            else:
                # No wallet exists, create one without fee (first wallet is free)
                success, message, wallet_data = await self.payment.create_user_wallet(user_id)
                
                if success:
                    wallet_text = (
                        f"✅ *Wallet Created Successfully!*\n\n"
                        f"📍 **Address:** `{wallet_data['address']}`\n"
                        f"🔑 **Private Key:** `{wallet_data['private_key']}`\n\n"
                        f"⚠️ **IMPORTANT:** Save your private key securely!\n"
                        f"🔒 Keep it safe - you'll need it to access your wallet.\n\n"
                        f"💰 **Balance:** 0 SOL\n"
                        f"🎁 **First wallet is free!**\n\n"
                        f"Your wallet is ready for trading!"
                    )
                    
                    keyboard = InlineKeyboardMarkup([
                        [InlineKeyboardButton("💼 View Wallets", callback_data="view_wallets")],
                        [InlineKeyboardButton("⚡ Start Trading", callback_data="trading_operations")],
                        [InlineKeyboardButton("🔙 Back", callback_data="wallet_operations")]
                    ])
                    
                    await query.edit_message_text(
                        wallet_text,
                        parse_mode='Markdown',
                        reply_markup=keyboard
                    )
                else:
                    await query.edit_message_text(
                        f"❌ *Wallet Creation Failed*\n\n{message}",
                        parse_mode='Markdown',
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🔄 Try Again", callback_data="create_wallet")],
                            [InlineKeyboardButton("🔙 Back", callback_data="wallet_operations")]
                        ])
                    )
                
        except Exception as e:
            logger.error(f"Error in create wallet callback: {e}")
            await query.edit_message_text(
                "❌ *Error*\n\nAn error occurred while creating your wallet. Please try again.",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Try Again", callback_data="create_wallet")],
                    [InlineKeyboardButton("🔙 Back", callback_data="wallet_operations")]
                ])
            )

    async def _handle_import_wallet_callback(self, query, user_id):
        """Handle import wallet callback - fully button-based"""
        try:
            # Set user state to wait for private key
            self.user_states[user_id] = {
                'state': 'waiting_for_private_key',
                'action': 'import_wallet'
            }
            
            import_text = (
                "🔑 *Import Existing Wallet*\n\n"
                "Please send your wallet's private key.\n\n"
                "⚠️ **Security Note:**\n"
                "• Your private key will be encrypted\n"
                "• Only you can access your wallet\n"
                "• We never store unencrypted keys\n\n"
                "Send your private key now:"
            )
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Cancel", callback_data="cancel_import")]
            ])
            
            await query.edit_message_text(
                import_text,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            
        except Exception as e:
            logger.error(f"Error in import wallet callback: {e}")
            await query.edit_message_text(
                "❌ *Error*\n\nAn error occurred. Please try again.",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Try Again", callback_data="import_wallet")],
                    [InlineKeyboardButton("🔙 Back", callback_data="wallet_operations")]
                ])
            )

    async def _handle_view_wallets_callback(self, query, user_id):
        """Handle view wallets callback - fully button-based"""
        try:
            # Get user wallets
            user_wallets = await self.db.get_user_wallets(user_id)
            
            if not user_wallets:
                no_wallets_text = (
                    "💼 *Your Wallets*\n\n"
                    "You don't have any wallets yet.\n\n"
                    "Create a new wallet or import an existing one:"
                )
                
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🆕 Create Wallet", callback_data="create_wallet")],
                    [InlineKeyboardButton("📥 Import Wallet", callback_data="import_wallet")],
                    [InlineKeyboardButton("🔙 Back", callback_data="wallet_operations")]
                ])
                
                await query.edit_message_text(
                    no_wallets_text,
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
                return
            
            # Show user wallets
            wallets_text = "💼 *Your Wallets*\n\n"
            
            for i, wallet in enumerate(user_wallets, 1):
                try:
                    balance = await self.solana.get_wallet_balance(wallet['address'])
                    sol_balance = balance.get('sol_balance', 0)
                except:
                    sol_balance = 0
                
                wallets_text += (
                    f"**{i}. {wallet['type'].title()} Wallet**\n"
                    f"📍 `{wallet['address']}`\n"
                    f"💰 {sol_balance:.4f} SOL\n"
                    f"📅 Created: {wallet.get('created_at', wallet.get('imported_at')).strftime('%Y-%m-%d')}\n\n"
                )
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🆕 Create New", callback_data="create_wallet")],
                [InlineKeyboardButton("📥 Import Another", callback_data="import_wallet")],
                [InlineKeyboardButton("⚡ Trade", callback_data="trading_operations")],
                [InlineKeyboardButton("🔙 Back", callback_data="wallet_operations")]
            ])
            
            await query.edit_message_text(
                wallets_text,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            
        except Exception as e:
            logger.error(f"Error in view wallets callback: {e}")
            await query.edit_message_text(
                "❌ *Error*\n\nAn error occurred while loading your wallets. Please try again.",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Try Again", callback_data="view_wallets")],
                    [InlineKeyboardButton("🔙 Back", callback_data="wallet_operations")]
                ])
            )



    async def _handle_cancel_import(self, query, user_id):
        """Handle cancel import callback"""
        try:
            # Clear user state
            self.user_states.pop(user_id, None)
            
            await query.edit_message_text(
                "❌ *Import Cancelled*\n\n"
                "Import process cancelled. You can try again anytime.",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📥 Import Wallet", callback_data="import_wallet")],
                    [InlineKeyboardButton("🔙 Back", callback_data="wallet_operations")]
                ])
            )
            
        except Exception as e:
            logger.error(f"Error in cancel import callback: {e}")

    async def _handle_upgrade_subscription(self, query, user_id, tier):
        """Handle upgrade subscription callback"""
        try:
            # Get user subscription
            user = await self.db.get_user(user_id)
            current_tier = user.get('subscription_tier', 'free')
            
            if current_tier == tier:
                await query.edit_message_text(
                    f"✅ *Already {tier.upper()}*\n\n"
                    f"You are already subscribed to the {tier} plan.",
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Back", callback_data="settings")]
                    ])
                )
                return
            
            # Show upgrade options
            tier_data = SUBSCRIPTION_TIERS[tier]
            upgrade_text = (
                f"💎 *Upgrade to {tier.upper()}*\n\n"
                f"💰 Monthly Fee: {tier_data['monthly_fee']} SOL\n"
                f"📊 Max Wallets: {tier_data['max_wallets']}\n"
                f"🔔 Max Alerts: {tier_data['max_alerts']}\n"
                f"✨ Features: {', '.join(tier_data['features'])}\n\n"
                f"Click 'Upgrade Now' to proceed with payment."
            )
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("💎 Upgrade Now", callback_data=f"confirm_upgrade_{tier}")],
                [InlineKeyboardButton("🔙 Back", callback_data="upgrade_plan")]
            ])
            
            await query.edit_message_text(
                upgrade_text,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            
        except Exception as e:
            logger.error(f"Error in upgrade subscription callback: {e}")
            await query.edit_message_text(
                "❌ *Error*\n\nAn error occurred. Please try again.",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data="upgrade_plan")]
                ])
            )

    async def handle_wallet_message(self, update: Update, user_id: int, message_text: str):
        """Handle wallet-related messages"""
        try:
            user_state = self.user_states.get(user_id, {})
            state = user_state.get('state')
            
            if state == 'waiting_for_private_key':
                # User is importing a wallet
                await self._process_import_wallet(update, user_id, message_text)
                
            elif state == 'waiting_wallet_amount':
                # User is creating a wallet
                await self._process_create_wallet(update, user_id, message_text)
                
            elif state == 'waiting_upgrade_amount':
                # User is upgrading subscription
                await self._process_upgrade_subscription(update, user_id, message_text)
                
            elif state == 'waiting_for_trading_wallet_key':
                # User is setting up a trading wallet
                await self._process_trading_wallet_setup(update, user_id, message_text)
                
            else:
                # Default wallet address processing
                await self._process_wallet_address(update, user_id, message_text)
                
        except Exception as e:
            logger.error(f"Error handling wallet message: {e}")
            await update.message.reply_text("❌ Error processing wallet message. Please try again.")
            
    async def _process_import_wallet(self, update: Update, user_id: int, private_key: str):
        """Process wallet import"""
        try:
            # Validate private key format
            if not self.security.validate_wallet_address(private_key):
                await update.message.reply_text(
                    "❌ Invalid private key format. Please check and try again."
                )
                return
            
            # Import wallet
            success, message = await self.payment.import_user_wallet(user_id, private_key)
            
            if success:
                # Clear user state
                self.user_states.pop(user_id, None)
                
                success_text = (
                    "✅ *Wallet Imported Successfully!*\n\n"
                    f"Your wallet has been imported and is ready for trading.\n\n"
                    f"Use /wallets to view your wallets or /trade to start trading."
                )
                
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("💼 View Wallets", callback_data="view_wallets")],
                    [InlineKeyboardButton("⚡ Start Trading", callback_data="trade_menu")],
                    [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
                ])
                
                await update.message.reply_text(
                    success_text,
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
            else:
                await update.message.reply_text(f"❌ {message}")
                
        except Exception as e:
            logger.error(f"Error importing wallet: {e}")
            await update.message.reply_text("❌ Error importing wallet. Please try again.")
            
    async def _process_create_wallet(self, update: Update, user_id: int, amount_text: str):
        """Process wallet creation"""
        try:
            # Parse amount
            try:
                amount = float(amount_text)
                if amount < WALLET_CREATION_FEE:
                    await update.message.reply_text(
                        f"❌ Amount must be at least {WALLET_CREATION_FEE} SOL for wallet creation fee."
                    )
                    return
            except ValueError:
                await update.message.reply_text("❌ Invalid amount. Please enter a valid number.")
                return
            
            # Create wallet
            success, message, wallet_data = await self.payment.create_user_wallet(user_id)
            
            if success:
                # Clear user state
                self.user_states.pop(user_id, None)
                
                wallet_text = (
                    f"✅ *Wallet Created Successfully!*\n\n"
                    f"📍 **Address:** `{wallet_data['address']}`\n"
                    f"🔑 **Private Key:** `{wallet_data['private_key']}`\n\n"
                    f"⚠️ **IMPORTANT:** Save your private key securely!\n"
                    f"🔒 Keep it safe - you'll need it to access your wallet.\n\n"
                    f"💰 **Balance:** 0 SOL\n\n"
                    f"Your wallet is ready for trading!"
                )
                
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("💼 View Wallets", callback_data="view_wallets")],
                    [InlineKeyboardButton("⚡ Start Trading", callback_data="trade_menu")],
                    [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
                ])
                
                await update.message.reply_text(
                    wallet_text,
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
            else:
                await update.message.reply_text(f"❌ {message}")
                
        except Exception as e:
            logger.error(f"Error creating wallet: {e}")
            await update.message.reply_text("❌ Error creating wallet. Please try again.")
            
    async def _process_upgrade_subscription(self, update: Update, user_id: int, amount_text: str):
        """Process subscription upgrade"""
        try:
            user_state = self.user_states.get(user_id, {})
            tier = user_state.get('tier', 'premium')
            
            # Parse amount
            try:
                amount = float(amount_text)
                required_amount = SUBSCRIPTION_TIERS[tier]['monthly_fee']
                if amount < required_amount:
                    await update.message.reply_text(
                        f"❌ Amount must be at least {required_amount} SOL for {tier} subscription."
                    )
                    return
            except ValueError:
                await update.message.reply_text("❌ Invalid amount. Please enter a valid number.")
                return
            
            # Process subscription payment
            success, message = await self.payment.process_subscription_payment(user_id, tier)
            
            if success:
                # Clear user state
                self.user_states.pop(user_id, None)
                
                success_text = (
                    f"✅ *Subscription Upgraded to {tier.upper()}!*\n\n"
                    f"Your subscription has been upgraded successfully.\n\n"
                    f"✨ **New Features:**\n"
                    f"• {SUBSCRIPTION_TIERS[tier]['max_wallets']} wallets\n"
                    f"• {SUBSCRIPTION_TIERS[tier]['max_alerts']} alerts\n"
                    f"• {', '.join(SUBSCRIPTION_TIERS[tier]['features'])}\n\n"
                    f"Enjoy your premium features!"
                )
                
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("💼 View Wallets", callback_data="view_wallets")],
                    [InlineKeyboardButton("⚡ Start Trading", callback_data="trade_menu")],
                    [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
                ])
                
                await update.message.reply_text(
                    success_text,
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
            else:
                await update.message.reply_text(f"❌ {message}")
                
        except Exception as e:
            logger.error(f"Error upgrading subscription: {e}")
            await update.message.reply_text("❌ Error upgrading subscription. Please try again.")

    async def _handle_connect_trading_wallet(self, query, user_id):
        """Handle connect trading wallet callback"""
        try:
            # Check if user already has a trading wallet
            existing_wallet = await self.payment.get_user_trading_wallet(user_id)
            
            if existing_wallet:
                # User already has a trading wallet - show options
                wallet_text = (
                    f"🔗 *Trading Wallet Connected*\n\n"
                    f"📍 **Address:** `{existing_wallet['address']}`\n"
                    f"📅 **Connected:** {existing_wallet['connected_at'].strftime('%Y-%m-%d %H:%M')}\n\n"
                    f"Choose an action:"
                )
                
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Replace Wallet", callback_data="replace_trading_wallet")],
                    [InlineKeyboardButton("❌ Disconnect Wallet", callback_data="disconnect_trading_wallet")],
                    [InlineKeyboardButton("🔙 Back", callback_data="settings")]
                ])
                
                await query.edit_message_text(
                    wallet_text,
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
            else:
                # No trading wallet connected - prompt for connection
                connect_text = (
                    "🔗 *Connect Trading Wallet*\n\n"
                    "To trade, you need to connect a wallet.\n\n"
                    "⚠️ **Important:**\n"
                    "• Only one trading wallet per user\n"
                    "• Your private key will be encrypted\n"
                    "• Only you can access your wallet\n\n"
                    "Send your wallet's private key:"
                )
                
                # Set user state to wait for private key
                self.user_states[user_id] = {
                    'state': 'waiting_for_trading_wallet_key',
                    'action': 'connect_trading_wallet'
                }
                
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("❌ Cancel", callback_data="settings")]
                ])
                
                await query.edit_message_text(
                    connect_text,
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
                
        except Exception as e:
            logger.error(f"Error in connect trading wallet callback: {e}")
            await query.edit_message_text(
                "❌ *Error*\n\nAn error occurred. Please try again.",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data="settings")]
                ])
            )

    async def _handle_replace_trading_wallet(self, query, user_id):
        """Handle replace trading wallet callback"""
        try:
            replace_text = (
                "🔄 *Replace Trading Wallet*\n\n"
                "This will replace your current trading wallet.\n\n"
                "⚠️ **Important:**\n"
                "• Your current wallet will be disconnected\n"
                "• Send the private key of your new wallet\n"
                "• Your private key will be encrypted\n\n"
                "Send your new wallet's private key:"
            )
            
            # Set user state to wait for private key
            self.user_states[user_id] = {
                'state': 'waiting_for_trading_wallet_key',
                'action': 'replace_trading_wallet'
            }
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Cancel", callback_data="connect_trading_wallet")]
            ])
            
            await query.edit_message_text(
                replace_text,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            
        except Exception as e:
            logger.error(f"Error in replace trading wallet callback: {e}")
            await query.edit_message_text(
                "❌ *Error*\n\nAn error occurred. Please try again.",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data="connect_trading_wallet")]
                ])
            )

    async def _handle_disconnect_trading_wallet(self, query, user_id):
        """Handle disconnect trading wallet callback"""
        try:
            # Get current trading wallet
            existing_wallet = await self.payment.get_user_trading_wallet(user_id)
            
            if not existing_wallet:
                await query.edit_message_text(
                    "❌ *No Trading Wallet*\n\n"
                    "You don't have a trading wallet connected.",
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔗 Connect Wallet", callback_data="connect_trading_wallet")],
                        [InlineKeyboardButton("🔙 Back", callback_data="settings")]
                    ])
                )
                return
            
            # Show confirmation
            confirm_text = (
                f"❌ *Disconnect Trading Wallet*\n\n"
                f"Are you sure you want to disconnect this wallet?\n\n"
                f"📍 **Address:** `{existing_wallet['address']}`\n"
                f"📅 **Connected:** {existing_wallet['connected_at'].strftime('%Y-%m-%d %H:%M')}\n\n"
                f"⚠️ **Warning:** You won't be able to trade until you connect a new wallet."
            )
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Confirm Disconnect", callback_data="confirm_disconnect_trading_wallet")],
                [InlineKeyboardButton("❌ Cancel", callback_data="connect_trading_wallet")]
            ])
            
            await query.edit_message_text(
                confirm_text,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            
        except Exception as e:
            logger.error(f"Error in disconnect trading wallet callback: {e}")
            await query.edit_message_text(
                "❌ *Error*\n\nAn error occurred. Please try again.",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data="connect_trading_wallet")]
                ])
            )

    async def _process_trading_wallet_setup(self, update: Update, user_id: int, private_key: str):
        """Process trading wallet setup"""
        try:
            user_state = self.user_states.get(user_id, {})
            action = user_state.get('action', 'connect_trading_wallet')
            
            if action == 'connect_trading_wallet':
                # Connect new trading wallet
                success, message, wallet_data = await self.payment.connect_trading_wallet(user_id, private_key)
            elif action == 'replace_trading_wallet':
                # Replace existing trading wallet
                success, message, wallet_data = await self.payment.replace_trading_wallet(user_id, private_key)
            else:
                await update.message.reply_text("❌ Invalid action. Please try again.")
                return
            
            if success:
                # Clear user state
                self.user_states.pop(user_id, None)
                
                success_text = (
                    f"✅ *Trading Wallet Connected!*\n\n"
                    f"📍 **Address:** `{wallet_data['address']}`\n"
                    f"🔑 **Private Key:** `{wallet_data['private_key']}`\n\n"
                    f"⚠️ **IMPORTANT:** Save your private key securely!\n"
                    f"🔒 Keep it safe - you'll need it to access your wallet.\n\n"
                    f"🎯 **You can now trade using this wallet!**\n\n"
                    f"Go to Trading menu to start trading."
                )
                
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("⚡ Start Trading", callback_data="trading_operations")],
                    [InlineKeyboardButton("🔗 Manage Wallet", callback_data="connect_trading_wallet")],
                    [InlineKeyboardButton("🔙 Back", callback_data="settings")]
                ])
                
                await update.message.reply_text(
                    success_text,
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
            else:
                await update.message.reply_text(f"❌ {message}")
                
        except Exception as e:
            logger.error(f"Error processing trading wallet setup: {e}")
            await update.message.reply_text("❌ Error processing trading wallet. Please try again.")

    async def _handle_confirm_disconnect_trading_wallet(self, query, user_id):
        """Handle confirm disconnect trading wallet callback"""
        try:
            # Disconnect the trading wallet
            success, message = await self.payment.disconnect_trading_wallet(user_id)
            
            if success:
                disconnect_text = (
                    "✅ *Trading Wallet Disconnected*\n\n"
                    "Your trading wallet has been disconnected successfully.\n\n"
                    "⚠️ **Note:** You won't be able to trade until you connect a new wallet.\n\n"
                    "To trade again, connect a new wallet in Settings."
                )
                
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔗 Connect New Wallet", callback_data="connect_trading_wallet")],
                    [InlineKeyboardButton("🔙 Back", callback_data="settings")]
                ])
                
                await query.edit_message_text(
                    disconnect_text,
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
            else:
                await query.edit_message_text(
                    f"❌ *Disconnect Failed*\n\n{message}",
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔄 Try Again", callback_data="disconnect_trading_wallet")],
                        [InlineKeyboardButton("🔙 Back", callback_data="connect_trading_wallet")]
                    ])
                )
                
        except Exception as e:
            logger.error(f"Error in confirm disconnect trading wallet callback: {e}")
            await query.edit_message_text(
                "❌ *Error*\n\nAn error occurred while disconnecting your wallet. Please try again.",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Try Again", callback_data="disconnect_trading_wallet")],
                    [InlineKeyboardButton("🔙 Back", callback_data="connect_trading_wallet")]
                ])
            )

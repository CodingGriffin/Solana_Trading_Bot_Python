"""
Telegram inline keyboard utilities
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def create_main_menu() -> InlineKeyboardMarkup:
    """Create main menu keyboard"""
    keyboard = [
        [InlineKeyboardButton("💼 Wallet Operations", callback_data="wallet_operations")],
        [InlineKeyboardButton("⚡ Trading", callback_data="trading_operations")],
        [InlineKeyboardButton("🔬 Analysis Tools", callback_data="analysis_tools")],
        [InlineKeyboardButton("🐋 Whale Alerts", callback_data="whale_alerts")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="settings")],
        [InlineKeyboardButton("❓ Help", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_wallet_menu() -> InlineKeyboardMarkup:
    """Create wallet analysis menu"""
    keyboard = [
        [InlineKeyboardButton("➕ Add Wallet for Analysis", callback_data="add_wallet")],
        [InlineKeyboardButton("📊 Monitor Wallets", callback_data="monitor_wallets")],
        [InlineKeyboardButton("🔍 Wallet Analysis", callback_data="analyze_wallet")],
        [InlineKeyboardButton("📈 Portfolio View", callback_data="portfolio_view")],
        [InlineKeyboardButton("💼 My Analysis Wallets", callback_data="view_wallets")],
        [InlineKeyboardButton("🔙 Back to Main", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_trade_menu() -> InlineKeyboardMarkup:
    """Create trading operations menu"""
    keyboard = [
        [
            InlineKeyboardButton("🟢 Quick Buy", callback_data="quick_buy"),
            InlineKeyboardButton("🔴 Quick Sell", callback_data="quick_sell")
        ],
        [InlineKeyboardButton("📋 Limit Orders", callback_data="limit_order")],
        [InlineKeyboardButton("🎯 Sniping Bot", callback_data="sniping_bot")],
        [InlineKeyboardButton("🔄 Copy Trading", callback_data="copy_trading")],
        [InlineKeyboardButton("📊 Trade History", callback_data="trade_history")],
        [InlineKeyboardButton("🔙 Back to Main", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_analysis_menu() -> InlineKeyboardMarkup:
    """Create analysis tools menu"""
    keyboard = [
        [InlineKeyboardButton("🔍 Analyze Wallet", callback_data="analyze_wallet")],
        [InlineKeyboardButton("📊 Token Analysis", callback_data="analyze_token")],
        [InlineKeyboardButton("🐋 Whale Tracker", callback_data="whale_tracker")],
        [InlineKeyboardButton("📈 Market Trends", callback_data="market_trends")],
        [InlineKeyboardButton("🎯 Top Performers", callback_data="top_performers")],
        [InlineKeyboardButton("🔙 Back to Main", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_settings_menu() -> InlineKeyboardMarkup:
    """Create settings menu"""
    keyboard = [
        [InlineKeyboardButton("🔗 Connect Trading Wallet", callback_data="connect_trading_wallet")],
        [InlineKeyboardButton("💎 Upgrade Plan", callback_data="upgrade_plan")],
        [InlineKeyboardButton("💼 My Wallets", callback_data="view_wallets")],
        [InlineKeyboardButton("⚙️ Trading Settings", callback_data="trading_settings")],
        [InlineKeyboardButton("🔔 Alert Settings", callback_data="alert_settings")],
        [InlineKeyboardButton("🔄 Copy Trading Settings", callback_data="copy_settings")],
        [InlineKeyboardButton("📊 Account Stats", callback_data="account_stats")],
        [InlineKeyboardButton("🔙 Back to Main", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_confirmation_keyboard(action: str, data: str = "") -> InlineKeyboardMarkup:
    """Create confirmation keyboard"""
    keyboard = [
        [
            InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_{action}_{data}"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_action")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_pagination_keyboard(current_page: int, total_pages: int, prefix: str) -> InlineKeyboardMarkup:
    """Create pagination keyboard"""
    keyboard = []
    
    # Navigation buttons
    nav_buttons = []
    if current_page > 1:
        nav_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"{prefix}_page_{current_page-1}"))
    if current_page < total_pages:
        nav_buttons.append(InlineKeyboardButton("➡️ Next", callback_data=f"{prefix}_page_{current_page+1}"))
        
    if nav_buttons:
        keyboard.append(nav_buttons)
        
    # Page info
    keyboard.append([InlineKeyboardButton(f"Page {current_page}/{total_pages}", callback_data="page_info")])
    
    # Back button
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="main_menu")])
    
    return InlineKeyboardMarkup(keyboard)

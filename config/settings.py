"""
Configuration settings for the Solana Trading Bot
"""

import os
from typing import List
from dotenv import load_dotenv

load_dotenv()

# Bot Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN", "your_telegram_bot_token")
BOT_USERNAME = os.getenv("BOT_USERNAME", "SolanaTraderBot")

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "mongodb://localhost:27017/solana_bot")

# Solana Configuration
SOLANA_RPC_URL = os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
SOLANA_WS_URL = os.getenv("SOLANA_WS_URL", "wss://api.mainnet-beta.solana.com")
PRIVATE_KEY = os.getenv("PRIVATE_KEY", "")  # Base58 encoded private key

# Trading Configuration
DEFAULT_SLIPPAGE = float(os.getenv("DEFAULT_SLIPPAGE", "0.5"))  # 0.5%
MAX_TRADE_AMOUNT = float(os.getenv("MAX_TRADE_AMOUNT", "10.0"))  # SOL
MIN_TRADE_AMOUNT = float(os.getenv("MIN_TRADE_AMOUNT", "0.01"))  # SOL

# Whale Detection Thresholds
WHALE_THRESHOLD_SOL = float(os.getenv("WHALE_THRESHOLD_SOL", "1000"))  # SOL
WHALE_THRESHOLD_USD = float(os.getenv("WHALE_THRESHOLD_USD", "100000"))  # USD

# Monitoring Configuration
MONITOR_INTERVAL = int(os.getenv("MONITOR_INTERVAL", "5"))  # seconds
MAX_CONCURRENT_MONITORS = int(os.getenv("MAX_CONCURRENT_MONITORS", "100"))

# Subscription Tiers - Monthly Plans
SUBSCRIPTION_TIERS = {
    "free": {
        "max_wallets": 1,
        "max_alerts": 5,
        "features": ["Basic trading", "Wallet monitoring", "Basic alerts"],
        "monthly_fee": 0.0
    },
    "premium": {
        "max_wallets": 3,
        "max_alerts": 20,
        "features": ["Advanced trading", "Copy trading", "Whale alerts", "Priority support"],
        "monthly_fee": 0.1  # 0.1 SOL per month
    },
    "pro": {
        "max_wallets": 10,
        "max_alerts": 100,
        "features": ["All Premium features", "API access", "Custom strategies", "VIP support", "Advanced analytics"],
        "monthly_fee": 0.5  # 0.5 SOL per month
    }
}

# Payment Configuration
ADMIN_WALLET_ADDRESS = os.getenv("ADMIN_WALLET_ADDRESS", "")
ADMIN_WALLET_PRIVATE_KEY = os.getenv("ADMIN_WALLET_PRIVATE_KEY", "")

# Fee Configuration
WALLET_CREATION_FEE = float(os.getenv("WALLET_CREATION_FEE", "0.01"))  # SOL
TRANSACTION_FEE_PERCENTAGE = float(os.getenv("TRANSACTION_FEE_PERCENTAGE", "0.1"))  # 0.1% on all trading transactions
SUBSCRIPTION_FEE_PERCENTAGE = float(os.getenv("SUBSCRIPTION_FEE_PERCENTAGE", "0.1"))  # 0.1% on subscription payments

# Wallet Management
WALLET_ENCRYPTION_KEY = os.getenv("WALLET_ENCRYPTION_KEY", "")
MAX_USER_WALLETS = int(os.getenv("MAX_USER_WALLETS", "5"))
ENABLE_WALLET_CREATION = os.getenv("ENABLE_WALLET_CREATION", "true").lower() == "true"
ENABLE_WALLET_IMPORT = os.getenv("ENABLE_WALLET_IMPORT", "true").lower() == "true"

# Trading Wallet Connection
ENABLE_TRADING_WALLET_CONNECTION = os.getenv("ENABLE_TRADING_WALLET_CONNECTION", "true").lower() == "true"
MAX_TRADING_WALLETS_PER_USER = int(os.getenv("MAX_TRADING_WALLETS_PER_USER", "1"))  # Only one trading wallet per user

# Payment Processing
PAYMENT_GATEWAY_ENABLED = os.getenv("PAYMENT_GATEWAY_ENABLED", "true").lower() == "true"
PAYMENT_CONFIRMATION_BLOCKS = int(os.getenv("PAYMENT_CONFIRMATION_BLOCKS", "3"))
MIN_PAYMENT_AMOUNT = float(os.getenv("MIN_PAYMENT_AMOUNT", "0.001"))  # SOL

# Subscription Management
SUBSCRIPTION_GRACE_PERIOD_DAYS = int(os.getenv("SUBSCRIPTION_GRACE_PERIOD_DAYS", "3"))
AUTO_SUBSCRIPTION_RENEWAL = os.getenv("AUTO_SUBSCRIPTION_RENEWAL", "true").lower() == "true"

# DEX Configuration
RAYDIUM_PROGRAM_ID = "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"
SERUM_PROGRAM_ID = "9xQeWvG816bUx9EPjHmaT23yvVM2ZWbrrpZb9PusVFin"

# Alert Configuration
TELEGRAM_ALERTS = True
DISCORD_ALERTS = os.getenv("DISCORD_ALERTS", "false").lower() == "true"
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")

# Performance Configuration
ASYNC_WORKERS = int(os.getenv("ASYNC_WORKERS", "10"))
CACHE_TTL = int(os.getenv("CACHE_TTL", "300"))  # 5 minutes

# Network Timeout Configuration
TELEGRAM_TIMEOUT = float(os.getenv("TELEGRAM_TIMEOUT", "60.0"))  # seconds
TELEGRAM_CONNECT_TIMEOUT = float(os.getenv("TELEGRAM_CONNECT_TIMEOUT", "20.0"))  # seconds
TELEGRAM_READ_TIMEOUT = float(os.getenv("TELEGRAM_READ_TIMEOUT", "60.0"))  # seconds
CALLBACK_TIMEOUT = float(os.getenv("CALLBACK_TIMEOUT", "10.0"))  # seconds

# Security Configuration
MAX_REQUESTS_PER_MINUTE = int(os.getenv("MAX_REQUESTS_PER_MINUTE", "60"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))  # seconds
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "")

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "solana_bot.log")

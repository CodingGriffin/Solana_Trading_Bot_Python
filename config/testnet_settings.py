"""
Testnet Configuration for Solana Trading Bot
Use this for safe testing before mainnet deployment
"""

import os

# Testnet Configuration
TESTNET_MODE = True

# Solana Testnet RPC Endpoints
SOLANA_RPC_URL = os.getenv("SOLANA_RPC_URL", "https://api.testnet.solana.com")
SOLANA_WS_URL = os.getenv("SOLANA_WS_URL", "wss://api.testnet.solana.com")

# Testnet Token Addresses (Example testnet tokens)
TESTNET_TOKENS = {
    "SOL": "So11111111111111111111111111111111111111112",  # Wrapped SOL
    "USDC": "4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU",  # Testnet USDC
    "USDT": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",  # Testnet USDT
}

# Testnet Jupiter API (if available, otherwise use mainnet for price data)
JUPITER_API_URL = os.getenv("JUPITER_API_URL", "https://quote-api.jup.ag/v6")

# Testnet Fee Configuration (Lower fees for testing)
TRANSACTION_FEE_PERCENTAGE = float(os.getenv("TRANSACTION_FEE_PERCENTAGE", "0.05"))  # 0.05% for testing
WALLET_CREATION_FEE = float(os.getenv("WALLET_CREATION_FEE", "0.001"))  # 0.001 SOL for testing

# Testnet Subscription Tiers (Lower fees for testing)
TESTNET_SUBSCRIPTION_TIERS = {
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
        "monthly_fee": 0.01  # 0.01 SOL per month for testing
    },
    "pro": {
        "max_wallets": 10,
        "max_alerts": 100,
        "features": ["All Premium features", "API access", "Custom strategies", "VIP support", "Advanced analytics"],
        "monthly_fee": 0.05  # 0.05 SOL per month for testing
    }
}

# Testnet Trading Limits (Lower limits for testing)
MAX_TRADE_AMOUNT = float(os.getenv("MAX_TRADE_AMOUNT", "1.0"))  # 1 SOL for testing
MIN_TRADE_AMOUNT = float(os.getenv("MIN_TRADE_AMOUNT", "0.001"))  # 0.001 SOL for testing

# Testnet Whale Thresholds (Lower thresholds for testing)
WHALE_THRESHOLD_SOL = float(os.getenv("WHALE_THRESHOLD_SOL", "10"))  # 10 SOL for testing
WHALE_THRESHOLD_USD = float(os.getenv("WHALE_THRESHOLD_USD", "1000"))  # $1000 for testing

# Testnet Payment Configuration
MIN_PAYMENT_AMOUNT = float(os.getenv("MIN_PAYMENT_AMOUNT", "0.0001"))  # 0.0001 SOL for testing

# Testnet Network Configuration
PAYMENT_CONFIRMATION_BLOCKS = int(os.getenv("PAYMENT_CONFIRMATION_BLOCKS", "1"))  # Faster confirmation for testing

# Testnet Alert Configuration
TESTNET_ALERTS = True
TESTNET_ALERT_PREFIX = "[TESTNET] "  # Prefix to identify testnet alerts

# Testnet Logging
TESTNET_LOG_FILE = os.getenv("TESTNET_LOG_FILE", "solana_bot_testnet.log")
TESTNET_LOG_LEVEL = os.getenv("TESTNET_LOG_LEVEL", "DEBUG")  # More detailed logging for testing

# Testnet Database (Separate database for testing)
TESTNET_DATABASE_URL = os.getenv("TESTNET_DATABASE_URL", "mongodb://localhost:27017/solana_bot_testnet")

# Testnet Admin Configuration
TESTNET_ADMIN_CHAT_ID = os.getenv("TESTNET_ADMIN_CHAT_ID", "")
TESTNET_ADMIN_WALLET_ADDRESS = os.getenv("TESTNET_ADMIN_WALLET_ADDRESS", "")

# Testnet Security (Relaxed for testing)
TESTNET_MAX_REQUESTS_PER_MINUTE = int(os.getenv("TESTNET_MAX_REQUESTS_PER_MINUTE", "120"))  # Higher limit for testing
TESTNET_RATE_LIMIT_WINDOW = int(os.getenv("TESTNET_RATE_LIMIT_WINDOW", "60"))  # seconds

# Testnet Monitoring
TESTNET_MONITOR_INTERVAL = int(os.getenv("TESTNET_MONITOR_INTERVAL", "10"))  # 10 seconds for testing
TESTNET_MAX_CONCURRENT_MONITORS = int(os.getenv("TESTNET_MAX_CONCURRENT_MONITORS", "50"))  # Lower for testing

# Testnet Performance
TESTNET_ASYNC_WORKERS = int(os.getenv("TESTNET_ASYNC_WORKERS", "5"))  # Lower for testing
TESTNET_CACHE_TTL = int(os.getenv("TESTNET_CACHE_TTL", "60"))  # 1 minute for testing

# Testnet Timeouts (Longer for testing)
TESTNET_TELEGRAM_TIMEOUT = float(os.getenv("TESTNET_TELEGRAM_TIMEOUT", "120.0"))  # 2 minutes for testing
TESTNET_TELEGRAM_CONNECT_TIMEOUT = float(os.getenv("TESTNET_TELEGRAM_CONNECT_TIMEOUT", "30.0"))  # 30 seconds for testing
TESTNET_TELEGRAM_READ_TIMEOUT = float(os.getenv("TESTNET_TELEGRAM_READ_TIMEOUT", "120.0"))  # 2 minutes for testing
TESTNET_CALLBACK_TIMEOUT = float(os.getenv("TESTNET_CALLBACK_TIMEOUT", "20.0"))  # 20 seconds for testing 
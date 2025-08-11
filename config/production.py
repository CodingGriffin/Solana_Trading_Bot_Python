"""
Production configuration settings
"""

import os
from typing import List
from config.settings import *

# Production-specific overrides
LOG_LEVEL = os.getenv("LOG_LEVEL", "WARNING")  # Less verbose in production
LOG_FILE = os.getenv("LOG_FILE", "/var/log/solana_bot.log")

# Enhanced security settings
MAX_REQUESTS_PER_MINUTE = int(os.getenv("MAX_REQUESTS_PER_MINUTE", "60"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))  # seconds

# Database security
DATABASE_URL = os.getenv("DATABASE_URL", "mongodb://localhost:27017/solana_bot")
DATABASE_USERNAME = os.getenv("DATABASE_USERNAME", "")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD", "")

# If database credentials are provided, update the connection string
if DATABASE_USERNAME and DATABASE_PASSWORD:
    # Parse the base URL and add authentication
    if DATABASE_URL.startswith("mongodb://"):
        base_url = DATABASE_URL.replace("mongodb://", "")
        DATABASE_URL = f"mongodb://{DATABASE_USERNAME}:{DATABASE_PASSWORD}@{base_url}"

# Enhanced monitoring
HEALTH_CHECK_INTERVAL = int(os.getenv("HEALTH_CHECK_INTERVAL", "30"))  # seconds
METRICS_ENABLED = os.getenv("METRICS_ENABLED", "true").lower() == "true"

# Circuit breaker settings
CIRCUIT_BREAKER_FAILURE_THRESHOLD = int(os.getenv("CIRCUIT_BREAKER_FAILURE_THRESHOLD", "5"))
CIRCUIT_BREAKER_RECOVERY_TIMEOUT = int(os.getenv("CIRCUIT_BREAKER_RECOVERY_TIMEOUT", "60"))  # seconds

# Backup settings
BACKUP_ENABLED = os.getenv("BACKUP_ENABLED", "true").lower() == "true"
BACKUP_INTERVAL_HOURS = int(os.getenv("BACKUP_INTERVAL_HOURS", "24"))

# Alerting
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "")
SYSTEM_ALERTS_ENABLED = os.getenv("SYSTEM_ALERTS_ENABLED", "true").lower() == "true"

# Performance tuning
ASYNC_WORKERS = int(os.getenv("ASYNC_WORKERS", "20"))  # More workers in production
CACHE_TTL = int(os.getenv("CACHE_TTL", "600"))  # 10 minutes cache

# Trading limits (stricter in production)
MAX_TRADE_AMOUNT = float(os.getenv("MAX_TRADE_AMOUNT", "5.0"))  # Reduced from 10.0
MIN_TRADE_AMOUNT = float(os.getenv("MIN_TRADE_AMOUNT", "0.1"))  # Increased from 0.01
DEFAULT_SLIPPAGE = float(os.getenv("DEFAULT_SLIPPAGE", "1.0"))  # Increased from 0.5

# Network resilience
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))  # seconds
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
RETRY_DELAY = int(os.getenv("RETRY_DELAY", "5"))  # seconds 
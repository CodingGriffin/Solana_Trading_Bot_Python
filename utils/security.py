"""
Security utilities for the Solana trading bot
"""

import re
import time
import hashlib
import hmac
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

class RateLimiter:
    """Rate limiting implementation"""
    
    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)
        
    def is_allowed(self, user_id: int) -> bool:
        """Check if user is within rate limits"""
        now = time.time()
        user_requests = self.requests[user_id]
        
        # Remove old requests outside the window
        user_requests[:] = [req_time for req_time in user_requests 
                           if now - req_time < self.window_seconds]
        
        # Check if user has exceeded limit
        if len(user_requests) >= self.max_requests:
            return False
            
        # Add current request
        user_requests.append(now)
        return True
        
    def get_remaining_requests(self, user_id: int) -> int:
        """Get remaining requests for user"""
        now = time.time()
        user_requests = self.requests[user_id]
        
        # Remove old requests
        user_requests[:] = [req_time for req_time in user_requests 
                           if now - req_time < self.window_seconds]
        
        return max(0, self.max_requests - len(user_requests))

class InputValidator:
    """Input validation utilities"""
    
    @staticmethod
    def validate_solana_address(address: str) -> bool:
        """Validate Solana wallet address format"""
        if not address or not isinstance(address, str):
            return False
            
        # Solana addresses are base58 encoded and 32-44 characters long
        if len(address) < 32 or len(address) > 44:
            return False
            
        # Check for valid base58 characters
        base58_chars = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
        return all(char in base58_chars for char in address)
    
    @staticmethod
    def validate_amount(amount: float, min_amount: float = 0.01, max_amount: float = 1000.0) -> bool:
        """Validate trade amount"""
        try:
            amount_float = float(amount)
            return min_amount <= amount_float <= max_amount
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def validate_slippage(slippage: float) -> bool:
        """Validate slippage percentage"""
        try:
            slippage_float = float(slippage)
            return 0.1 <= slippage_float <= 50.0  # 0.1% to 50%
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def sanitize_input(text: str) -> str:
        """Sanitize user input"""
        if not text:
            return ""
        
        # Remove potentially dangerous characters
        sanitized = re.sub(r'[<>"\']', '', text)
        return sanitized.strip()

class Authentication:
    """Authentication utilities"""
    
    def __init__(self, admin_chat_ids: List[int] = None):
        self.admin_chat_ids = set(admin_chat_ids or [])
        
    def is_admin(self, user_id: int) -> bool:
        """Check if user is admin"""
        return user_id in self.admin_chat_ids
        
    def require_admin(self, user_id: int) -> Tuple[bool, str]:
        """Require admin privileges"""
        if not self.is_admin(user_id):
            return False, "This command requires administrator privileges."
        return True, ""
    
    @staticmethod
    def generate_signature(data: str, secret: str) -> str:
        """Generate HMAC signature for data"""
        return hmac.new(
            secret.encode('utf-8'),
            data.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    @staticmethod
    def verify_signature(data: str, signature: str, secret: str) -> bool:
        """Verify HMAC signature"""
        expected_signature = Authentication.generate_signature(data, secret)
        return hmac.compare_digest(signature, expected_signature)

class SecurityManager:
    """Main security manager"""
    
    def __init__(self, max_requests: int = 60, window_seconds: int = 60, admin_chat_ids: List[int] = None):
        self.rate_limiter = RateLimiter(max_requests, window_seconds)
        self.validator = InputValidator()
        self.auth = Authentication(admin_chat_ids)
        
    def check_rate_limit(self, user_id: int) -> Tuple[bool, str]:
        """Check rate limit for user"""
        if not self.rate_limiter.is_allowed(user_id):
            remaining = self.rate_limiter.get_remaining_requests(user_id)
            return False, f"Rate limit exceeded. Try again later. Remaining requests: {remaining}"
        return True, ""
    
    def validate_wallet_address(self, address: str) -> Tuple[bool, str]:
        """Validate wallet address"""
        if not self.validator.validate_solana_address(address):
            return False, "Invalid Solana wallet address format."
        return True, ""
    
    def validate_trade_params(self, amount: float, slippage: float) -> Tuple[bool, str]:
        """Validate trading parameters"""
        if not self.validator.validate_amount(amount):
            return False, "Invalid trade amount."
        if not self.validator.validate_slippage(slippage):
            return False, "Invalid slippage percentage."
        return True, ""
    
    def sanitize_user_input(self, text: str) -> str:
        """Sanitize user input"""
        return self.validator.sanitize_input(text)
    
    def require_admin(self, user_id: int) -> Tuple[bool, str]:
        """Require admin privileges"""
        return self.auth.require_admin(user_id) 
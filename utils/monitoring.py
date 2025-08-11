"""
Monitoring and health check utilities
"""

import asyncio
import time
import psutil
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import defaultdict
from telegram import Bot
from config.settings import BOT_TOKEN

logger = logging.getLogger(__name__)

@dataclass
class HealthCheck:
    """Health check result"""
    service: str
    status: str  # "healthy", "degraded", "unhealthy"
    response_time: float
    error_message: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

class MetricsCollector:
    """Collect and store metrics"""
    
    def __init__(self):
        self.metrics = defaultdict(list)
        self.start_time = time.time()
        
    def record_metric(self, metric_name: str, value: float, labels: Dict[str, str] = None):
        """Record a metric"""
        metric_data = {
            'value': value,
            'timestamp': time.time(),
            'labels': labels or {}
        }
        self.metrics[metric_name].append(metric_data)
        
        # Keep only last 1000 data points per metric
        if len(self.metrics[metric_name]) > 1000:
            self.metrics[metric_name] = self.metrics[metric_name][-1000:]
    
    def get_metric_summary(self, metric_name: str, minutes: int = 60) -> Dict[str, Any]:
        """Get metric summary for the last N minutes"""
        if metric_name not in self.metrics:
            return {}
            
        cutoff_time = time.time() - (minutes * 60)
        recent_data = [
            data for data in self.metrics[metric_name]
            if data['timestamp'] >= cutoff_time
        ]
        
        if not recent_data:
            return {}
            
        values = [data['value'] for data in recent_data]
        return {
            'count': len(values),
            'min': min(values),
            'max': max(values),
            'avg': sum(values) / len(values),
            'latest': values[-1] if values else 0
        }
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system metrics"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available_gb': memory.available / (1024**3),
                'disk_percent': disk.percent,
                'disk_free_gb': disk.free / (1024**3),
                'uptime_seconds': time.time() - self.start_time
            }
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            return {}

class HealthChecker:
    """Health check manager"""
    
    def __init__(self, db_manager, solana_service):
        self.db_manager = db_manager
        self.solana_service = solana_service
        self.metrics = MetricsCollector()
        self.last_checks = {}
        
    async def check_database_health(self) -> HealthCheck:
        """Check database connectivity"""
        start_time = time.time()
        try:
            # Try a simple database operation
            await self.db_manager.db.command('ping')
            response_time = time.time() - start_time
            
            self.metrics.record_metric('database_response_time', response_time)
            return HealthCheck(
                service="database",
                status="healthy",
                response_time=response_time
            )
        except Exception as e:
            response_time = time.time() - start_time
            self.metrics.record_metric('database_errors', 1)
            return HealthCheck(
                service="database",
                status="unhealthy",
                response_time=response_time,
                error_message=str(e)
            )
    
    async def check_solana_health(self) -> HealthCheck:
        """Check Solana RPC connectivity"""
        start_time = time.time()
        try:
            # Try to get recent blockhash
            await self.solana_service.rpc_client.get_recent_blockhash()
            response_time = time.time() - start_time
            
            self.metrics.record_metric('solana_response_time', response_time)
            return HealthCheck(
                service="solana",
                status="healthy",
                response_time=response_time
            )
        except Exception as e:
            response_time = time.time() - start_time
            self.metrics.record_metric('solana_errors', 1)
            return HealthCheck(
                service="solana",
                status="unhealthy",
                response_time=response_time,
                error_message=str(e)
            )
    
    async def check_telegram_health(self) -> HealthCheck:
        """Check Telegram API connectivity"""
        start_time = time.time()
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get('https://api.telegram.org', timeout=10) as response:
                    response_time = time.time() - start_time
                    
                    if response.status == 200:
                        self.metrics.record_metric('telegram_response_time', response_time)
                        return HealthCheck(
                            service="telegram",
                            status="healthy",
                            response_time=response_time
                        )
                    else:
                        self.metrics.record_metric('telegram_errors', 1)
                        return HealthCheck(
                            service="telegram",
                            status="degraded",
                            response_time=response_time,
                            error_message=f"HTTP {response.status}"
                        )
        except Exception as e:
            response_time = time.time() - start_time
            self.metrics.record_metric('telegram_errors', 1)
            return HealthCheck(
                service="telegram",
                status="unhealthy",
                response_time=response_time,
                error_message=str(e)
            )
    
    async def run_health_checks(self) -> List[HealthCheck]:
        """Run all health checks"""
        checks = []
        
        # Database health check
        db_check = await self.check_database_health()
        checks.append(db_check)
        
        # Solana health check
        solana_check = await self.check_solana_health()
        checks.append(solana_check)
        
        # Telegram health check
        telegram_check = await self.check_telegram_health()
        checks.append(telegram_check)
        
        # Store results
        self.last_checks = {check.service: check for check in checks}
        
        return checks
    
    def get_overall_health(self) -> str:
        """Get overall system health status"""
        if not self.last_checks:
            return "unknown"
            
        statuses = [check.status for check in self.last_checks.values()]
        
        if "unhealthy" in statuses:
            return "unhealthy"
        elif "degraded" in statuses:
            return "degraded"
        else:
            return "healthy"
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get health check summary"""
        return {
            'overall_status': self.get_overall_health(),
            'services': {
                service: {
                    'status': check.status,
                    'response_time': check.response_time,
                    'last_check': check.timestamp.isoformat(),
                    'error': check.error_message
                }
                for service, check in self.last_checks.items()
            },
            'system_metrics': self.metrics.get_system_metrics(),
            'performance_metrics': {
                'database_response_time': self.metrics.get_metric_summary('database_response_time'),
                'solana_response_time': self.metrics.get_metric_summary('solana_response_time'),
                'telegram_response_time': self.metrics.get_metric_summary('telegram_response_time')
            }
        }

class AlertManager:
    """Alert management system"""
    
    def __init__(self, admin_chat_id: str = None, bot_token: str = None):
        self.admin_chat_id = admin_chat_id
        self.bot_token = bot_token or BOT_TOKEN
        self.bot = Bot(token=self.bot_token) if self.bot_token else None
        self.alert_history = []
        
    async def send_system_alert(self, message: str, severity: str = "info"):
        """Send system alert to admin"""
        if not self.admin_chat_id or not self.bot:
            logger.warning(f"System alert (no admin configured): {message}")
            return
            
        alert_data = {
            'message': message,
            'severity': severity,
            'timestamp': datetime.utcnow(),
            'sent': False
        }
        
        try:
            # Send real Telegram alert
            severity_emoji = {
                'info': 'ℹ️',
                'warning': '⚠️',
                'error': '❌',
                'success': '✅',
                'critical': '🚨'
            }.get(severity, 'ℹ️')
            
            formatted_message = f"{severity_emoji} **System Alert** ({severity.upper()})\n\n{message}\n\n⏰ {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
            
            await self.bot.send_message(
                chat_id=self.admin_chat_id,
                text=formatted_message,
                parse_mode='Markdown'
            )
            
            alert_data['sent'] = True
            logger.info(f"System alert sent ({severity}): {message}")
            
        except Exception as e:
            logger.error(f"Failed to send system alert: {e}")
            alert_data['sent'] = False
            
        self.alert_history.append(alert_data)
        
        # Keep only last 100 alerts
        if len(self.alert_history) > 100:
            self.alert_history = self.alert_history[-100:]
            
    async def send_user_alert(self, user_id: int, message: str, alert_type: str = "info"):
        """Send alert to specific user"""
        if not self.bot:
            logger.warning(f"User alert (no bot configured): {message}")
            return
            
        try:
            # Send real Telegram alert to user
            type_emoji = {
                'info': 'ℹ️',
                'trade': '💰',
                'whale': '🐋',
                'alert': '🔔',
                'success': '✅',
                'error': '❌'
            }.get(alert_type, 'ℹ️')
            
            formatted_message = f"{type_emoji} **{alert_type.title()} Alert**\n\n{message}\n\n⏰ {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
            
            await self.bot.send_message(
                chat_id=user_id,
                text=formatted_message,
                parse_mode='Markdown'
            )
            
            logger.info(f"User alert sent to {user_id} ({alert_type}): {message}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send user alert to {user_id}: {e}")
            return False
            
    async def send_whale_alert(self, user_ids: List[int], whale_data: Dict[str, Any]):
        """Send whale activity alert to multiple users"""
        if not self.bot:
            return
            
        message = (
            f"🐋 **Whale Activity Detected!**\n\n"
            f"💰 Amount: {whale_data.get('amount', 0):.2f} SOL\n"
            f"📍 Wallet: `{whale_data.get('wallet', 'Unknown')[:8]}...`\n"
            f"🎯 Action: {whale_data.get('action', 'Unknown')}\n"
            f"🪙 Token: {whale_data.get('token_symbol', 'Unknown')}\n"
            f"⏰ Time: {whale_data.get('timestamp', 'Unknown')}"
        )
        
        # Send to all users
        for user_id in user_ids:
            try:
                await self.bot.send_message(
                    chat_id=user_id,
                    text=message,
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Failed to send whale alert to {user_id}: {e}")
                
    async def send_trade_alert(self, user_id: int, trade_data: Dict[str, Any]):
        """Send trade execution alert to user"""
        if not self.bot:
            return
            
        trade_type = trade_data.get('trade_type', 'Unknown')
        amount = trade_data.get('amount', 0)
        token_symbol = trade_data.get('token_symbol', 'Unknown')
        signature = trade_data.get('signature', 'Unknown')
        
        message = (
            f"💰 **Trade Executed Successfully!**\n\n"
            f"📊 Type: {trade_type.title()}\n"
            f"🪙 Token: {token_symbol}\n"
            f"💰 Amount: {amount:.4f} SOL\n"
            f"🔗 Transaction: `{signature[:8]}...`\n"
            f"✅ Status: Completed"
        )
        
        try:
            await self.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to send trade alert to {user_id}: {e}")
            
    async def send_price_alert(self, user_id: int, token_symbol: str, price_change: float, current_price: float):
        """Send price change alert to user"""
        if not self.bot:
            return
            
        change_emoji = "📈" if price_change > 0 else "📉"
        message = (
            f"{change_emoji} **Price Alert**\n\n"
            f"🪙 Token: {token_symbol}\n"
            f"💰 Current Price: ${current_price:.6f}\n"
            f"📊 24h Change: {price_change:+.2f}%\n"
            f"⏰ Time: {datetime.utcnow().strftime('%H:%M:%S')} UTC"
        )
        
        try:
            await self.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to send price alert to {user_id}: {e}")
            
    def get_alert_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent alert history"""
        return self.alert_history[-limit:] if self.alert_history else []
        
    async def cleanup_old_alerts(self, days: int = 7):
        """Clean up old alerts from history"""
        cutoff_time = datetime.utcnow() - timedelta(days=days)
        self.alert_history = [
            alert for alert in self.alert_history 
            if alert['timestamp'] > cutoff_time
        ] 
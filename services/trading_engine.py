"""
Advanced trading engine with copy trading and automation
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
from services.solana_service import SolanaService
from services.database import DatabaseManager
from services.payment_service import PaymentService
from config.settings import DEFAULT_SLIPPAGE, MAX_TRADE_AMOUNT, MIN_TRADE_AMOUNT

logger = logging.getLogger(__name__)

class TradeType(Enum):
    BUY = "buy"
    SELL = "sell"
    LIMIT_BUY = "limit_buy"
    LIMIT_SELL = "limit_sell"
    COPY_TRADE = "copy_trade"
    SNIPE = "snipe"

class TradeStatus(Enum):
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class TradeOrder:
    user_id: int
    trade_type: TradeType
    input_token: str
    output_token: str
    amount: float
    price: Optional[float] = None
    slippage: float = DEFAULT_SLIPPAGE
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    expires_at: Optional[datetime] = None
    copy_wallet: Optional[str] = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()

class TradingEngine:
    def __init__(self, solana_service: SolanaService, db_manager: DatabaseManager, payment_service: PaymentService):
        self.solana = solana_service
        self.db = db_manager
        self.payment = payment_service
        self.active_orders: Dict[str, TradeOrder] = {}
        self.copy_trading_subscriptions: Dict[int, List[str]] = {}  # user_id -> wallet_addresses
        self.is_running = False
        self.price_monitors: Dict[str, float] = {}  # token -> target_price
        
    async def start_monitoring(self):
        """Start trading engine background tasks"""
        if self.is_running:
            return
            
        self.is_running = True
        logger.info("Starting trading engine")
        
        # Load existing orders and subscriptions
        await self._load_active_orders()
        await self._load_copy_trading_subscriptions()
        
        # Start background tasks
        asyncio.create_task(self._process_orders())
        asyncio.create_task(self._monitor_copy_trading())
        asyncio.create_task(self._monitor_limit_orders())
        asyncio.create_task(self._monitor_stop_losses())
        
    async def stop_monitoring(self):
        """Stop trading engine"""
        self.is_running = False
        logger.info("Stopping trading engine")
        
    async def _load_active_orders(self):
        """Load active orders from database"""
        try:
            cursor = self.db.db.trades.find({
                'status': {'$in': ['pending', 'executing']}
            })
            
            orders = await cursor.to_list(length=None)
            
            for order in orders:
                trade_order = TradeOrder(
                    user_id=order['user_id'],
                    trade_type=TradeType(order['trade_type']),
                    input_token=order['input_token'],
                    output_token=order['output_token'],
                    amount=order['amount'],
                    price=order.get('price'),
                    slippage=order.get('slippage', DEFAULT_SLIPPAGE),
                    stop_loss=order.get('stop_loss'),
                    take_profit=order.get('take_profit'),
                    expires_at=order.get('expires_at'),
                    copy_wallet=order.get('copy_wallet'),
                    created_at=order['created_at']
                )
                
                self.active_orders[str(order['_id'])] = trade_order
                
            logger.info(f"Loaded {len(self.active_orders)} active orders")
            
        except Exception as e:
            logger.error(f"Error loading active orders: {e}")
            
    async def _load_copy_trading_subscriptions(self):
        """Load copy trading subscriptions"""
        try:
            cursor = self.db.db.copy_subscriptions.find({'is_active': True})
            subscriptions = await cursor.to_list(length=None)
            
            for sub in subscriptions:
                user_id = sub['user_id']
                wallet_address = sub['wallet_address']
                
                if user_id not in self.copy_trading_subscriptions:
                    self.copy_trading_subscriptions[user_id] = []
                    
                self.copy_trading_subscriptions[user_id].append(wallet_address)
                
            logger.info(f"Loaded copy trading subscriptions for {len(self.copy_trading_subscriptions)} users")
            
        except Exception as e:
            logger.error(f"Error loading copy trading subscriptions: {e}")
            
    async def create_trade_order(self, order: TradeOrder) -> Tuple[bool, str]:
        """Create a new trade order"""
        try:
            # Validate order
            validation_result = await self._validate_order(order)
            if not validation_result[0]:
                return False, validation_result[1]
                
            # Store in database
            order_data = {
                'user_id': order.user_id,
                'trade_type': order.trade_type.value,
                'input_token': order.input_token,
                'output_token': order.output_token,
                'amount': order.amount,
                'price': order.price,
                'slippage': order.slippage,
                'stop_loss': order.stop_loss,
                'take_profit': order.take_profit,
                'expires_at': order.expires_at,
                'copy_wallet': order.copy_wallet,
                'status': TradeStatus.PENDING.value,
                'created_at': order.created_at
            }
            
            result = await self.db.store_trade(order_data)
            if not result:
                return False, "Failed to store trade order"
                
            # Add to active orders (get the inserted ID)
            cursor = self.db.db.trades.find({'user_id': order.user_id}).sort('created_at', -1).limit(1)
            trade_doc = await cursor.to_list(length=1)
            
            if trade_doc:
                order_id = str(trade_doc[0]['_id'])
                self.active_orders[order_id] = order
                
                # For market orders, execute immediately
                if order.trade_type in [TradeType.BUY, TradeType.SELL]:
                    asyncio.create_task(self._execute_market_order(order_id, order))
                    
                return True, f"Order created successfully. ID: {order_id}"
            else:
                return False, "Failed to retrieve order ID"
                
        except Exception as e:
            logger.error(f"Error creating trade order: {e}")
            return False, str(e)
            
    async def _validate_order(self, order: TradeOrder) -> Tuple[bool, str]:
        """Validate trade order"""
        try:
            # Check user exists and has permissions
            user = await self.db.get_user(order.user_id)
            if not user:
                return False, "User not found"
                
            # Check subscription limits
            user_tier = user.get('subscription_tier', 'free')
            if user_tier == 'free' and order.trade_type == TradeType.COPY_TRADE:
                return False, "Copy trading requires premium subscription"
                
            # Validate amount
            if order.amount < MIN_TRADE_AMOUNT:
                return False, f"Minimum trade amount is {MIN_TRADE_AMOUNT} SOL"
                
            if order.amount > MAX_TRADE_AMOUNT:
                return False, f"Maximum trade amount is {MAX_TRADE_AMOUNT} SOL"
                
            # Check user's max trade amount setting
            user_max = user.get('settings', {}).get('max_trade_amount', MAX_TRADE_AMOUNT)
            if order.amount > user_max:
                return False, f"Amount exceeds your maximum trade limit of {user_max} SOL"
                
            # Validate token addresses
            if not await self.solana.validate_address(order.input_token):
                return False, "Invalid input token address"
                
            if not await self.solana.validate_address(order.output_token):
                return False, "Invalid output token address"
                
            # Validate slippage
            if order.slippage < 0.1 or order.slippage > 50:
                return False, "Slippage must be between 0.1% and 50%"
                
            return True, "Order validated successfully"
            
        except Exception as e:
            logger.error(f"Error validating order: {e}")
            return False, str(e)
            
    async def _process_orders(self):
        """Main order processing loop"""
        while self.is_running:
            try:
                if not self.active_orders:
                    await asyncio.sleep(5)
                    continue
                    
                # Process orders in batches
                order_items = list(self.active_orders.items())
                
                for order_id, order in order_items:
                    try:
                        # Check if order expired
                        if order.expires_at and datetime.utcnow() > order.expires_at:
                            await self._cancel_order(order_id, "Order expired")
                            continue
                            
                        # Process based on order type
                        if order.trade_type in [TradeType.LIMIT_BUY, TradeType.LIMIT_SELL]:
                            await self._check_limit_order(order_id, order)
                        elif order.trade_type == TradeType.SNIPE:
                            await self._check_snipe_order(order_id, order)
                            
                    except Exception as e:
                        logger.error(f"Error processing order {order_id}: {e}")
                        
                await asyncio.sleep(2)  # Check every 2 seconds
                
            except Exception as e:
                logger.error(f"Error in order processing loop: {e}")
                await asyncio.sleep(5)
                
    async def _execute_market_order(self, order_id: str, order: TradeOrder):
        """Execute market order immediately"""
        try:
            # Update status to executing
            await self.db.update_trade_status(order_id, TradeStatus.EXECUTING.value)
            
            # Execute swap
            result = await self.solana.execute_swap(
                input_mint=order.input_token,
                output_mint=order.output_token,
                amount=order.amount,
                slippage=order.slippage
            )
            
            if result['success']:
                # Order completed successfully
                await self.db.update_trade_status(
                    order_id, 
                    TradeStatus.COMPLETED.value,
                    {
                        'signature': result['signature'],
                        'output_amount': result['output_amount'],
                        'price_impact': result['price_impact'],
                        'completed_at': datetime.utcnow()
                    }
                )
                
                # Remove from active orders
                if order_id in self.active_orders:
                    del self.active_orders[order_id]
                    
                # Send success notification
                await self.db.create_alert(order.user_id, {
                    'type': 'trade_completed',
                    'message': f"✅ Trade completed! Swapped {order.amount} tokens",
                    'data': result
                })
                
                logger.info(f"Market order {order_id} completed successfully")
                
            else:
                # Order failed
                await self.db.update_trade_status(
                    order_id,
                    TradeStatus.FAILED.value,
                    {
                        'error': result['error'],
                        'failed_at': datetime.utcnow()
                    }
                )
                
                # Remove from active orders
                if order_id in self.active_orders:
                    del self.active_orders[order_id]
                    
                # Send failure notification
                await self.db.create_alert(order.user_id, {
                    'type': 'trade_failed',
                    'message': f"❌ Trade failed: {result['error']}",
                    'data': result
                })
                
                logger.error(f"Market order {order_id} failed: {result['error']}")
                
        except Exception as e:
            logger.error(f"Error executing market order {order_id}: {e}")
            
            # Mark as failed
            await self.db.update_trade_status(
                order_id,
                TradeStatus.FAILED.value,
                {'error': str(e), 'failed_at': datetime.utcnow()}
            )
            
            if order_id in self.active_orders:
                del self.active_orders[order_id]
                
    async def _monitor_limit_orders(self):
        """Monitor limit orders for execution"""
        while self.is_running:
            try:
                # Get all active limit orders
                limit_orders = await self.db.get_all_pending_orders(status='pending')
                
                for order in limit_orders:
                    try:
                        # Check if order should be executed
                        await self._check_limit_order(str(order['_id']), order)
                    except Exception as e:
                        logger.error(f"Error checking limit order {order.get('_id')}: {e}")
                        
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Error in limit order monitoring: {e}")
                await asyncio.sleep(30)
                
    async def _check_limit_order(self, order_id: str, order: Dict[str, Any]):
        """Check if limit order should be executed"""
        try:
            # Get current token price
            price_data = await self.solana.get_token_price(order['output_token'])
            current_price = price_data.get('price', 0)
            
            if current_price == 0:
                return  # Can't get price, skip this check
                
            should_execute = False
            order_type = order.get('trade_type', 'limit_buy')
            limit_price = order.get('price', 0)
            
            if order_type == 'limit_buy' and limit_price > 0:
                # Execute if current price is at or below limit price
                should_execute = current_price <= limit_price
                
            elif order_type == 'limit_sell' and limit_price > 0:
                # Execute if current price is at or above limit price
                should_execute = current_price >= limit_price
                
            if should_execute:
                logger.info(f"Executing limit order {order_id} at price {current_price}")
                
                # Execute the order
                if order_type == 'limit_buy':
                    result = await self.execute_market_buy(
                        order['user_id'], 
                        order['output_token'], 
                        order['amount_sol']
                    )
                else:  # limit_sell
                    result = await self.execute_market_sell(
                        order['user_id'], 
                        order['input_token'], 
                        order['amount_tokens']
                    )
                
                if result.get('success'):
                    # Update order status to completed
                    await self.db.update_order_status(
                        order_id, 
                        'completed',
                        {
                            'executed_at': datetime.utcnow(),
                            'execution_price': current_price,
                            'signature': result.get('signature')
                        }
                    )
                    
                    # Send completion alert
                    await self._send_limit_order_alert(order['user_id'], {
                        'order_id': order_id,
                        'token_symbol': order.get('token_symbol', 'Unknown'),
                        'amount': order.get('amount_sol', order.get('amount_tokens', 0)),
                        'execution_price': current_price,
                        'signature': result.get('signature')
                    })
                    
                    logger.info(f"Limit order {order_id} executed successfully")
                else:
                    # Update order status to failed
                    await self.db.update_order_status(
                        order_id, 
                        'failed',
                        {
                            'error': result.get('error', 'Unknown error'),
                            'failed_at': datetime.utcnow()
                        }
                    )
                    
                    logger.error(f"Limit order {order_id} failed: {result.get('error')}")
                
        except Exception as e:
            logger.error(f"Error checking limit order {order_id}: {e}")
            
    async def _send_limit_order_alert(self, user_id: int, order_data: Dict[str, Any]):
        """Send limit order execution alert to user"""
        try:
            from utils.monitoring import AlertManager
            alert_manager = AlertManager()
            
            message = (
                f"📋 **Limit Order Executed!**\n\n"
                f"🪙 Token: {order_data['token_symbol']}\n"
                f"💰 Amount: {order_data['amount']:.4f}\n"
                f"💵 Execution Price: ${order_data['execution_price']:.6f}\n"
                f"🔗 Transaction: `{order_data['signature'][:8]}...`\n"
                f"✅ Status: Completed"
            )
            
            await alert_manager.send_user_alert(user_id, message, "limit_order")
            
        except Exception as e:
            logger.error(f"Error sending limit order alert: {e}")
            
    async def _check_snipe_order(self, order_id: str, order: TradeOrder):
        """Check if snipe order should be executed (new token detection)"""
        try:
            # This would involve monitoring for new token launches
            # For now, we'll implement a basic version that checks if token is tradeable
            
            # Try to get token info
            token_info = await self.solana.get_token_info(order.output_token)
            
            if token_info.get('symbol') != 'UNKNOWN':
                # Token is now available, execute snipe
                logger.info(f"Executing snipe order {order_id} for token {token_info.get('symbol')}")
                await self._execute_market_order(order_id, order)
                
        except Exception as e:
            logger.error(f"Error checking snipe order {order_id}: {e}")
            
    async def _monitor_copy_trading(self):
        """Monitor wallets for copy trading opportunities"""
        while self.is_running:
            try:
                if not self.copy_trading_subscriptions:
                    await asyncio.sleep(30)
                    continue
                    
                # Get all monitored wallets
                monitored_wallets = set()
                for wallets in self.copy_trading_subscriptions.values():
                    monitored_wallets.update(wallets)
                    
                # Check recent transactions for each wallet
                for wallet_address in monitored_wallets:
                    recent_txs = await self.solana.get_wallet_transactions(wallet_address, limit=5)
                    
                    for tx in recent_txs:
                        # Check if this is a recent transaction (last 5 minutes)
                        if tx.get('block_time'):
                            tx_time = datetime.fromtimestamp(tx['block_time'])
                            if datetime.utcnow() - tx_time > timedelta(minutes=5):
                                continue
                                
                        # Check if it's a significant transaction (buy or sell)
                        tx_type = tx.get('type', 'unknown')
                        amount = tx.get('amount', 0)
                        amount_usd = tx.get('amount_usd', 0)
                        
                        # Detect both buy and sell transactions
                        is_significant_trade = False
                        detected_trade_type = None
                        
                        if tx_type == 'receive' and amount > 0.1:  # Buy transaction
                            is_significant_trade = True
                            detected_trade_type = 'buy'
                        elif tx_type == 'send' and amount > 0.1:  # Sell transaction
                            is_significant_trade = True
                            detected_trade_type = 'sell'
                        elif amount_usd > 100:  # Any transaction > $100 USD
                            is_significant_trade = True
                            detected_trade_type = 'swap'
                        
                        if is_significant_trade:
                            # Add trade type to transaction data
                            tx['detected_trade_type'] = detected_trade_type
                            await self._execute_copy_trades(wallet_address, tx)
                            
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Error in copy trading monitoring: {e}")
                await asyncio.sleep(30)
                
    async def _execute_copy_trades(self, wallet_address: str, transaction: Dict):
        """Execute copy trades for a monitored wallet transaction"""
        try:
            # Get all users copying this wallet
            copy_users = await self.db.get_copy_trading_users(wallet_address)
            
            if not copy_users:
                return
                
            # Analyze the transaction to determine if it's worth copying
            tx_type = transaction.get('detected_trade_type', transaction.get('type', 'unknown'))
            amount = transaction.get('amount', 0)
            amount_usd = transaction.get('amount_usd', 0)
            
            # Only copy significant trades (configurable threshold)
            if amount < 0.1 and amount_usd < 100:  # Less than 0.1 SOL or $100
                return
                
            # Get transaction details
            input_token = transaction.get('input_token')
            output_token = transaction.get('output_token')
            
            if not input_token or not output_token:
                return
                
            # Execute copy trades for each user
            for user_data in copy_users:
                user_id = user_data['user_id']
                copy_settings = user_data.get('copy_settings', {})
                
                # Check if user has copy trading enabled
                if not copy_settings.get('enabled', False):
                    continue
                    
                # Check copy percentage and limits
                copy_percentage = copy_settings.get('copy_percentage', 100) / 100
                max_copy_amount = copy_settings.get('max_copy_amount', 1.0)
                
                # Calculate copy amount (use USD amount if available)
                if amount_usd > 0:
                    copy_amount_usd = min(amount_usd * copy_percentage, max_copy_amount * 100)  # Convert SOL to USD
                    copy_amount = copy_amount_usd / 100  # Approximate SOL equivalent
                else:
                    copy_amount = min(amount * copy_percentage, max_copy_amount)
                
                if copy_amount < 0.01:  # Minimum trade amount
                    continue
                    
                # Execute the copy trade
                try:
                    if tx_type == 'buy':
                        # Copy the buy
                        result = await self.execute_market_buy(
                            user_id, output_token, copy_amount
                        )
                    elif tx_type == 'sell':
                        # Copy the sell
                        result = await self.execute_market_sell(
                            user_id, input_token, copy_amount
                        )
                    elif tx_type == 'swap':
                        # For swaps, determine direction based on token flow
                        if input_token == 'So11111111111111111111111111111111111111112':  # SOL
                            result = await self.execute_market_buy(
                                user_id, output_token, copy_amount
                            )
                        else:
                            result = await self.execute_market_sell(
                                user_id, input_token, copy_amount
                            )
                    else:
                        continue
                        
                    if result.get('success'):
                        # Log successful copy trade
                        logger.info(f"Copy trade executed for user {user_id}: {tx_type} {copy_amount} SOL")
                        
                        # Send copy trade alert
                        await self._send_copy_trade_alert(user_id, {
                            'original_wallet': wallet_address,
                            'trade_type': tx_type,
                            'amount': copy_amount,
                            'signature': result.get('signature'),
                            'token_symbol': result.get('token_symbol', 'Unknown')
                        })
                        
                        # Update copy trading statistics
                        await self.db.update_copy_trading_stats(user_id, {
                            'total_copied_trades': 1,
                            'total_copied_volume': copy_amount,
                            'last_copied_at': datetime.utcnow()
                        })
                        
                except Exception as e:
                    logger.error(f"Error executing copy trade for user {user_id}: {e}")
                    
        except Exception as e:
            logger.error(f"Error in copy trading execution: {e}")
            
    async def _send_copy_trade_alert(self, user_id: int, trade_data: Dict[str, Any]):
        """Send copy trade alert to user"""
        try:
            from utils.monitoring import AlertManager
            alert_manager = AlertManager()
            
            message = (
                f"🔄 **Copy Trade Executed!**\n\n"
                f"📊 Type: {trade_data['trade_type'].title()}\n"
                f"🪙 Token: {trade_data['token_symbol']}\n"
                f"💰 Amount: {trade_data['amount']:.4f} SOL\n"
                f"📍 Copied from: `{trade_data['original_wallet'][:8]}...`\n"
                f"🔗 Transaction: `{trade_data['signature'][:8]}...`\n"
                f"✅ Status: Completed"
            )
            
            await alert_manager.send_user_alert(user_id, message, "copy_trade")
            
        except Exception as e:
            logger.error(f"Error sending copy trade alert: {e}")
            
    async def subscribe_copy_trading(self, user_id: int, wallet_address: str, settings: Dict[str, Any] = None) -> Tuple[bool, str]:
        """Subscribe to copy trading for a specific wallet"""
        try:
            # Validate wallet address
            if not await self.solana.validate_address(wallet_address):
                return False, "Invalid wallet address"
                
            # Default copy settings
            default_settings = {
                'enabled': True,
                'copy_percentage': 100,  # Copy 100% of trades
                'max_copy_amount': 1.0,  # Max 1 SOL per trade
                'min_trade_amount': 0.1,  # Only copy trades >= 0.1 SOL
                'copy_delay': 0,  # No delay
                'risk_level': 'medium'
            }
            
            # Merge with user settings
            copy_settings = {**default_settings, **(settings or {})}
            
            # Store copy trading subscription
            subscription_data = {
                'user_id': user_id,
                'wallet_address': wallet_address,
                'copy_settings': copy_settings,
                'created_at': datetime.utcnow(),
                'is_active': True
            }
            
            success = await self.db.store_copy_trading_subscription(subscription_data)
            
            if success:
                # Add wallet to monitoring if not already monitored
                await self.analyzer.add_wallet_monitor(wallet_address, user_id)
                
                logger.info(f"User {user_id} subscribed to copy trading for wallet {wallet_address}")
                return True, "Successfully subscribed to copy trading"
            else:
                return False, "Failed to store subscription"
                
        except Exception as e:
            logger.error(f"Error subscribing to copy trading: {e}")
            return False, f"Error: {str(e)}"
            
    async def unsubscribe_copy_trading(self, user_id: int, wallet_address: str) -> Tuple[bool, str]:
        """Unsubscribe from copy trading for a specific wallet"""
        try:
            success = await self.db.remove_copy_trading_subscription(user_id, wallet_address)
            
            if success:
                logger.info(f"User {user_id} unsubscribed from copy trading for wallet {wallet_address}")
                return True, "Successfully unsubscribed from copy trading"
            else:
                return False, "Failed to remove subscription"
                
        except Exception as e:
            logger.error(f"Error unsubscribing from copy trading: {e}")
            return False, f"Error: {str(e)}"
            
    async def get_copy_trading_subscriptions(self, user_id: int) -> List[Dict[str, Any]]:
        """Get user's copy trading subscriptions"""
        try:
            return await self.db.get_user_copy_trading_subscriptions(user_id)
        except Exception as e:
            logger.error(f"Error getting copy trading subscriptions: {e}")
            return []
            
    async def update_copy_trading_settings(self, user_id: int, wallet_address: str, settings: Dict[str, Any]) -> Tuple[bool, str]:
        """Update copy trading settings for a specific wallet"""
        try:
            success = await self.db.update_copy_trading_settings(user_id, wallet_address, settings)
            
            if success:
                return True, "Copy trading settings updated successfully"
            else:
                return False, "Failed to update settings"
                
        except Exception as e:
            logger.error(f"Error updating copy trading settings: {e}")
            return False, f"Error: {str(e)}"
            
    async def get_user_orders(self, user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """Get user's trading orders"""
        try:
            return await self.db.get_user_trades(user_id, limit)
        except Exception as e:
            logger.error(f"Error getting user orders: {e}")
            return []
            
    async def cancel_user_order(self, user_id: int, order_id: str) -> Tuple[bool, str]:
        """Cancel a user's order"""
        try:
            # Check if order exists and belongs to user
            order = await self.db.db.trades.find_one({
                '_id': order_id,
                'user_id': user_id
            })
            
            if not order:
                return False, "Order not found"
                
            # Cancel the order
            await self.db.update_trade_status(order_id, 'cancelled')
            
            # Remove from active orders if present
            if order_id in self.active_orders:
                del self.active_orders[order_id]
                
            return True, "Order cancelled successfully"
            
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            return False, f"Error cancelling order: {str(e)}"

    # New methods for enhanced functionality
    async def execute_market_buy(self, user_id: int, token_address: str, amount_sol: float) -> Dict[str, Any]:
        """Execute a market buy order"""
        try:
            # Validate amount
            if amount_sol < MIN_TRADE_AMOUNT or amount_sol > MAX_TRADE_AMOUNT:
                return {
                    'success': False,
                    'error': f"Amount must be between {MIN_TRADE_AMOUNT} and {MAX_TRADE_AMOUNT} SOL"
                }
            
            # Get user settings
            user_settings = await self.db.get_user_settings(user_id)
            max_amount = user_settings.get('trading', {}).get('max_amount', MAX_TRADE_AMOUNT)
            
            if amount_sol > max_amount:
                return {
                    'success': False,
                    'error': f"Amount exceeds your maximum trade limit of {max_amount} SOL"
                }
            
            # Get token info
            token_info = await self.solana.get_token_info(token_address)
            
            # Execute real swap via Jupiter
            swap_result = await self.solana.execute_swap(
                input_mint='So11111111111111111111111111111111111111112',  # SOL
                output_mint=token_address,
                amount=amount_sol,
                slippage=DEFAULT_SLIPPAGE
            )
            
            if swap_result.get('success'):
                # Store trade in database
                trade_data = {
                    'user_id': user_id,
                    'trade_type': 'market_buy',
                    'input_token': 'SOL',
                    'output_token': token_address,
                    'amount_sol': amount_sol,
                    'tokens_received': swap_result.get('output_amount', 0),
                    'signature': swap_result.get('signature'),
                    'status': 'completed',
                    'created_at': datetime.utcnow(),
                    'token_symbol': token_info.get('symbol', 'Unknown'),
                    'token_name': token_info.get('name', 'Unknown Token'),
                    'slippage': swap_result.get('slippage', DEFAULT_SLIPPAGE)
                }
                
                trade_id = await self.db.store_trade(trade_data)
                
                # Automatically deduct transaction fee
                fee_deduction_success = await self.payment.process_automatic_fee_deduction(
                    user_id, 
                    amount_sol, 
                    'trade', 
                    swap_result.get('signature', 'unknown')
                )
                
                if not fee_deduction_success:
                    logger.warning(f"Failed to deduct transaction fee for user {user_id}")
                
                return {
                    'success': True,
                    'trade_id': trade_id,
                    'signature': swap_result.get('signature'),
                    'token_symbol': token_info.get('symbol', 'Unknown'),
                    'tokens_received': swap_result.get('output_amount', 0),
                    'amount_sol': amount_sol,
                    'slippage': swap_result.get('slippage', DEFAULT_SLIPPAGE),
                    'fee_deducted': fee_deduction_success
                }
            else:
                return {
                    'success': False,
                    'error': swap_result.get('error', 'Unknown error')
                }
                
        except Exception as e:
            logger.error(f"Error executing market buy: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    async def execute_market_sell(self, user_id: int, token_address: str, amount_tokens: float) -> Dict[str, Any]:
        """Execute a market sell order"""
        try:
            # Get token info
            token_info = await self.solana.get_token_info(token_address)
            
            # Execute real swap via Jupiter
            swap_result = await self.solana.execute_swap(
                input_mint=token_address,
                output_mint='So11111111111111111111111111111111111111112',  # SOL
                amount=amount_tokens,
                slippage=DEFAULT_SLIPPAGE
            )
            
            if swap_result.get('success'):
                # Store trade in database
                trade_data = {
                    'user_id': user_id,
                    'trade_type': 'market_sell',
                    'input_token': token_address,
                    'output_token': 'SOL',
                    'amount_tokens': amount_tokens,
                    'sol_received': swap_result.get('output_amount', 0),
                    'signature': swap_result.get('signature'),
                    'status': 'completed',
                    'created_at': datetime.utcnow(),
                    'token_symbol': token_info.get('symbol', 'Unknown'),
                    'token_name': token_info.get('name', 'Unknown Token'),
                    'slippage': swap_result.get('slippage', DEFAULT_SLIPPAGE)
                }
                
                trade_id = await self.db.store_trade(trade_data)
                
                # Automatically deduct transaction fee
                fee_deduction_success = await self.payment.process_automatic_fee_deduction(
                    user_id, 
                    swap_result.get('output_amount', 0), 
                    'trade', 
                    swap_result.get('signature', 'unknown')
                )
                
                if not fee_deduction_success:
                    logger.warning(f"Failed to deduct transaction fee for user {user_id}")
                
                return {
                    'success': True,
                    'trade_id': trade_id,
                    'signature': swap_result.get('signature'),
                    'token_symbol': token_info.get('symbol', 'Unknown'),
                    'sol_received': swap_result.get('output_amount', 0),
                    'amount_tokens': amount_tokens,
                    'slippage': swap_result.get('slippage', DEFAULT_SLIPPAGE),
                    'fee_deducted': fee_deduction_success
                }
            else:
                return {
                    'success': False,
                    'error': swap_result.get('error', 'Unknown error')
                }
                
        except Exception as e:
            logger.error(f"Error executing market sell: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    async def create_limit_order(self, user_id: int, token_address: str, amount_sol: float) -> Dict[str, Any]:
        """Create a limit order"""
        try:
            # Validate amount
            if amount_sol < MIN_TRADE_AMOUNT or amount_sol > MAX_TRADE_AMOUNT:
                return {
                    'success': False,
                    'error': f"Amount must be between {MIN_TRADE_AMOUNT} and {MAX_TRADE_AMOUNT} SOL"
                }
            
            # Get token info
            token_info = await self.solana.get_token_info(token_address)
            
            # Create order data
            order_data = {
                'user_id': user_id,
                'trade_type': 'limit_buy',
                'input_token': 'SOL',
                'output_token': token_address,
                'amount_sol': amount_sol,
                'status': 'pending',
                'created_at': datetime.utcnow(),
                'token_symbol': token_info.get('symbol', 'Unknown'),
                'token_name': token_info.get('name', 'Unknown Token')
            }
            
            # Store in database
            order_id = await self.db.create_limit_order(order_data)
            
            if order_id:
                return {
                    'success': True,
                    'order_id': order_id,
                    'token_symbol': token_info.get('symbol', 'Unknown'),
                    'amount_sol': amount_sol
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to create order'
                }
                
        except Exception as e:
            logger.error(f"Error creating limit order: {e}")
            return {
                'success': False,
                'error': f"Error creating order: {str(e)}"
            }

    async def get_user_trade_history(self, user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """Get user's trade history"""
        try:
            trades = await self.db.get_user_trades(user_id, limit)
            return trades
        except Exception as e:
            logger.error(f"Error getting trade history: {e}")
            return []

    async def get_user_portfolio(self, user_id: int) -> Dict[str, Any]:
        """Get user's current portfolio"""
        try:
            # Get user's wallets
            wallets = await self.db.get_user_wallets(user_id)
            
            portfolio = {
                'total_value_usd': 0,
                'sol_balance': 0,
                'tokens': [],
                'recent_trades': []
            }
            
            # Calculate total portfolio value
            for wallet in wallets:
                if wallet.get('is_active', False):
                    wallet_data = await self.solana.get_wallet_balance(wallet['address'])
                    
                    # Add SOL balance
                    sol_balance = wallet_data.get('sol_balance', 0)
                    sol_price = await self.solana.get_sol_price()
                    portfolio['sol_balance'] += sol_balance
                    portfolio['total_value_usd'] += sol_balance * sol_price
                    
                    # Add token balances
                    for token in wallet_data.get('tokens', []):
                        if token.get('balance', 0) > 0:
                            token_price = await self.solana.get_token_price(token['mint'])
                            token_value = token['balance'] * token_price
                            portfolio['total_value_usd'] += token_value
                            
                            portfolio['tokens'].append({
                                'mint': token['mint'],
                                'balance': token['balance'],
                                'value_usd': token_value,
                                'price_usd': token_price
                            })
            
            # Get recent trades
            portfolio['recent_trades'] = await self.get_user_trade_history(user_id, 5)
            
            return portfolio
            
        except Exception as e:
            logger.error(f"Error getting user portfolio: {e}")
            return {
                'total_value_usd': 0,
                'sol_balance': 0,
                'tokens': [],
                'recent_trades': []
            }

    async def get_trading_statistics(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """Get user's trading statistics"""
        try:
            # Get user analytics
            analytics = await self.db.get_user_analytics(user_id, days)
            
            # Get portfolio
            portfolio = await self.get_user_portfolio(user_id)
            
            # Calculate additional metrics
            total_trades = analytics.get('total_trades', 0)
            successful_trades = int(total_trades * analytics.get('success_rate', 0) / 100)
            failed_trades = total_trades - successful_trades
            
            return {
                'period_days': days,
                'total_trades': total_trades,
                'successful_trades': successful_trades,
                'failed_trades': failed_trades,
                'success_rate': analytics.get('success_rate', 0),
                'total_volume': analytics.get('total_volume', 0),
                'total_profit': analytics.get('total_profit', 0),
                'avg_trade_size': analytics.get('avg_trade_size', 0),
                'portfolio_value': portfolio.get('total_value_usd', 0),
                'monitored_wallets': analytics.get('monitored_wallets', 0),
                'alerts_received': analytics.get('alerts_received', 0)
            }
            
        except Exception as e:
            logger.error(f"Error getting trading statistics: {e}")
            return {
                'period_days': days,
                'total_trades': 0,
                'successful_trades': 0,
                'failed_trades': 0,
                'success_rate': 0,
                'total_volume': 0,
                'total_profit': 0,
                'avg_trade_size': 0,
                'portfolio_value': 0,
                'monitored_wallets': 0,
                'alerts_received': 0
            }

    async def get_market_analysis(self) -> Dict[str, Any]:
        """Get market analysis and trends"""
        try:
            # Get market trends
            trends = await self.db.get_market_trends(24)  # Last 24 hours
            
            # Get network stats
            network_stats = await self.solana.get_network_stats()
            
            # Get top performing tokens
            trending_tokens = trends.get('trending_tokens', [])
            
            return {
                'trending_tokens': trending_tokens[:5],  # Top 5
                'total_volume_24h': trends.get('total_volume', 0),
                'total_transactions_24h': trends.get('total_transactions', 0),
                'network_tps': network_stats.get('tps', 0),
                'current_slot': network_stats.get('current_slot', 0),
                'market_sentiment': 'bullish' if trends.get('total_volume', 0) > 1000000 else 'neutral'
            }
            
        except Exception as e:
            logger.error(f"Error getting market analysis: {e}")
            return {
                'trending_tokens': [],
                'total_volume_24h': 0,
                'total_transactions_24h': 0,
                'network_tps': 0,
                'current_slot': 0,
                'market_sentiment': 'neutral'
            }

    async def create_snipe_order(self, user_id: int, snipe_config: Dict[str, Any]) -> Tuple[bool, str]:
        """Create a snipe order for new token detection"""
        try:
            # Validate snipe configuration
            required_fields = ['max_amount', 'slippage', 'take_profit', 'stop_loss']
            for field in required_fields:
                if field not in snipe_config:
                    return False, f"Missing required field: {field}"
            
            # Validate amounts
            max_amount = snipe_config['max_amount']
            if max_amount < 0.01 or max_amount > 10.0:
                return False, "Max amount must be between 0.01 and 10.0 SOL"
            
            # Create snipe order
            snipe_order = {
                'user_id': user_id,
                'max_amount': max_amount,
                'slippage': snipe_config['slippage'],
                'take_profit': snipe_config['take_profit'],
                'stop_loss': snipe_config['stop_loss'],
                'filters': snipe_config.get('filters', {}),
                'status': 'active',
                'created_at': datetime.utcnow(),
                'executed_trades': [],
                'total_spent': 0.0,
                'total_profit': 0.0
            }
            
            # Store in database
            order_id = await self.db.store_snipe_order(snipe_order)
            
            if order_id:
                logger.info(f"Created snipe order {order_id} for user {user_id}")
                return True, f"Snipe order created successfully (ID: {order_id})"
            else:
                return False, "Failed to create snipe order"
                
        except Exception as e:
            logger.error(f"Error creating snipe order: {e}")
            return False, f"Error: {str(e)}"
    
    async def execute_snipe_trade(self, snipe_order: Dict[str, Any], token_address: str, token_info: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a snipe trade for a detected token"""
        try:
            user_id = snipe_order['user_id']
            max_amount = snipe_order['max_amount']
            slippage = snipe_order['slippage']
            
            # Check if we've already spent the max amount
            if snipe_order['total_spent'] >= max_amount:
                return {'success': False, 'error': 'Max amount already spent'}
            
            # Calculate trade amount (remaining amount or a percentage)
            remaining_amount = max_amount - snipe_order['total_spent']
            trade_amount = min(remaining_amount, max_amount * 0.2)  # Max 20% per trade
            
            if trade_amount < 0.01:
                return {'success': False, 'error': 'Insufficient remaining amount'}
            
            # Execute the snipe trade
            result = await self.execute_market_buy(
                user_id, token_address, trade_amount
            )
            
            if result.get('success'):
                # Update snipe order
                executed_trade = {
                    'token_address': token_address,
                    'token_symbol': token_info.get('symbol', 'Unknown'),
                    'amount': trade_amount,
                    'signature': result.get('signature'),
                    'executed_at': datetime.utcnow(),
                    'price_at_execution': await self._get_token_price_at_time(token_address)
                }
                
                # Add to executed trades
                snipe_order['executed_trades'].append(executed_trade)
                snipe_order['total_spent'] += trade_amount
                
                # Update in database
                await self.db.update_snipe_order(snipe_order['_id'], {
                    'executed_trades': snipe_order['executed_trades'],
                    'total_spent': snipe_order['total_spent']
                })
                
                # Send snipe alert
                await self._send_snipe_alert(user_id, {
                    'token_symbol': token_info.get('symbol', 'Unknown'),
                    'amount': trade_amount,
                    'signature': result.get('signature'),
                    'snipe_order_id': snipe_order['_id']
                })
                
                logger.info(f"Snipe trade executed for user {user_id}: {token_info.get('symbol', 'Unknown')} - {trade_amount} SOL")
                
                return {
                    'success': True,
                    'trade_id': result.get('trade_id'),
                    'signature': result.get('signature'),
                    'amount': trade_amount,
                    'token_symbol': token_info.get('symbol', 'Unknown')
                }
            else:
                return result
                
        except Exception as e:
            logger.error(f"Error executing snipe trade: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _send_snipe_alert(self, user_id: int, snipe_data: Dict[str, Any]):
        """Send snipe trade alert to user"""
        try:
            from utils.monitoring import AlertManager
            alert_manager = AlertManager()
            
            message = (
                f"🎯 **Snipe Trade Executed!**\n\n"
                f"🪙 Token: {snipe_data['token_symbol']}\n"
                f"💰 Amount: {snipe_data['amount']:.4f} SOL\n"
                f"🔗 Transaction: `{snipe_data['signature'][:8]}...`\n"
                f"📊 Order ID: {snipe_data['snipe_order_id']}\n"
                f"✅ Status: Completed"
            )
            
            await alert_manager.send_user_alert(user_id, message, "snipe")
            
        except Exception as e:
            logger.error(f"Error sending snipe alert: {e}")
    
    async def get_user_snipe_orders(self, user_id: int) -> List[Dict[str, Any]]:
        """Get user's snipe orders"""
        try:
            return await self.db.get_user_snipe_orders(user_id)
        except Exception as e:
            logger.error(f"Error getting snipe orders: {e}")
            return []
    
    async def cancel_snipe_order(self, user_id: int, order_id: str) -> Tuple[bool, str]:
        """Cancel a snipe order"""
        try:
            success = await self.db.cancel_snipe_order(user_id, order_id)
            
            if success:
                return True, "Snipe order cancelled successfully"
            else:
                return False, "Failed to cancel snipe order"
                
        except Exception as e:
            logger.error(f"Error cancelling snipe order: {e}")
            return False, f"Error: {str(e)}"
    
    async def _get_token_price_at_time(self, token_address: str) -> float:
        """Get token price at current time"""
        try:
            price_data = await self.solana.get_token_price(token_address)
            return price_data.get('price', 0.0)
        except Exception as e:
            logger.error(f"Error getting token price: {e}")
            return 0.0

    async def _monitor_stop_losses(self):
        """Monitor stop loss orders for execution"""
        while self.is_running:
            try:
                # Get all completed trades with stop loss settings
                completed_trades = await self.db.get_completed_trades_with_stop_loss()
                
                for trade in completed_trades:
                    try:
                        await self._check_stop_loss(trade)
                    except Exception as e:
                        logger.error(f"Error checking stop loss for trade {trade.get('_id')}: {e}")
                        
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in stop loss monitoring: {e}")
                await asyncio.sleep(60)
                
    async def _check_stop_loss(self, trade: Dict[str, Any]):
        """Check if stop loss should be triggered for a trade"""
        try:
            # Get current token price
            token_address = trade.get('output_token')
            if not token_address:
                return
                
            price_data = await self.solana.get_token_price(token_address)
            current_price = price_data.get('price', 0)
            
            if current_price == 0:
                return  # Can't get price, skip this check
                
            # Get entry price from trade
            entry_price = trade.get('entry_price', 0)
            if entry_price == 0:
                return  # No entry price, skip
                
            # Calculate price change percentage
            price_change_pct = ((current_price - entry_price) / entry_price) * 100
            
            # Get stop loss percentage
            stop_loss_pct = trade.get('stop_loss', 0)
            if stop_loss_pct == 0:
                return  # No stop loss set
                
            # Check if stop loss should trigger (price dropped below threshold)
            if price_change_pct <= -stop_loss_pct:
                logger.info(f"Stop loss triggered for trade {trade.get('_id')}: {price_change_pct:.2f}%")
                
                # Execute stop loss sell
                await self._execute_stop_loss(trade, current_price)
                
        except Exception as e:
            logger.error(f"Error checking stop loss: {e}")
            
    async def _execute_stop_loss(self, trade: Dict[str, Any], current_price: float):
        """Execute stop loss order"""
        try:
            user_id = trade.get('user_id')
            token_address = trade.get('output_token')
            token_amount = trade.get('output_amount', 0)
            
            if token_amount <= 0:
                return
                
            # Execute market sell for the position
            result = await self.execute_market_sell(
                user_id, token_address, token_amount
            )
            
            if result.get('success'):
                # Update original trade with stop loss info
                await self.db.update_trade_stop_loss_triggered(
                    str(trade.get('_id')),
                    {
                        'stop_loss_triggered': True,
                        'stop_loss_triggered_at': datetime.utcnow(),
                        'stop_loss_price': current_price,
                        'stop_loss_signature': result.get('signature')
                    }
                )
                
                # Send stop loss alert
                await self._send_stop_loss_alert(user_id, {
                    'token_symbol': trade.get('token_symbol', 'Unknown'),
                    'entry_price': trade.get('entry_price', 0),
                    'stop_loss_price': current_price,
                    'amount': token_amount,
                    'signature': result.get('signature')
                })
                
                logger.info(f"Stop loss executed successfully for trade {trade.get('_id')}")
            else:
                logger.error(f"Stop loss execution failed: {result.get('error')}")
                
        except Exception as e:
            logger.error(f"Error executing stop loss: {e}")
            
    async def _send_stop_loss_alert(self, user_id: int, stop_loss_data: Dict[str, Any]):
        """Send stop loss alert to user"""
        try:
            from utils.monitoring import AlertManager
            alert_manager = AlertManager()
            
            message = (
                f"🛑 **Stop Loss Triggered!**\n\n"
                f"🪙 Token: {stop_loss_data['token_symbol']}\n"
                f"💰 Amount: {stop_loss_data['amount']:.4f}\n"
                f"📉 Entry Price: ${stop_loss_data['entry_price']:.6f}\n"
                f"📉 Stop Loss Price: ${stop_loss_data['stop_loss_price']:.6f}\n"
                f"🔗 Transaction: `{stop_loss_data['signature'][:8]}...`\n"
                f"✅ Stop loss executed successfully"
            )
            
            await alert_manager.send_user_alert(user_id, message, "stop_loss")
            
        except Exception as e:
            logger.error(f"Error sending stop loss alert: {e}")

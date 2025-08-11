"""
Database service using MongoDB for high-performance data storage
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import IndexModel, ASCENDING, DESCENDING
import json

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.client = None
        self.db = None
        
    async def connect(self):
        """Connect to MongoDB"""
        try:
            self.client = AsyncIOMotorClient(self.connection_string)
            self.db = self.client.solana_trading_bot
            
            # Create indexes for performance
            await self._create_indexes()
            
            logger.info("Database connected successfully")
            
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
            
    async def disconnect(self):
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
            
    async def _create_indexes(self):
        """Create database indexes for optimal performance"""
        try:
            # Users collection indexes
            await self.db.users.create_indexes([
                IndexModel([("user_id", ASCENDING)], unique=True),
                IndexModel([("username", ASCENDING)]),
                IndexModel([("created_at", DESCENDING)])
            ])
            
            # Wallets collection indexes
            await self.db.wallets.create_indexes([
                IndexModel([("address", ASCENDING)], unique=True),
                IndexModel([("user_id", ASCENDING)]),
                IndexModel([("is_whale", ASCENDING)]),
                IndexModel([("last_activity", DESCENDING)])
            ])
            
            # Transactions collection indexes
            await self.db.transactions.create_indexes([
                IndexModel([("signature", ASCENDING)], unique=True),
                IndexModel([("wallet_address", ASCENDING)]),
                IndexModel([("block_time", DESCENDING)]),
                IndexModel([("amount_usd", DESCENDING)]),
                IndexModel([("type", ASCENDING)])
            ])
            
            # Alerts collection indexes
            await self.db.alerts.create_indexes([
                IndexModel([("user_id", ASCENDING)]),
                IndexModel([("wallet_address", ASCENDING)]),
                IndexModel([("created_at", DESCENDING)]),
                IndexModel([("is_sent", ASCENDING)])
            ])
            
            # Trades collection indexes
            await self.db.trades.create_indexes([
                IndexModel([("user_id", ASCENDING)]),
                IndexModel([("signature", ASCENDING)], unique=True),
                IndexModel([("created_at", DESCENDING)]),
                IndexModel([("status", ASCENDING)])
            ])
            
            logger.info("Database indexes created successfully")
            
        except Exception as e:
            logger.error(f"Error creating indexes: {e}")
            
    # User Management
    async def create_user(self, user_id: int, username: str) -> Dict[str, Any]:
        """Create or update user"""
        try:
            user_data = {
                'user_id': user_id,
                'username': username,
                'subscription_tier': 'free',
                'created_at': datetime.utcnow(),
                'settings': {
                    'max_trade_amount': 1.0,
                    'stop_loss': 10.0,
                    'slippage': 0.5,
                    'alerts_enabled': True,
                    'auto_trading': False
                },
                'stats': {
                    'total_trades': 0,
                    'successful_trades': 0,
                    'total_profit_loss': 0.0,
                    'wallets_monitored': 0
                }
            }
            
            result = await self.db.users.update_one(
                {'user_id': user_id},
                {'$setOnInsert': user_data, '$set': {'last_active': datetime.utcnow()}},
                upsert=True
            )
            
            return user_data
            
        except Exception as e:
            logger.error(f"Error creating user {user_id}: {e}")
            raise
            
    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        try:
            return await self.db.users.find_one({'user_id': user_id})
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            return None
            
    async def get_user_settings(self, user_id: int) -> Dict[str, Any]:
        """Get user settings"""
        try:
            user = await self.get_user(user_id)
            if user:
                return user.get('settings', {})
            return {}
        except Exception as e:
            logger.error(f"Error getting user settings {user_id}: {e}")
            return {}
            
    async def update_user_settings(self, user_id: int, settings: Dict[str, Any]) -> bool:
        """Update user settings"""
        try:
            result = await self.db.users.update_one(
                {'user_id': user_id},
                {'$set': {'settings': settings}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating user settings {user_id}: {e}")
            return False
            
    # Wallet Management
    async def add_user_wallet(self, user_id: int, address: str) -> bool:
        """Add wallet to user's monitoring list"""
        try:
            wallet_data = {
                'address': address,
                'user_id': user_id,
                'added_at': datetime.utcnow(),
                'is_active': True,
                'is_whale': False,
                'last_activity': None,
                'balance_history': [],
                'alert_settings': {
                    'large_transactions': True,
                    'new_tokens': True,
                    'whale_activity': True
                }
            }
            
            # Insert wallet if not exists
            result = await self.db.wallets.update_one(
                {'address': address, 'user_id': user_id},
                {'$setOnInsert': wallet_data},
                upsert=True
            )
            
            # Update user stats
            if result.upserted_id:
                await self.db.users.update_one(
                    {'user_id': user_id},
                    {'$inc': {'stats.wallets_monitored': 1}}
                )
                
            return True
            
        except Exception as e:
            logger.error(f"Error adding wallet {address} for user {user_id}: {e}")
            return False
            
    async def get_user_wallets(self, user_id: int) -> List[Dict[str, Any]]:
        """Get user's monitored wallets"""
        try:
            cursor = self.db.wallets.find(
                {'user_id': user_id, 'is_active': True}
            ).sort('added_at', DESCENDING)
            
            return await cursor.to_list(length=None)
            
        except Exception as e:
            logger.error(f"Error getting wallets for user {user_id}: {e}")
            return []
            
    async def update_wallet_data(self, address: str, data: Dict[str, Any]) -> bool:
        """Update wallet data"""
        try:
            update_data = {
                'last_activity': datetime.utcnow(),
                **data
            }
            
            result = await self.db.wallets.update_one(
                {'address': address},
                {'$set': update_data}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error updating wallet data {address}: {e}")
            return False
            
    async def mark_wallet_as_whale(self, address: str, whale_data: Dict[str, Any]) -> bool:
        """Mark wallet as whale"""
        try:
            result = await self.db.wallets.update_one(
                {'address': address},
                {
                    '$set': {
                        'is_whale': True,
                        'whale_data': whale_data,
                        'whale_detected_at': datetime.utcnow()
                    }
                }
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error marking wallet as whale {address}: {e}")
            return False
            
    # Transaction Management
    async def store_transaction(self, tx_data: Dict[str, Any]) -> bool:
        """Store transaction data"""
        try:
            tx_data['stored_at'] = datetime.utcnow()
            
            result = await self.db.transactions.update_one(
                {'signature': tx_data['signature']},
                {'$setOnInsert': tx_data},
                upsert=True
            )
            
            return result.upserted_id is not None
            
        except Exception as e:
            logger.error(f"Error storing transaction: {e}")
            return False
            
    async def get_wallet_transactions(self, address: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get transactions for a wallet"""
        try:
            cursor = self.db.transactions.find(
                {'wallet_address': address}
            ).sort('block_time', DESCENDING).limit(limit)
            
            return await cursor.to_list(length=None)
            
        except Exception as e:
            logger.error(f"Error getting transactions for {address}: {e}")
            return []
            
    async def get_large_transactions(self, min_amount_usd: float = 10000, hours: int = 24) -> List[Dict[str, Any]]:
        """Get large transactions (whale activity)"""
        try:
            since = datetime.utcnow() - timedelta(hours=hours)
            
            cursor = self.db.transactions.find({
                'amount_usd': {'$gte': min_amount_usd},
                'block_time': {'$gte': since.timestamp()}
            }).sort('amount_usd', DESCENDING).limit(100)
            
            return await cursor.to_list(length=None)
            
        except Exception as e:
            logger.error(f"Error getting large transactions: {e}")
            return []
            
    # Alert Management
    async def create_alert(self, user_id: int, alert_data: Dict[str, Any]) -> bool:
        """Create alert for user"""
        try:
            alert = {
                'user_id': user_id,
                'created_at': datetime.utcnow(),
                'is_sent': False,
                **alert_data
            }
            
            result = await self.db.alerts.insert_one(alert)
            return result.inserted_id is not None
            
        except Exception as e:
            logger.error(f"Error creating alert: {e}")
            return False
            
    async def get_pending_alerts(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get pending alerts to send"""
        try:
            cursor = self.db.alerts.find(
                {'is_sent': False}
            ).sort('created_at', ASCENDING).limit(limit)
            
            return await cursor.to_list(length=None)
            
        except Exception as e:
            logger.error(f"Error getting pending alerts: {e}")
            return []
            
    async def mark_alert_sent(self, alert_id: str) -> bool:
        """Mark alert as sent"""
        try:
            from bson import ObjectId
            
            result = await self.db.alerts.update_one(
                {'_id': ObjectId(alert_id)},
                {'$set': {'is_sent': True, 'sent_at': datetime.utcnow()}}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error marking alert sent: {e}")
            return False
            
    # Trading Management
    async def store_trade(self, trade_data: Dict[str, Any]) -> bool:
        """Store trade execution data"""
        try:
            trade_data['created_at'] = datetime.utcnow()
            
            result = await self.db.trades.insert_one(trade_data)
            return result.inserted_id is not None
            
        except Exception as e:
            logger.error(f"Error storing trade: {e}")
            return False
            
    async def get_user_trades(self, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Get user's trade history"""
        try:
            cursor = self.db.trades.find(
                {'user_id': user_id}
            ).sort('created_at', DESCENDING).limit(limit)
            
            return await cursor.to_list(length=None)
            
        except Exception as e:
            logger.error(f"Error getting trades for user {user_id}: {e}")
            return []
            
    async def update_trade_status(self, trade_id: str, status: str, result_data: Dict[str, Any] = None) -> bool:
        """Update trade status"""
        try:
            from bson import ObjectId
            
            update_data = {
                'status': status,
                'updated_at': datetime.utcnow()
            }
            
            if result_data:
                update_data.update(result_data)
                
            result = await self.db.trades.update_one(
                {'_id': ObjectId(trade_id)},
                {'$set': update_data}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error updating trade status: {e}")
            return False
            
    # Analytics
    async def get_wallet_analytics(self, address: str, days: int = 30) -> Dict[str, Any]:
        """Get wallet analytics"""
        try:
            since = datetime.utcnow() - timedelta(days=days)
            
            # Get transaction stats
            pipeline = [
                {
                    '$match': {
                        'wallet_address': address,
                        'block_time': {'$gte': since.timestamp()}
                    }
                },
                {
                    '$group': {
                        '_id': None,
                        'total_transactions': {'$sum': 1},
                        'total_volume': {'$sum': '$amount_usd'},
                        'avg_transaction_size': {'$avg': '$amount_usd'},
                        'max_transaction': {'$max': '$amount_usd'}
                    }
                }
            ]
            
            cursor = self.db.transactions.aggregate(pipeline)
            stats = await cursor.to_list(length=1)
            
            if stats:
                return stats[0]
            else:
                return {
                    'total_transactions': 0,
                    'total_volume': 0,
                    'avg_transaction_size': 0,
                    'max_transaction': 0
                }
                
        except Exception as e:
            logger.error(f"Error getting wallet analytics: {e}")
            return {}
            
    async def get_top_wallets(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get top wallets by transaction volume"""
        try:
            pipeline = [
                {
                    '$group': {
                        '_id': '$wallet_address',
                        'total_volume': {'$sum': '$amount_usd'},
                        'transaction_count': {'$sum': 1},
                        'last_activity': {'$max': '$block_time'}
                    }
                },
                {'$sort': {'total_volume': -1}},
                {'$limit': limit}
            ]
            
            cursor = self.db.transactions.aggregate(pipeline)
            wallets = await cursor.to_list(length=limit)
            
            return wallets
            
        except Exception as e:
            logger.error(f"Error getting top wallets: {e}")
            return []

    # New methods for enhanced functionality
    async def get_user_copy_stats(self, user_id: int) -> Dict[str, Any]:
        """Get user's copy trading statistics"""
        try:
            pipeline = [
                {'$match': {'user_id': user_id, 'type': 'copy_trade'}},
                {
                    '$group': {
                        '_id': None,
                        'total_trades': {'$sum': 1},
                        'successful_trades': {
                            '$sum': {'$cond': [{'$eq': ['$status', 'completed']}, 1, 0]}
                        },
                        'total_profit': {'$sum': '$profit_sol'},
                        'total_volume': {'$sum': '$amount_sol'}
                    }
                }
            ]
            
            cursor = self.db.trades.aggregate(pipeline)
            result = await cursor.to_list(length=1)
            
            if result:
                stats = result[0]
                success_rate = (stats['successful_trades'] / stats['total_trades'] * 100) if stats['total_trades'] > 0 else 0
                return {
                    'total_trades': stats['total_trades'],
                    'success_rate': success_rate,
                    'total_profit': stats['total_profit'],
                    'total_volume': stats['total_volume']
                }
            
            return {'total_trades': 0, 'success_rate': 0, 'total_profit': 0, 'total_volume': 0}
            
        except Exception as e:
            logger.error(f"Error getting copy stats: {e}")
            return {'total_trades': 0, 'success_rate': 0, 'total_profit': 0, 'total_volume': 0}

    async def get_recent_whale_activity(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent whale activity"""
        try:
            # Get recent large transactions
            pipeline = [
                {'$match': {'amount_usd': {'$gte': 100000}}},  # $100k+ transactions
                {'$sort': {'block_time': -1}},
                {'$limit': limit},
                {
                    '$lookup': {
                        'from': 'wallets',
                        'localField': 'wallet_address',
                        'foreignField': 'address',
                        'as': 'wallet_info'
                    }
                }
            ]
            
            cursor = self.db.transactions.aggregate(pipeline)
            activities = await cursor.to_list(length=limit)
            
            return activities
            
        except Exception as e:
            logger.error(f"Error getting whale activity: {e}")
            return []

    async def get_whale_statistics(self) -> Dict[str, Any]:
        """Get whale statistics"""
        try:
            # Count total whales
            whale_count = await self.db.wallets.count_documents({'is_whale': True})
            
            # Get today's large transactions
            today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            today_txs = await self.db.transactions.count_documents({
                'amount_usd': {'$gte': 100000},
                'block_time': {'$gte': today.timestamp()}
            })
            
            # Get average transaction size
            pipeline = [
                {'$match': {'amount_usd': {'$gte': 100000}}},
                {
                    '$group': {
                        '_id': None,
                        'avg_amount': {'$avg': '$amount_sol'},
                        'total_volume': {'$sum': '$amount_sol'}
                    }
                }
            ]
            
            cursor = self.db.transactions.aggregate(pipeline)
            result = await cursor.to_list(length=1)
            
            avg_amount = result[0]['avg_amount'] if result else 0
            
            return {
                'total_whales': whale_count,
                'today_transactions': today_txs,
                'avg_transaction_size': avg_amount
            }
            
        except Exception as e:
            logger.error(f"Error getting whale statistics: {e}")
            return {'total_whales': 0, 'today_transactions': 0, 'avg_transaction_size': 0}

    async def get_token_info(self, token_address: str) -> Dict[str, Any]:
        """Get token information from database"""
        try:
            token = await self.db.tokens.find_one({'address': token_address})
            return token or {}
        except Exception as e:
            logger.error(f"Error getting token info: {e}")
            return {}

    async def store_token_info(self, token_data: Dict[str, Any]) -> bool:
        """Store token information"""
        try:
            await self.db.tokens.update_one(
                {'address': token_data['address']},
                {'$set': token_data},
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Error storing token info: {e}")
            return False

    async def get_user_orders(self, user_id: int, status: str = None) -> List[Dict[str, Any]]:
        """Get user's limit orders"""
        try:
            query = {'user_id': user_id}
            if status:
                query['status'] = status
                
            cursor = self.db.orders.find(query).sort('created_at', -1)
            orders = await cursor.to_list(length=50)
            return orders
            
        except Exception as e:
            logger.error(f"Error getting user orders: {e}")
            return []

    async def create_limit_order(self, order_data: Dict[str, Any]) -> str:
        """Create a new limit order"""
        try:
            order_data['created_at'] = datetime.utcnow()
            order_data['status'] = 'pending'
            
            result = await self.db.orders.insert_one(order_data)
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"Error creating limit order: {e}")
            return None

    async def update_order_status(self, order_id: str, status: str, result_data: Dict[str, Any] = None) -> bool:
        """Update order status"""
        try:
            update_data = {'status': status, 'updated_at': datetime.utcnow()}
            if result_data:
                update_data.update(result_data)
                
            await self.db.orders.update_one(
                {'_id': order_id},
                {'$set': update_data}
            )
            return True
            
        except Exception as e:
            logger.error(f"Error updating order status: {e}")
            return False

    async def get_market_trends(self, hours: int = 24) -> Dict[str, Any]:
        """Get market trends and statistics"""
        try:
            # Get trending tokens
            pipeline = [
                {
                    '$match': {
                        'block_time': {
                            '$gte': (datetime.utcnow() - timedelta(hours=hours)).timestamp()
                        }
                    }
                },
                {
                    '$group': {
                        '_id': '$token_address',
                        'volume': {'$sum': '$amount_usd'},
                        'transaction_count': {'$sum': 1},
                        'unique_wallets': {'$addToSet': '$wallet_address'}
                    }
                },
                {
                    '$project': {
                        'token_address': '$_id',
                        'volume': 1,
                        'transaction_count': 1,
                        'unique_wallets': {'$size': '$unique_wallets'}
                    }
                },
                {'$sort': {'volume': -1}},
                {'$limit': 10}
            ]
            
            cursor = self.db.transactions.aggregate(pipeline)
            trending_tokens = await cursor.to_list(length=10)
            
            # Get market statistics
            total_volume = sum(token['volume'] for token in trending_tokens)
            total_transactions = sum(token['transaction_count'] for token in trending_tokens)
            
            return {
                'trending_tokens': trending_tokens,
                'total_volume': total_volume,
                'total_transactions': total_transactions,
                'period_hours': hours
            }
            
        except Exception as e:
            logger.error(f"Error getting market trends: {e}")
            return {'trending_tokens': [], 'total_volume': 0, 'total_transactions': 0, 'period_hours': hours}

    async def get_user_analytics(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """Get comprehensive user analytics"""
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Get user's trading statistics
            pipeline = [
                {
                    '$match': {
                        'user_id': user_id,
                        'created_at': {'$gte': start_date}
                    }
                },
                {
                    '$group': {
                        '_id': None,
                        'total_trades': {'$sum': 1},
                        'successful_trades': {
                            '$sum': {'$cond': [{'$eq': ['$status', 'completed']}, 1, 0]}
                        },
                        'total_volume': {'$sum': '$amount_sol'},
                        'total_profit': {'$sum': '$profit_sol'},
                        'avg_trade_size': {'$avg': '$amount_sol'}
                    }
                }
            ]
            
            cursor = self.db.trades.aggregate(pipeline)
            trade_stats = await cursor.to_list(length=1)
            
            # Get wallet monitoring statistics
            monitored_wallets = await self.db.wallets.count_documents({
                'user_id': user_id,
                'is_active': True
            })
            
            # Get alert statistics
            alert_count = await self.db.alerts.count_documents({
                'user_id': user_id,
                'created_at': {'$gte': start_date}
            })
            
            if trade_stats:
                stats = trade_stats[0]
                success_rate = (stats['successful_trades'] / stats['total_trades'] * 100) if stats['total_trades'] > 0 else 0
                
                return {
                    'total_trades': stats['total_trades'],
                    'success_rate': success_rate,
                    'total_volume': stats['total_volume'],
                    'total_profit': stats['total_profit'],
                    'avg_trade_size': stats['avg_trade_size'],
                    'monitored_wallets': monitored_wallets,
                    'alerts_received': alert_count,
                    'period_days': days
                }
            
            return {
                'total_trades': 0,
                'success_rate': 0,
                'total_volume': 0,
                'total_profit': 0,
                'avg_trade_size': 0,
                'monitored_wallets': monitored_wallets,
                'alerts_received': alert_count,
                'period_days': days
            }
            
        except Exception as e:
            logger.error(f"Error getting user analytics: {e}")
            return {
                'total_trades': 0,
                'success_rate': 0,
                'total_volume': 0,
                'total_profit': 0,
                'avg_trade_size': 0,
                'monitored_wallets': 0,
                'alerts_received': 0,
                'period_days': days
            }

    async def store_copy_trading_subscription(self, subscription_data: Dict[str, Any]) -> bool:
        """Store copy trading subscription"""
        try:
            result = await self.db.copy_trading_subscriptions.insert_one(subscription_data)
            return bool(result.inserted_id)
        except Exception as e:
            logger.error(f"Error storing copy trading subscription: {e}")
            return False
    
    async def get_copy_trading_users(self, wallet_address: str) -> List[Dict[str, Any]]:
        """Get all users copying a specific wallet"""
        try:
            cursor = self.db.copy_trading_subscriptions.find({
                'wallet_address': wallet_address,
                'is_active': True
            })
            return await cursor.to_list(length=None)
        except Exception as e:
            logger.error(f"Error getting copy trading users: {e}")
            return []
    
    async def get_user_copy_trading_subscriptions(self, user_id: int) -> List[Dict[str, Any]]:
        """Get user's copy trading subscriptions"""
        try:
            cursor = self.db.copy_trading_subscriptions.find({
                'user_id': user_id,
                'is_active': True
            })
            return await cursor.to_list(length=None)
        except Exception as e:
            logger.error(f"Error getting user copy trading subscriptions: {e}")
            return []
    
    async def remove_copy_trading_subscription(self, user_id: int, wallet_address: str) -> bool:
        """Remove copy trading subscription"""
        try:
            result = await self.db.copy_trading_subscriptions.update_one(
                {'user_id': user_id, 'wallet_address': wallet_address},
                {'$set': {'is_active': False, 'unsubscribed_at': datetime.utcnow()}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error removing copy trading subscription: {e}")
            return False
    
    async def update_copy_trading_settings(self, user_id: int, wallet_address: str, settings: Dict[str, Any]) -> bool:
        """Update copy trading settings"""
        try:
            result = await self.db.copy_trading_subscriptions.update_one(
                {'user_id': user_id, 'wallet_address': wallet_address},
                {'$set': {'copy_settings': settings, 'updated_at': datetime.utcnow()}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating copy trading settings: {e}")
            return False
    
    async def update_copy_trading_stats(self, user_id: int, stats: Dict[str, Any]) -> bool:
        """Update copy trading statistics"""
        try:
            result = await self.db.users.update_one(
                {'user_id': user_id},
                {'$inc': stats}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating copy trading stats: {e}")
            return False
    
    async def store_snipe_order(self, snipe_order: Dict[str, Any]) -> str:
        """Store snipe order"""
        try:
            result = await self.db.snipe_orders.insert_one(snipe_order)
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error storing snipe order: {e}")
            return None
    
    async def get_user_snipe_orders(self, user_id: int) -> List[Dict[str, Any]]:
        """Get user's snipe orders"""
        try:
            cursor = self.db.snipe_orders.find({
                'user_id': user_id,
                'status': 'active'
            }).sort('created_at', -1)
            return await cursor.to_list(length=None)
        except Exception as e:
            logger.error(f"Error getting user snipe orders: {e}")
            return []
    
    async def update_snipe_order(self, order_id: str, updates: Dict[str, Any]) -> bool:
        """Update snipe order"""
        try:
            from bson import ObjectId
            result = await self.db.snipe_orders.update_one(
                {'_id': ObjectId(order_id)},
                {'$set': updates}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating snipe order: {e}")
            return False
    
    async def cancel_snipe_order(self, user_id: int, order_id: str) -> bool:
        """Cancel snipe order"""
        try:
            from bson import ObjectId
            result = await self.db.snipe_orders.update_one(
                {'_id': ObjectId(order_id), 'user_id': user_id},
                {'$set': {'status': 'cancelled', 'cancelled_at': datetime.utcnow()}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error cancelling snipe order: {e}")
            return False
    
    async def get_active_snipe_orders(self) -> List[Dict[str, Any]]:
        """Get all active snipe orders"""
        try:
            cursor = self.db.snipe_orders.find({'status': 'active'})
            return await cursor.to_list(length=None)
        except Exception as e:
            logger.error(f"Error getting active snipe orders: {e}")
            return []

    async def get_all_pending_orders(self, status: str = 'pending') -> List[Dict[str, Any]]:
        """Get all pending orders regardless of user"""
        try:
            query = {'status': status}
            cursor = self.db.orders.find(query).sort('created_at', -1)
            orders = await cursor.to_list(length=100)
            return orders
            
        except Exception as e:
            logger.error(f"Error getting all pending orders: {e}")
            return []

    async def get_completed_trades_with_stop_loss(self) -> List[Dict[str, Any]]:
        """Get completed trades that have stop loss settings"""
        try:
            cursor = self.db.trades.find({
                'status': 'completed',
                'stop_loss': {'$exists': True, '$ne': None, '$gt': 0},
                'stop_loss_triggered': {'$ne': True}  # Not already triggered
            })
            return await cursor.to_list(length=None)
        except Exception as e:
            logger.error(f"Error getting completed trades with stop loss: {e}")
            return []
    
    async def update_trade_stop_loss_triggered(self, trade_id: str, stop_loss_data: Dict[str, Any]) -> bool:
        """Update trade with stop loss trigger information"""
        try:
            from bson import ObjectId
            result = await self.db.trades.update_one(
                {'_id': ObjectId(trade_id)},
                {'$set': stop_loss_data}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating trade stop loss: {e}")
            return False
    
    async def get_trade_by_id(self, trade_id: str) -> Optional[Dict[str, Any]]:
        """Get trade by ID"""
        try:
            from bson import ObjectId
            return await self.db.trades.find_one({'_id': ObjectId(trade_id)})
        except Exception as e:
            logger.error(f"Error getting trade by ID: {e}")
            return None
    
    async def update_trade_entry_price(self, trade_id: str, entry_price: float) -> bool:
        """Update trade with entry price"""
        try:
            from bson import ObjectId
            result = await self.db.trades.update_one(
                {'_id': ObjectId(trade_id)},
                {'$set': {'entry_price': entry_price}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating trade entry price: {e}")
            return False

    async def store_backup(self, backup_name: str, backup_data: Dict[str, Any]) -> str:
        """Store backup data in database"""
        try:
            backup_doc = {
                'name': backup_name,
                'data': backup_data,
                'created_at': datetime.utcnow(),
                'size_bytes': len(str(backup_data))
            }
            
            result = await self.db.backups.insert_one(backup_doc)
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"Error storing backup: {e}")
            return None
    
    async def get_user_statistics(self) -> Dict[str, Any]:
        """Get comprehensive user statistics"""
        try:
            pipeline = [
                {
                    '$group': {
                        '_id': None,
                        'total_users': {'$sum': 1},
                        'active_users_24h': {
                            '$sum': {
                                '$cond': [
                                    {'$gte': ['$last_active', datetime.utcnow() - timedelta(hours=24)]},
                                    1, 0
                                ]
                            }
                        },
                        'premium_users': {
                            '$sum': {
                                '$cond': [
                                    {'$eq': ['$subscription_tier', 'premium']},
                                    1, 0
                                ]
                            }
                        },
                        'pro_users': {
                            '$sum': {
                                '$cond': [
                                    {'$eq': ['$subscription_tier', 'pro']},
                                    1, 0
                                ]
                            }
                        }
                    }
                }
            ]
            
            cursor = self.db.users.aggregate(pipeline)
            result = await cursor.to_list(length=1)
            
            if result:
                return result[0]
            else:
                return {
                    'total_users': 0,
                    'active_users_24h': 0,
                    'premium_users': 0,
                    'pro_users': 0
                }
                
        except Exception as e:
            logger.error(f"Error getting user statistics: {e}")
            return {}
    
    async def get_trading_statistics(self) -> Dict[str, Any]:
        """Get comprehensive trading statistics"""
        try:
            pipeline = [
                {
                    '$group': {
                        '_id': None,
                        'total_trades': {'$sum': 1},
                        'completed_trades': {
                            '$sum': {
                                '$cond': [
                                    {'$eq': ['$status', 'completed']},
                                    1, 0
                                ]
                            }
                        },
                        'failed_trades': {
                            '$sum': {
                                '$cond': [
                                    {'$eq': ['$status', 'failed']},
                                    1, 0
                                ]
                            }
                        },
                        'total_volume_sol': {'$sum': '$amount'},
                        'total_volume_usd': {'$sum': '$amount_usd'}
                    }
                }
            ]
            
            cursor = self.db.trades.aggregate(pipeline)
            result = await cursor.to_list(length=1)
            
            if result:
                return result[0]
            else:
                return {
                    'total_trades': 0,
                    'completed_trades': 0,
                    'failed_trades': 0,
                    'total_volume_sol': 0,
                    'total_volume_usd': 0
                }
                
        except Exception as e:
            logger.error(f"Error getting trading statistics: {e}")
            return {}

    # Payment and Wallet Management Methods
    async def store_user_wallet(self, wallet_data: Dict[str, Any]) -> bool:
        """Store user wallet in database"""
        try:
            result = await self.db.user_wallets.insert_one(wallet_data)
            return bool(result.inserted_id)
        except Exception as e:
            logger.error(f"Error storing user wallet: {e}")
            return False

    async def get_user_primary_wallet(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user's primary wallet"""
        try:
            return await self.db.user_wallets.find_one({
                'user_id': user_id,
                'is_active': True
            })
        except Exception as e:
            logger.error(f"Error getting user primary wallet: {e}")
            return None

    async def get_user_wallet_by_address(self, address: str) -> Optional[Dict[str, Any]]:
        """Get wallet by address"""
        try:
            return await self.db.user_wallets.find_one({'address': address})
        except Exception as e:
            logger.error(f"Error getting wallet by address: {e}")
            return None

    async def update_user_subscription(self, user_id: int, tier: str, payment_date: datetime) -> bool:
        """Update user subscription tier"""
        try:
            result = await self.db.users.update_one(
                {'user_id': user_id},
                {
                    '$set': {
                        'subscription_tier': tier,
                        'subscription_paid_at': payment_date,
                        'subscription_expires_at': payment_date + timedelta(days=30)
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating user subscription: {e}")
            return False

    async def record_fee_payment(self, user_id: int, payment_data: Dict[str, Any]) -> bool:
        """Record fee payment in database"""
        try:
            payment_data['user_id'] = user_id
            payment_data['created_at'] = datetime.utcnow()
            payment_data['status'] = 'completed'
            
            result = await self.db.payments.insert_one(payment_data)
            return bool(result.inserted_id)
        except Exception as e:
            logger.error(f"Error recording fee payment: {e}")
            return False

    async def get_recent_payment(self, user_id: int, payment_type: str, hours: int = 24) -> Optional[Dict[str, Any]]:
        """Get recent payment by type"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            return await self.db.payments.find_one({
                'user_id': user_id,
                'type': payment_type,
                'created_at': {'$gte': cutoff_time},
                'status': 'completed'
            })
        except Exception as e:
            logger.error(f"Error getting recent payment: {e}")
            return None

    async def get_pending_payments(self) -> List[Dict[str, Any]]:
        """Get pending payments"""
        try:
            cursor = self.db.payments.find({
                'status': 'pending'
            }).sort('created_at', DESCENDING)
            
            return await cursor.to_list(length=None)
        except Exception as e:
            logger.error(f"Error getting pending payments: {e}")
            return []

    async def confirm_payment(self, payment_id: str) -> bool:
        """Confirm payment"""
        try:
            result = await self.db.payments.update_one(
                {'_id': payment_id},
                {'$set': {'status': 'completed', 'confirmed_at': datetime.utcnow()}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error confirming payment: {e}")
            return False

    async def expire_payment(self, payment_id: str) -> bool:
        """Expire payment"""
        try:
            result = await self.db.payments.update_one(
                {'_id': payment_id},
                {'$set': {'status': 'expired', 'expired_at': datetime.utcnow()}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error expiring payment: {e}")
            return False

    async def get_expiring_subscriptions(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get users with expiring subscriptions"""
        try:
            cutoff_date = datetime.utcnow() + timedelta(days=days)
            cursor = self.db.users.find({
                'subscription_expires_at': {'$lte': cutoff_date},
                'subscription_tier': {'$ne': 'free'}
            })
            
            return await cursor.to_list(length=None)
        except Exception as e:
            logger.error(f"Error getting expiring subscriptions: {e}")
            return []

    async def get_payment_statistics(self) -> Dict[str, Any]:
        """Get payment statistics"""
        try:
            pipeline = [
                {
                    '$group': {
                        '_id': None,
                        'total_payments': {'$sum': 1},
                        'total_amount': {'$sum': '$amount'},
                        'wallet_creation_fees': {
                            '$sum': {
                                '$cond': [
                                    {'$eq': ['$type', 'wallet_creation_fee']},
                                    '$amount', 0
                                ]
                            }
                        },
                        'subscription_fees': {
                            '$sum': {
                                '$cond': [
                                    {'$eq': ['$type', 'subscription_fee']},
                                    '$amount', 0
                                ]
                            }
                        },
                        'trade_fees': {
                            '$sum': {
                                '$cond': [
                                    {'$eq': ['$type', 'trade_fee']},
                                    '$amount', 0
                                ]
                            }
                        }
                    }
                }
            ]
            
            cursor = self.db.payments.aggregate(pipeline)
            result = await cursor.to_list(length=1)
            
            if result:
                return result[0]
            else:
                return {
                    'total_payments': 0,
                    'total_amount': 0,
                    'wallet_creation_fees': 0,
                    'subscription_fees': 0,
                    'trade_fees': 0
                }
                
        except Exception as e:
            logger.error(f"Error getting payment statistics: {e}")
            return {}

    async def store_trading_wallet(self, wallet_data: Dict[str, Any]) -> bool:
        """Store user's trading wallet connection"""
        try:
            # Check if user already has a trading wallet
            existing_wallet = await self.get_user_trading_wallet(wallet_data['user_id'])
            if existing_wallet:
                # Update existing trading wallet
                result = await self.db.trading_wallets.update_one(
                    {'user_id': wallet_data['user_id']},
                    {'$set': wallet_data}
                )
            else:
                # Insert new trading wallet
                result = await self.db.trading_wallets.insert_one(wallet_data)
            
            return result.acknowledged
        except Exception as e:
            logger.error(f"Error storing trading wallet: {e}")
            return False

    async def get_user_trading_wallet(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user's connected trading wallet"""
        try:
            wallet = await self.db.trading_wallets.find_one({'user_id': user_id})
            return wallet
        except Exception as e:
            logger.error(f"Error getting user trading wallet: {e}")
            return None

    async def update_trading_wallet(self, user_id: int, wallet_data: Dict[str, Any]) -> bool:
        """Update user's trading wallet"""
        try:
            result = await self.db.trading_wallets.update_one(
                {'user_id': user_id},
                {'$set': wallet_data}
            )
            return result.acknowledged
        except Exception as e:
            logger.error(f"Error updating trading wallet: {e}")
            return False

    async def disconnect_trading_wallet(self, user_id: int) -> bool:
        """Disconnect user's trading wallet"""
        try:
            result = await self.db.trading_wallets.delete_one({'user_id': user_id})
            return result.acknowledged
        except Exception as e:
            logger.error(f"Error disconnecting trading wallet: {e}")
            return False

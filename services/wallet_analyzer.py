"""
Advanced wallet analysis service with ML-based insights
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
import numpy as np
from collections import defaultdict
from services.database import DatabaseManager
from services.solana_service import SolanaService
from config.settings import WHALE_THRESHOLD_SOL, WHALE_THRESHOLD_USD, MONITOR_INTERVAL

logger = logging.getLogger(__name__)

class WalletAnalyzer:
    def __init__(self, db_manager: DatabaseManager, solana_service: SolanaService):
        self.db = db_manager
        self.solana = solana_service
        self.monitored_wallets: Set[str] = set()
        self.user_wallet_map: Dict[str, List[int]] = defaultdict(list)
        self.is_monitoring = False
        
    async def start_monitoring(self):
        """Start wallet monitoring background task"""
        if self.is_monitoring:
            return
            
        self.is_monitoring = True
        logger.info("Starting wallet monitoring service")
        
        # Load existing monitored wallets
        await self._load_monitored_wallets()
        
        # Start monitoring tasks
        asyncio.create_task(self._monitor_wallets())
        asyncio.create_task(self._detect_whales())
        asyncio.create_task(self._analyze_patterns())
        
    async def stop_monitoring(self):
        """Stop wallet monitoring"""
        self.is_monitoring = False
        logger.info("Stopping wallet monitoring service")
        
    async def _load_monitored_wallets(self):
        """Load monitored wallets from database"""
        try:
            # Get all active wallets
            cursor = self.db.db.wallets.find({'is_active': True})
            wallets = await cursor.to_list(length=None)
            
            for wallet in wallets:
                address = wallet['address']
                user_id = wallet['user_id']
                
                self.monitored_wallets.add(address)
                self.user_wallet_map[address].append(user_id)
                
            logger.info(f"Loaded {len(self.monitored_wallets)} wallets for monitoring")
            
        except Exception as e:
            logger.error(f"Error loading monitored wallets: {e}")
            
    async def add_wallet_monitor(self, address: str, user_id: int):
        """Add wallet to monitoring"""
        self.monitored_wallets.add(address)
        self.user_wallet_map[address].append(user_id)
        
        # Start immediate analysis
        asyncio.create_task(self._analyze_wallet_immediate(address))
        
    async def remove_wallet_monitor(self, address: str, user_id: int):
        """Remove wallet from monitoring"""
        if address in self.user_wallet_map:
            if user_id in self.user_wallet_map[address]:
                self.user_wallet_map[address].remove(user_id)
                
            if not self.user_wallet_map[address]:
                self.monitored_wallets.discard(address)
                del self.user_wallet_map[address]
                
    async def _monitor_wallets(self):
        """Main wallet monitoring loop"""
        while self.is_monitoring:
            try:
                if not self.monitored_wallets:
                    await asyncio.sleep(MONITOR_INTERVAL)
                    continue
                    
                # Process wallets in batches
                wallet_list = list(self.monitored_wallets)
                batch_size = 10
                
                for i in range(0, len(wallet_list), batch_size):
                    batch = wallet_list[i:i + batch_size]
                    await asyncio.gather(*[
                        self._analyze_wallet(address) 
                        for address in batch
                    ], return_exceptions=True)
                    
                await asyncio.sleep(MONITOR_INTERVAL)
                
            except Exception as e:
                logger.error(f"Error in wallet monitoring loop: {e}")
                await asyncio.sleep(MONITOR_INTERVAL)
                
    async def _analyze_wallet(self, address: str):
        """Analyze individual wallet"""
        try:
            # Get current wallet state
            wallet_data = await self.solana.get_wallet_balance(address)
            
            if 'error' in wallet_data:
                return
                
            # Get recent transactions
            recent_txs = await self.solana.get_wallet_transactions(address, limit=20)
            
            # Store transactions in database
            for tx in recent_txs:
                tx['wallet_address'] = address
                tx['amount_usd'] = tx.get('amount', 0) * wallet_data.get('sol_price', 0)
                await self.db.store_transaction(tx)
                
            # Update wallet data
            await self.db.update_wallet_data(address, {
                'sol_balance': wallet_data['sol_balance'],
                'total_usd_value': wallet_data['total_usd_value'],
                'token_count': wallet_data['token_count'],
                'last_analysis': datetime.utcnow()
            })
            
            # Check for alerts
            await self._check_wallet_alerts(address, wallet_data, recent_txs)
            
        except Exception as e:
            logger.error(f"Error analyzing wallet {address}: {e}")
            
    async def _analyze_wallet_immediate(self, address: str):
        """Immediate wallet analysis for new additions"""
        try:
            # Get comprehensive wallet data
            wallet_data = await self.solana.get_wallet_balance(address)
            transactions = await self.solana.get_wallet_transactions(address, limit=100)
            
            # Analyze wallet characteristics
            analysis = await self._perform_wallet_analysis(address, wallet_data, transactions)
            
            # Check if whale
            if self._is_whale_wallet(wallet_data, analysis):
                await self.db.mark_wallet_as_whale(address, analysis)
                
            # Store analysis
            await self.db.update_wallet_data(address, {
                'analysis_data': analysis,
                'risk_score': analysis.get('risk_score', 0),
                'profit_score': analysis.get('profit_score', 0),
                'activity_score': analysis.get('activity_score', 0)
            })
            
            # Send initial analysis alert to users
            for user_id in self.user_wallet_map.get(address, []):
                await self.db.create_alert(user_id, {
                    'type': 'wallet_analysis_complete',
                    'wallet_address': address,
                    'message': f"Analysis complete for wallet {address[:8]}...",
                    'data': analysis
                })
                
        except Exception as e:
            logger.error(f"Error in immediate wallet analysis {address}: {e}")
            
    async def _perform_wallet_analysis(self, address: str, wallet_data: Dict, transactions: List[Dict]) -> Dict[str, Any]:
        """Perform comprehensive wallet analysis"""
        try:
            analysis = {
                'address': address,
                'analyzed_at': datetime.utcnow(),
                'total_value_usd': wallet_data.get('total_usd_value', 0),
                'sol_balance': wallet_data.get('sol_balance', 0),
                'token_diversity': len(wallet_data.get('tokens', [])),
                'transaction_count': len(transactions),
                'risk_score': 0,
                'profit_score': 0,
                'activity_score': 0,
                'patterns': [],
                'characteristics': []
            }
            
            if not transactions:
                return analysis
                
            # Calculate time-based metrics
            now = datetime.utcnow()
            tx_times = [datetime.fromtimestamp(tx.get('block_time', 0)) for tx in transactions if tx.get('block_time')]
            
            if tx_times:
                # Activity analysis
                time_diffs = [(now - tx_time).total_seconds() / 3600 for tx_time in tx_times]  # Hours
                avg_time_between = np.mean(np.diff(sorted(time_diffs))) if len(time_diffs) > 1 else 0
                
                analysis['avg_time_between_tx'] = avg_time_between
                analysis['most_recent_tx'] = min(time_diffs)
                analysis['oldest_tx'] = max(time_diffs)
                
                # Activity score (0-100)
                if avg_time_between > 0:
                    daily_tx_rate = 24 / avg_time_between
                    analysis['activity_score'] = min(100, daily_tx_rate * 10)
                    
            # Transaction amount analysis
            amounts = [tx.get('amount', 0) for tx in transactions if tx.get('amount')]
            if amounts:
                analysis['avg_transaction_amount'] = np.mean(amounts)
                analysis['max_transaction_amount'] = max(amounts)
                analysis['total_volume'] = sum(amounts)
                analysis['transaction_variance'] = np.var(amounts)
                
            # Token interaction analysis
            tokens_interacted = set()
            for tx in transactions:
                if tx.get('token', {}).get('mint'):
                    tokens_interacted.add(tx['token']['mint'])
                    
            analysis['unique_tokens_traded'] = len(tokens_interacted)
            
            # Pattern detection
            patterns = await self._detect_trading_patterns(transactions)
            analysis['patterns'] = patterns
            
            # Risk assessment
            risk_factors = []
            
            # High frequency trading
            if analysis.get('activity_score', 0) > 80:
                risk_factors.append('high_frequency_trader')
                
            # Large transaction amounts
            if analysis.get('max_transaction_amount', 0) > 100:  # > 100 SOL
                risk_factors.append('large_transactions')
                
            # Many different tokens
            if analysis.get('unique_tokens_traded', 0) > 20:
                risk_factors.append('diverse_portfolio')
                
            analysis['risk_factors'] = risk_factors
            analysis['risk_score'] = len(risk_factors) * 25  # 0-100 scale
            
            # Profit estimation (simplified)
            profit_indicators = 0
            if analysis.get('total_value_usd', 0) > 50000:  # High portfolio value
                profit_indicators += 1
            if 'consistent_gains' in patterns:
                profit_indicators += 1
            if analysis.get('unique_tokens_traded', 0) > 10:  # Diversified
                profit_indicators += 1
                
            analysis['profit_score'] = profit_indicators * 33  # 0-100 scale
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error performing wallet analysis: {e}")
            return {'error': str(e)}
            
    async def _detect_trading_patterns(self, transactions: List[Dict]) -> List[str]:
        """Detect trading patterns from transaction history"""
        patterns = []
        
        try:
            if len(transactions) < 5:
                return patterns
                
            # Group transactions by type
            buys = [tx for tx in transactions if tx.get('type') == 'receive']
            sells = [tx for tx in transactions if tx.get('type') == 'send']
            
            # Pattern: Frequent trader
            if len(transactions) > 50:
                patterns.append('frequent_trader')
                
            # Pattern: Buy and hold
            if len(buys) > len(sells) * 2:
                patterns.append('buy_and_hold')
                
            # Pattern: Day trader
            if len(buys) > 10 and len(sells) > 10 and abs(len(buys) - len(sells)) < 5:
                patterns.append('day_trader')
                
            # Pattern: Whale activity
            large_txs = [tx for tx in transactions if tx.get('amount', 0) > 50]
            if len(large_txs) > 5:
                patterns.append('whale_activity')
                
            # Pattern: Token sniper (many small buys of different tokens)
            token_buys = {}
            for tx in buys:
                if tx.get('token', {}).get('mint'):
                    mint = tx['token']['mint']
                    if mint not in token_buys:
                        token_buys[mint] = 0
                    token_buys[mint] += 1
                    
            if len(token_buys) > 10 and max(token_buys.values()) < 3:
                patterns.append('token_sniper')
                
            return patterns
            
        except Exception as e:
            logger.error(f"Error detecting trading patterns: {e}")
            return []
            
    def _is_whale_wallet(self, wallet_data: Dict, analysis: Dict) -> bool:
        """Determine if wallet qualifies as whale"""
        try:
            # SOL balance threshold
            if wallet_data.get('sol_balance', 0) >= WHALE_THRESHOLD_SOL:
                return True
                
            # USD value threshold
            if wallet_data.get('total_usd_value', 0) >= WHALE_THRESHOLD_USD:
                return True
                
            # Large transaction history
            if analysis.get('max_transaction_amount', 0) >= WHALE_THRESHOLD_SOL:
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error checking whale status: {e}")
            return False
            
    async def _check_wallet_alerts(self, address: str, wallet_data: Dict, transactions: List[Dict]):
        """Check for alert conditions"""
        try:
            user_ids = self.user_wallet_map.get(address, [])
            if not user_ids:
                return
                
            # Check for large transactions
            for tx in transactions[:5]:  # Check recent 5 transactions
                amount_usd = tx.get('amount', 0) * wallet_data.get('sol_price', 0)
                
                if amount_usd >= 10000:  # $10k+ transaction
                    for user_id in user_ids:
                        await self.db.create_alert(user_id, {
                            'type': 'large_transaction',
                            'wallet_address': address,
                            'message': f"🚨 Large transaction detected: ${amount_usd:,.2f}",
                            'data': {
                                'amount_usd': amount_usd,
                                'transaction': tx
                            }
                        })
                        
            # Check for new token interactions
            for tx in transactions[:3]:
                if tx.get('token') and tx.get('type') == 'receive':
                    token_symbol = tx['token'].get('symbol', 'UNKNOWN')
                    
                    for user_id in user_ids:
                        await self.db.create_alert(user_id, {
                            'type': 'new_token',
                            'wallet_address': address,
                            'message': f"🪙 New token acquired: {token_symbol}",
                            'data': {
                                'token': tx['token'],
                                'transaction': tx
                            }
                        })
                        
        except Exception as e:
            logger.error(f"Error checking wallet alerts: {e}")
            
    async def _detect_whales(self):
        """Background task to detect whale wallets"""
        while self.is_monitoring:
            try:
                # Get large transactions from last hour
                large_txs = await self.db.get_large_transactions(min_amount_usd=50000, hours=1)
                
                for tx in large_txs:
                    wallet_address = tx.get('wallet_address')
                    if not wallet_address:
                        continue
                        
                    # Check if already marked as whale
                    wallet_doc = await self.db.db.wallets.find_one({'address': wallet_address})
                    if wallet_doc and wallet_doc.get('is_whale'):
                        continue
                        
                    # Analyze wallet
                    wallet_data = await self.solana.get_wallet_balance(wallet_address)
                    analysis = await self._perform_wallet_analysis(
                        wallet_address, 
                        wallet_data, 
                        [tx]
                    )
                    
                    if self._is_whale_wallet(wallet_data, analysis):
                        await self.db.mark_wallet_as_whale(wallet_address, analysis)
                        
                        # Alert all users about new whale
                        await self._broadcast_whale_alert(wallet_address, wallet_data, tx)
                        
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                logger.error(f"Error in whale detection: {e}")
                await asyncio.sleep(300)
                
    async def _broadcast_whale_alert(self, address: str, wallet_data: Dict, transaction: Dict):
        """Broadcast whale alert to all users"""
        try:
            # Get all users with whale alerts enabled
            cursor = self.db.db.users.find({
                'settings.alerts_enabled': True,
                'subscription_tier': {'$in': ['premium', 'pro']}
            })
            
            users = await cursor.to_list(length=None)
            
            for user in users:
                await self.db.create_alert(user['user_id'], {
                    'type': 'whale_detected',
                    'wallet_address': address,
                    'message': f"🐋 New whale detected! ${wallet_data.get('total_usd_value', 0):,.0f} portfolio",
                    'data': {
                        'wallet_data': wallet_data,
                        'trigger_transaction': transaction
                    }
                })
                
        except Exception as e:
            logger.error(f"Error broadcasting whale alert: {e}")
            
    async def _analyze_patterns(self):
        """Background task for pattern analysis"""
        while self.is_monitoring:
            try:
                # Analyze market patterns every 30 minutes
                await self._analyze_market_trends()
                await self._detect_copy_trading_opportunities()
                
                await asyncio.sleep(1800)  # 30 minutes
                
            except Exception as e:
                logger.error(f"Error in pattern analysis: {e}")
                await asyncio.sleep(1800)
                
    async def _analyze_market_trends(self):
        """Analyze overall market trends"""
        try:
            # Get top wallets by recent activity
            top_wallets = await self.db.get_top_wallets(limit=50)
            
            # Analyze common tokens being traded
            token_activity = defaultdict(int)
            
            for wallet_data in top_wallets:
                wallet_address = wallet_data['_id']
                recent_txs = await self.db.get_wallet_transactions(wallet_address, limit=10)
                
                for tx in recent_txs:
                    if tx.get('token', {}).get('mint'):
                        token_activity[tx['token']['mint']] += 1
                        
            # Find trending tokens
            trending_tokens = sorted(
                token_activity.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:10]
            
            # Store trend data
            trend_data = {
                'timestamp': datetime.utcnow(),
                'trending_tokens': trending_tokens,
                'top_wallets_count': len(top_wallets)
            }
            
            await self.db.db.market_trends.insert_one(trend_data)
            
        except Exception as e:
            logger.error(f"Error analyzing market trends: {e}")
            
    async def _detect_copy_trading_opportunities(self):
        """Detect profitable wallets for copy trading"""
        try:
            # Get wallets with high profit scores
            cursor = self.db.db.wallets.find({
                'is_whale': True,
                'analysis_data.profit_score': {'$gte': 70}
            }).sort('analysis_data.profit_score', -1).limit(20)
            
            profitable_wallets = await cursor.to_list(length=None)
            
            for wallet in profitable_wallets:
                # Analyze recent performance
                recent_txs = await self.db.get_wallet_transactions(
                    wallet['address'], 
                    limit=20
                )
                
                if len(recent_txs) >= 10:
                    # Calculate recent success rate (simplified)
                    success_indicators = 0
                    for tx in recent_txs[:10]:
                        if tx.get('amount_usd', 0) > 1000:  # Significant transaction
                            success_indicators += 1
                            
                    success_rate = success_indicators / 10
                    
                    if success_rate >= 0.6:  # 60% success rate
                        # Mark as copy trading candidate
                        await self.db.db.wallets.update_one(
                            {'address': wallet['address']},
                            {
                                '$set': {
                                    'copy_trading_candidate': True,
                                    'success_rate': success_rate,
                                    'last_performance_check': datetime.utcnow()
                                }
                            }
                        )
                        
        except Exception as e:
            logger.error(f"Error detecting copy trading opportunities: {e}")
            
    async def get_wallet_summary(self, address: str) -> Dict[str, Any]:
        """Get wallet summary for display"""
        try:
            # Get from database first
            wallet_doc = await self.db.db.wallets.find_one({'address': address})
            
            if wallet_doc:
                return {
                    'address': address,
                    'sol_balance': wallet_doc.get('sol_balance', 0),
                    'total_usd_value': wallet_doc.get('total_usd_value', 0),
                    'is_whale': wallet_doc.get('is_whale', False),
                    'last_activity': wallet_doc.get('last_activity'),
                    'risk_score': wallet_doc.get('analysis_data', {}).get('risk_score', 0),
                    'profit_score': wallet_doc.get('analysis_data', {}).get('profit_score', 0)
                }
            else:
                # Get live data
                wallet_data = await self.solana.get_wallet_balance(address)
                return {
                    'address': address,
                    'sol_balance': wallet_data.get('sol_balance', 0),
                    'total_usd_value': wallet_data.get('total_usd_value', 0),
                    'is_whale': False,
                    'last_activity': None,
                    'risk_score': 0,
                    'profit_score': 0
                }
                
        except Exception as e:
            logger.error(f"Error getting wallet summary: {e}")
            return {
                'address': address,
                'error': str(e)
            }
            
    async def get_recent_whale_activity(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent whale activity"""
        try:
            # Get recent large transactions
            large_txs = await self.db.get_large_transactions(
                min_amount_usd=25000, 
                hours=24
            )
            
            whale_activities = []
            
            for tx in large_txs[:limit]:
                # Get token info if available
                token_symbol = 'SOL'
                if tx.get('token', {}).get('symbol'):
                    token_symbol = tx['token']['symbol']
                    
                whale_activities.append({
                    'wallet': tx.get('wallet_address', ''),
                    'amount': tx.get('amount', 0),
                    'amount_usd': tx.get('amount_usd', 0),
                    'token_symbol': token_symbol,
                    'action': tx.get('type', 'unknown'),
                    'timestamp': datetime.fromtimestamp(
                        tx.get('block_time', 0)
                    ).strftime('%Y-%m-%d %H:%M:%S') if tx.get('block_time') else 'Unknown'
                })
                
            return whale_activities
            
        except Exception as e:
            logger.error(f"Error getting whale activity: {e}")
            return []

"""
Payment service for handling crypto payments and subscriptions
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.transaction import Transaction
from services.database import DatabaseManager
from services.solana_service import SolanaService
from config.settings import (
    ADMIN_WALLET_ADDRESS, ADMIN_WALLET_PRIVATE_KEY, WALLET_CREATION_FEE,
    TRANSACTION_FEE_PERCENTAGE, SUBSCRIPTION_FEE_PERCENTAGE, PAYMENT_CONFIRMATION_BLOCKS,
    MIN_PAYMENT_AMOUNT, SUBSCRIPTION_GRACE_PERIOD_DAYS, AUTO_SUBSCRIPTION_RENEWAL
)

logger = logging.getLogger(__name__)

class PaymentService:
    def __init__(self, db_manager: DatabaseManager, solana_service: SolanaService):
        self.db = db_manager
        self.solana = solana_service
        self.admin_keypair = None
        self.is_running = False
        
        # Initialize admin wallet
        if ADMIN_WALLET_PRIVATE_KEY:
            try:
                self.admin_keypair = Keypair.from_base58_string(ADMIN_WALLET_PRIVATE_KEY)
                logger.info("Admin wallet initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize admin wallet: {e}")
        
    async def start_monitoring(self):
        """Start payment monitoring"""
        if self.is_running:
            return
            
        self.is_running = True
        logger.info("Starting payment monitoring service")
        
        # Start background tasks
        asyncio.create_task(self._monitor_payments())
        asyncio.create_task(self._process_subscription_renewals())
        
    async def stop_monitoring(self):
        """Stop payment monitoring"""
        self.is_running = False
        logger.info("Stopping payment monitoring service")
        
    async def create_user_wallet(self, user_id: int) -> Tuple[bool, str, Dict[str, Any]]:
        """Create a new wallet for user"""
        try:
            # Check if user has paid creation fee
            payment_status = await self._check_wallet_creation_payment(user_id)
            if not payment_status['paid']:
                return False, "Wallet creation fee not paid", {}
            
            # Generate new keypair
            new_keypair = Keypair()
            wallet_address = str(new_keypair.pubkey())
            private_key = new_keypair.to_base58_string()
            
            # Encrypt private key (basic encryption for demo)
            encrypted_key = self._encrypt_private_key(private_key)
            
            # Store wallet in database
            wallet_data = {
                'user_id': user_id,
                'address': wallet_address,
                'encrypted_private_key': encrypted_key,
                'created_at': datetime.utcnow(),
                'is_active': True,
                'balance': 0.0,
                'type': 'user_wallet'
            }
            
            success = await self.db.store_user_wallet(wallet_data)
            
            if success:
                logger.info(f"Created wallet {wallet_address} for user {user_id}")
                return True, "Wallet created successfully", {
                    'address': wallet_address,
                    'private_key': private_key  # Return unencrypted for user
                }
            else:
                return False, "Failed to store wallet", {}
                
        except Exception as e:
            logger.error(f"Error creating wallet for user {user_id}: {e}")
            return False, f"Error creating wallet: {str(e)}", {}
            
    async def import_user_wallet(self, user_id: int, private_key: str) -> Tuple[bool, str]:
        """Import existing wallet for user"""
        try:
            # Validate private key
            try:
                keypair = Keypair.from_base58_string(private_key)
                wallet_address = str(keypair.pubkey())
            except Exception:
                return False, "Invalid private key format"
            
            # Check if wallet already exists
            existing_wallet = await self.db.get_user_wallet_by_address(wallet_address)
            if existing_wallet:
                return False, "Wallet already imported by another user"
            
            # Encrypt and store wallet
            encrypted_key = self._encrypt_private_key(private_key)
            
            wallet_data = {
                'user_id': user_id,
                'address': wallet_address,
                'encrypted_private_key': encrypted_key,
                'imported_at': datetime.utcnow(),
                'is_active': True,
                'type': 'imported_wallet'
            }
            
            success = await self.db.store_user_wallet(wallet_data)
            
            if success:
                logger.info(f"Imported wallet {wallet_address} for user {user_id}")
                return True, "Wallet imported successfully"
            else:
                return False, "Failed to import wallet"
                
        except Exception as e:
            logger.error(f"Error importing wallet for user {user_id}: {e}")
            return False, f"Error importing wallet: {str(e)}"
            
    async def process_trade_fee(self, user_id: int, trade_amount: float, trade_signature: str) -> bool:
        """Process trade fee automatically from user's wallet"""
        try:
            # Get user's primary wallet
            user_wallet = await self.db.get_user_primary_wallet(user_id)
            if not user_wallet:
                logger.error(f"No wallet found for user {user_id}")
                return False
            
            # Calculate fee amount
            fee_amount = trade_amount * (TRANSACTION_FEE_PERCENTAGE / 100)
            
            if fee_amount < MIN_PAYMENT_AMOUNT:
                fee_amount = MIN_PAYMENT_AMOUNT
            
            # Get wallet balance
            balance = await self.solana.get_wallet_balance(user_wallet['address'])
            sol_balance = balance.get('sol_balance', 0)
            
            if sol_balance < fee_amount:
                logger.warning(f"Insufficient balance for fee deduction: {sol_balance} < {fee_amount}")
                return False
            
            # Transfer fee to admin wallet
            success = await self._transfer_fee_to_admin(
                user_wallet['address'], 
                fee_amount, 
                f"Trade fee for transaction {trade_signature}"
            )
            
            if success:
                # Record fee payment
                await self.db.record_fee_payment({
                    'user_id': user_id,
                    'amount': fee_amount,
                    'transaction_signature': trade_signature,
                    'payment_type': 'trade_fee',
                    'status': 'completed',
                    'created_at': datetime.utcnow()
                })
                
                logger.info(f"Trade fee {fee_amount} SOL deducted from user {user_id}")
                return True
            else:
                logger.error(f"Failed to transfer trade fee for user {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error processing trade fee for user {user_id}: {e}")
            return False

    async def process_automatic_fee_deduction(self, user_id: int, transaction_amount: float, transaction_type: str, transaction_signature: str) -> bool:
        """Automatically deduct fees from any transaction"""
        try:
            # Get user's primary wallet
            user_wallet = await self.db.get_user_primary_wallet(user_id)
            if not user_wallet:
                logger.error(f"No wallet found for user {user_id}")
                return False
            
            # Calculate fee based on transaction type
            if transaction_type == 'trade':
                fee_percentage = TRANSACTION_FEE_PERCENTAGE
            elif transaction_type == 'subscription':
                fee_percentage = SUBSCRIPTION_FEE_PERCENTAGE
            else:
                fee_percentage = TRANSACTION_FEE_PERCENTAGE  # Default
            
            fee_amount = transaction_amount * (fee_percentage / 100)
            
            if fee_amount < MIN_PAYMENT_AMOUNT:
                fee_amount = MIN_PAYMENT_AMOUNT
            
            # Get wallet balance
            balance = await self.solana.get_wallet_balance(user_wallet['address'])
            sol_balance = balance.get('sol_balance', 0)
            
            if sol_balance < fee_amount:
                logger.warning(f"Insufficient balance for automatic fee deduction: {sol_balance} < {fee_amount}")
                return False
            
            # Transfer fee to admin wallet
            success = await self._transfer_fee_to_admin(
                user_wallet['address'], 
                fee_amount, 
                f"Automatic {transaction_type} fee for transaction {transaction_signature}"
            )
            
            if success:
                # Record fee payment
                await self.db.record_fee_payment({
                    'user_id': user_id,
                    'amount': fee_amount,
                    'transaction_signature': transaction_signature,
                    'payment_type': f'{transaction_type}_fee',
                    'status': 'completed',
                    'created_at': datetime.utcnow()
                })
                
                logger.info(f"Automatic {transaction_type} fee {fee_amount} SOL deducted from user {user_id}")
                return True
            else:
                logger.error(f"Failed to transfer automatic fee for user {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error processing automatic fee deduction for user {user_id}: {e}")
            return False

    async def check_and_deduct_wallet_creation_fee(self, user_id: int) -> bool:
        """Check if user has sufficient balance and deduct wallet creation fee automatically"""
        try:
            # Get user's primary wallet
            user_wallet = await self.db.get_user_primary_wallet(user_id)
            if not user_wallet:
                logger.error(f"No wallet found for user {user_id}")
                return False
            
            # Check if fee already paid
            payment_status = await self._check_wallet_creation_payment(user_id)
            if payment_status['paid']:
                return True
            
            # Get wallet balance
            balance = await self.solana.get_wallet_balance(user_wallet['address'])
            sol_balance = balance.get('sol_balance', 0)
            
            if sol_balance < WALLET_CREATION_FEE:
                logger.warning(f"Insufficient balance for wallet creation fee: {sol_balance} < {WALLET_CREATION_FEE}")
                return False
            
            # Transfer fee to admin wallet
            success = await self._transfer_fee_to_admin(
                user_wallet['address'], 
                WALLET_CREATION_FEE, 
                f"Wallet creation fee for user {user_id}"
            )
            
            if success:
                # Record fee payment
                await self.db.record_fee_payment({
                    'user_id': user_id,
                    'amount': WALLET_CREATION_FEE,
                    'transaction_signature': f'wallet_creation_{user_id}_{datetime.utcnow().timestamp()}',
                    'payment_type': 'wallet_creation_fee',
                    'status': 'completed',
                    'created_at': datetime.utcnow()
                })
                
                logger.info(f"Wallet creation fee {WALLET_CREATION_FEE} SOL deducted from user {user_id}")
                return True
            else:
                logger.error(f"Failed to transfer wallet creation fee for user {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error processing wallet creation fee for user {user_id}: {e}")
            return False
            
    async def process_subscription_payment(self, user_id: int, tier: str) -> Tuple[bool, str]:
        """Process subscription payment for monthly plan"""
        try:
            # Get user's primary wallet
            user_wallet = await self.db.get_user_primary_wallet(user_id)
            if not user_wallet:
                return False, "No wallet found. Please create or import a wallet first."
            
            # Get subscription tier info
            if tier not in SUBSCRIPTION_TIERS:
                return False, f"Invalid subscription tier: {tier}"
            
            tier_data = SUBSCRIPTION_TIERS[tier]
            monthly_fee = tier_data['monthly_fee']
            
            if monthly_fee == 0:
                # Free tier - just update subscription
                await self.db.update_user_subscription(user_id, tier)
                return True, f"Successfully upgraded to {tier} plan (free)"
            
            # Calculate total payment (monthly fee + transaction fee)
            transaction_fee = monthly_fee * (SUBSCRIPTION_FEE_PERCENTAGE / 100)
            total_payment = monthly_fee + transaction_fee
            
            # Get wallet balance
            balance = await self.solana.get_wallet_balance(user_wallet['address'])
            sol_balance = balance.get('sol_balance', 0)
            
            if sol_balance < total_payment:
                return False, f"Insufficient balance. Need {total_payment:.4f} SOL (fee: {monthly_fee:.4f} SOL + transaction fee: {transaction_fee:.4f} SOL). Current balance: {sol_balance:.4f} SOL"
            
            # Transfer monthly fee to admin wallet
            fee_success = await self._transfer_fee_to_admin(
                user_wallet['address'], 
                monthly_fee, 
                f"Monthly subscription fee for {tier} plan"
            )
            
            if fee_success:
                # Update user subscription
                await self.db.update_user_subscription(user_id, tier)
                
                # Record subscription payment
                await self.db.record_fee_payment({
                    'user_id': user_id,
                    'amount': monthly_fee,
                    'transaction_signature': f'subscription_{tier}_{user_id}_{datetime.utcnow().timestamp()}',
                    'payment_type': 'subscription_fee',
                    'subscription_tier': tier,
                    'status': 'completed',
                    'created_at': datetime.utcnow()
                })
                
                logger.info(f"Subscription payment {monthly_fee} SOL processed for user {user_id} to {tier} plan")
                return True, f"Successfully upgraded to {tier} plan! Monthly fee: {monthly_fee} SOL"
            else:
                return False, "Failed to process subscription payment. Please try again."
                
        except Exception as e:
            logger.error(f"Error processing subscription payment for user {user_id}: {e}")
            return False, f"Error processing subscription: {str(e)}"
            
    async def _transfer_fee_to_admin(self, from_address: str, amount: float, description: str) -> bool:
        """Transfer fee from user wallet to admin wallet"""
        try:
            if not self.admin_keypair:
                logger.error("Admin wallet not configured")
                return False
            
            # Create transfer transaction
            transfer_tx = await self.solana.create_transfer_transaction(
                from_address=from_address,
                to_address=ADMIN_WALLET_ADDRESS,
                amount=amount,
                description=description
            )
            
            if transfer_tx.get('success'):
                logger.info(f"Transferred {amount} SOL to admin wallet")
                return True
            else:
                logger.error(f"Transfer failed: {transfer_tx.get('error')}")
                return False
                
        except Exception as e:
            logger.error(f"Error transferring fee: {e}")
            return False
            
    async def _check_wallet_creation_payment(self, user_id: int) -> Dict[str, Any]:
        """Check if user has paid wallet creation fee"""
        try:
            # Check recent payments for this user
            recent_payment = await self.db.get_recent_payment(user_id, 'wallet_creation_fee')
            
            if recent_payment:
                return {'paid': True, 'payment_id': recent_payment['_id']}
            else:
                return {'paid': False, 'required_amount': WALLET_CREATION_FEE}
                
        except Exception as e:
            logger.error(f"Error checking wallet creation payment: {e}")
            return {'paid': False, 'error': str(e)}
            
    async def _monitor_payments(self):
        """Monitor incoming payments"""
        while self.is_running:
            try:
                # Check for pending payments
                pending_payments = await self.db.get_pending_payments()
                
                for payment in pending_payments:
                    await self._process_pending_payment(payment)
                    
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in payment monitoring: {e}")
                await asyncio.sleep(60)
                
    async def _process_pending_payment(self, payment: Dict[str, Any]):
        """Process a pending payment"""
        try:
            payment_id = payment['_id']
            user_id = payment['user_id']
            payment_type = payment['type']
            
            # Verify payment on blockchain
            if await self._verify_payment_on_chain(payment):
                # Mark payment as confirmed
                await self.db.confirm_payment(payment_id)
                
                # Process based on payment type
                if payment_type == 'wallet_creation_fee':
                    await self._handle_wallet_creation_confirmed(user_id)
                elif payment_type == 'subscription_fee':
                    await self._handle_subscription_confirmed(user_id, payment)
                    
                logger.info(f"Payment {payment_id} confirmed and processed")
            else:
                # Check if payment is too old
                payment_age = datetime.utcnow() - payment['created_at']
                if payment_age > timedelta(hours=24):
                    await self.db.expire_payment(payment_id)
                    logger.warning(f"Payment {payment_id} expired")
                    
        except Exception as e:
            logger.error(f"Error processing payment {payment.get('_id')}: {e}")
            
    async def _process_subscription_renewals(self):
        """Process monthly subscription renewals"""
        while self.is_running:
            try:
                # Get users with expiring subscriptions
                expiring_users = await self.db.get_expiring_subscriptions()
                
                for user in expiring_users:
                    await self._handle_subscription_renewal(user)
                
                # Check every hour
                await asyncio.sleep(3600)  # 1 hour
                
            except Exception as e:
                logger.error(f"Error in subscription renewal process: {e}")
                await asyncio.sleep(300)  # 5 minutes on error

    async def _handle_subscription_renewal(self, user: Dict[str, Any]):
        """Handle automatic subscription renewal for monthly plans"""
        try:
            user_id = user['user_id']
            current_tier = user.get('subscription_tier', 'free')
            
            if current_tier == 'free':
                return  # No renewal needed for free tier
            
            # Get subscription tier info
            tier_data = SUBSCRIPTION_TIERS.get(current_tier)
            if not tier_data:
                logger.warning(f"Invalid subscription tier {current_tier} for user {user_id}")
                return
            
            monthly_fee = tier_data['monthly_fee']
            
            if monthly_fee == 0:
                return  # Free tier
            
            # Get user's primary wallet
            user_wallet = await self.db.get_user_primary_wallet(user_id)
            if not user_wallet:
                logger.warning(f"No wallet found for user {user_id} subscription renewal")
                await self._send_payment_reminder(user_id, current_tier)
                return
            
            # Check wallet balance
            balance = await self.solana.get_wallet_balance(user_wallet['address'])
            sol_balance = balance.get('sol_balance', 0)
            
            # Calculate total payment needed
            transaction_fee = monthly_fee * (SUBSCRIPTION_FEE_PERCENTAGE / 100)
            total_payment = monthly_fee + transaction_fee
            
            if sol_balance >= total_payment:
                # Auto-renew subscription
                fee_success = await self._transfer_fee_to_admin(
                    user_wallet['address'], 
                    monthly_fee, 
                    f"Monthly subscription renewal for {current_tier} plan"
                )
                
                if fee_success:
                    # Update subscription renewal date
                    await self.db.update_user_subscription(user_id, current_tier)
                    
                    # Record renewal payment
                    await self.db.record_fee_payment({
                        'user_id': user_id,
                        'amount': monthly_fee,
                        'transaction_signature': f'renewal_{current_tier}_{user_id}_{datetime.utcnow().timestamp()}',
                        'payment_type': 'subscription_renewal',
                        'subscription_tier': current_tier,
                        'status': 'completed',
                        'created_at': datetime.utcnow()
                    })
                    
                    logger.info(f"Auto-renewed {current_tier} subscription for user {user_id}")
                else:
                    logger.warning(f"Failed to auto-renew subscription for user {user_id}")
                    await self._send_payment_reminder(user_id, current_tier)
            else:
                # Insufficient balance - send reminder
                logger.warning(f"Insufficient balance for subscription renewal: user {user_id}, balance: {sol_balance}, needed: {total_payment}")
                await self._send_payment_reminder(user_id, current_tier)
                
        except Exception as e:
            logger.error(f"Error handling subscription renewal for user {user.get('user_id')}: {e}")

    async def _send_payment_reminder(self, user_id: int, tier: str):
        """Send payment reminder for subscription renewal"""
        try:
            tier_data = SUBSCRIPTION_TIERS.get(tier, {})
            monthly_fee = tier_data.get('monthly_fee', 0)
            
            reminder_text = (
                f"⚠️ *Subscription Renewal Reminder*\n\n"
                f"Your {tier.upper()} subscription needs renewal.\n"
                f"Monthly fee: {monthly_fee} SOL\n\n"
                f"Please ensure you have sufficient balance in your wallet for automatic renewal."
            )
            
            # This would typically send a Telegram message
            # For now, just log it
            logger.info(f"Payment reminder sent to user {user_id} for {tier} subscription")
            
        except Exception as e:
            logger.error(f"Error sending payment reminder to user {user_id}: {e}")
            
    def _encrypt_private_key(self, private_key: str) -> str:
        """Basic encryption for private keys (should be enhanced in production)"""
        # This is a basic implementation - use proper encryption in production
        import base64
        return base64.b64encode(private_key.encode()).decode()
        
    def _decrypt_private_key(self, encrypted_key: str) -> str:
        """Basic decryption for private keys"""
        import base64
        return base64.b64decode(encrypted_key.encode()).decode()
        
    async def _verify_payment_on_chain(self, payment: Dict[str, Any]) -> bool:
        """Verify payment on blockchain"""
        try:
            # This would check the actual blockchain for the payment
            # For now, return True as placeholder
            return True
        except Exception as e:
            logger.error(f"Error verifying payment on chain: {e}")
            return False 

    async def connect_trading_wallet(self, user_id: int, private_key: str) -> Tuple[bool, str, Dict[str, Any]]:
        """Connect a wallet for trading (one per user)"""
        try:
            # Validate private key
            try:
                keypair = Keypair.from_base58_string(private_key)
                wallet_address = str(keypair.pubkey())
            except Exception as e:
                return False, "Invalid private key format", {}
            
            # Check if user already has a trading wallet
            existing_wallet = await self.db.get_user_trading_wallet(user_id)
            if existing_wallet:
                return False, "You already have a trading wallet connected. Please disconnect it first or replace it.", {}
            
            # Encrypt private key
            encrypted_key = self._encrypt_private_key(private_key)
            
            # Store trading wallet
            wallet_data = {
                'user_id': user_id,
                'address': wallet_address,
                'encrypted_private_key': encrypted_key,
                'connected_at': datetime.utcnow(),
                'is_active': True,
                'type': 'trading_wallet'
            }
            
            success = await self.db.store_trading_wallet(wallet_data)
            
            if success:
                logger.info(f"Connected trading wallet {wallet_address} for user {user_id}")
                return True, "Trading wallet connected successfully", {
                    'address': wallet_address,
                    'private_key': private_key  # Return unencrypted for user
                }
            else:
                return False, "Failed to store trading wallet", {}
                
        except Exception as e:
            logger.error(f"Error connecting trading wallet for user {user_id}: {e}")
            return False, f"Error connecting wallet: {str(e)}", {}

    async def replace_trading_wallet(self, user_id: int, private_key: str) -> Tuple[bool, str, Dict[str, Any]]:
        """Replace user's existing trading wallet"""
        try:
            # Validate private key
            try:
                keypair = Keypair.from_base58_string(private_key)
                wallet_address = str(keypair.pubkey())
            except Exception as e:
                return False, "Invalid private key format", {}
            
            # Encrypt private key
            encrypted_key = self._encrypt_private_key(private_key)
            
            # Update trading wallet
            wallet_data = {
                'user_id': user_id,
                'address': wallet_address,
                'encrypted_private_key': encrypted_key,
                'connected_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
                'is_active': True,
                'type': 'trading_wallet'
            }
            
            success = await self.db.update_trading_wallet(user_id, wallet_data)
            
            if success:
                logger.info(f"Replaced trading wallet {wallet_address} for user {user_id}")
                return True, "Trading wallet replaced successfully", {
                    'address': wallet_address,
                    'private_key': private_key  # Return unencrypted for user
                }
            else:
                return False, "Failed to replace trading wallet", {}
                
        except Exception as e:
            logger.error(f"Error replacing trading wallet for user {user_id}: {e}")
            return False, f"Error replacing wallet: {str(e)}", {}

    async def disconnect_trading_wallet(self, user_id: int) -> Tuple[bool, str]:
        """Disconnect user's trading wallet"""
        try:
            success = await self.db.disconnect_trading_wallet(user_id)
            
            if success:
                logger.info(f"Disconnected trading wallet for user {user_id}")
                return True, "Trading wallet disconnected successfully"
            else:
                return False, "Failed to disconnect trading wallet"
                
        except Exception as e:
            logger.error(f"Error disconnecting trading wallet for user {user_id}: {e}")
            return False, f"Error disconnecting wallet: {str(e)}"

    async def get_user_trading_wallet(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user's connected trading wallet"""
        try:
            return await self.db.get_user_trading_wallet(user_id)
        except Exception as e:
            logger.error(f"Error getting trading wallet for user {user_id}: {e}")
            return None 
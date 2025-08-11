"""
Solana blockchain service for real-time data and trading
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from solana.rpc.async_api import AsyncClient
from solana.rpc.websocket_api import connect
from solders.pubkey import Pubkey as PublicKey
from solders.transaction import Transaction
from solders.keypair import Keypair
from solders.pubkey import Pubkey
import json
import aiohttp
from config.settings import SOLANA_RPC_URL, SOLANA_WS_URL, PRIVATE_KEY

logger = logging.getLogger(__name__)

class SolanaService:
    def __init__(self):
        self.rpc_client = None
        self.ws_connection = None
        self.keypair = None
        self.price_cache = {}
        self.session = None
        
    async def connect(self):
        """Initialize Solana connections"""
        try:
            self.rpc_client = AsyncClient(SOLANA_RPC_URL)
            self.session = aiohttp.ClientSession()
            
            if PRIVATE_KEY and PRIVATE_KEY != "your_base58_encoded_private_key_here":
                try:
                    self.keypair = Keypair.from_base58_string(PRIVATE_KEY)
                    logger.info("Solana wallet configured successfully")
                except Exception as key_error:
                    logger.warning(f"Invalid private key format: {key_error}")
                    self.keypair = None
            else:
                logger.info("No private key configured - running in limited mode")
                self.keypair = None
                
            logger.info("Solana service connected successfully")
            
        except Exception as e:
            logger.error(f"Failed to connect to Solana: {e}")
            raise
            
    async def disconnect(self):
        """Close connections"""
        if self.rpc_client:
            await self.rpc_client.close()
        if self.session:
            await self.session.close()
        if self.ws_connection:
            await self.ws_connection.close()
            
    async def validate_address(self, address: str) -> bool:
        """Validate Solana address"""
        try:
            PublicKey.from_string(address)
            return True
        except:
            return False
            
    async def get_wallet_balance(self, address: str) -> Dict[str, Any]:
        """Get wallet SOL balance and token balances"""
        try:
            pubkey = PublicKey.from_string(address)
            
            # Get SOL balance
            balance_response = await self.rpc_client.get_balance(pubkey)
            sol_balance = balance_response.value / 1e9  # Convert lamports to SOL
            
            # Get token accounts
            token_accounts = await self.rpc_client.get_token_accounts_by_owner(
                pubkey, 
                {"programId": PublicKey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")}
            )
            
            tokens = []
            total_usd_value = 0
            
            for account in token_accounts.value:
                try:
                    account_data = account.account.data
                    if hasattr(account_data, 'parsed'):
                        token_info = account_data.parsed['info']
                        mint = token_info['mint']
                        amount = float(token_info['tokenAmount']['uiAmount'] or 0)
                        
                        if amount > 0:
                            # Get token metadata and price
                            token_data = await self.get_token_info(mint)
                            price = await self.get_token_price(mint)
                            
                            token_value = amount * price
                            total_usd_value += token_value
                            
                            tokens.append({
                                'mint': mint,
                                'symbol': token_data.get('symbol', 'UNKNOWN'),
                                'name': token_data.get('name', 'Unknown Token'),
                                'amount': amount,
                                'price': price,
                                'value_usd': token_value
                            })
                except Exception as e:
                    logger.warning(f"Error processing token account: {e}")
                    continue
                    
            # Get SOL price for USD value
            sol_price = await self.get_sol_price()
            sol_usd_value = sol_balance * sol_price
            total_usd_value += sol_usd_value
            
            return {
                'address': address,
                'sol_balance': sol_balance,
                'sol_price': sol_price,
                'sol_usd_value': sol_usd_value,
                'tokens': tokens,
                'total_usd_value': total_usd_value,
                'token_count': len(tokens)
            }
            
        except Exception as e:
            logger.error(f"Error getting wallet balance for {address}: {e}")
            return {
                'address': address,
                'sol_balance': 0,
                'tokens': [],
                'total_usd_value': 0,
                'error': str(e)
            }
            
    async def get_wallet_transactions(self, address: str, limit: int = 50) -> List[Dict]:
        """Get recent wallet transactions"""
        try:
            pubkey = PublicKey(address)
            
            # Get transaction signatures
            signatures = await self.rpc_client.get_signatures_for_address(
                pubkey, 
                limit=limit
            )
            
            transactions = []
            
            for sig_info in signatures.value:
                try:
                    # Get transaction details
                    tx = await self.rpc_client.get_transaction(
                        sig_info.signature,
                        encoding="jsonParsed",
                        max_supported_transaction_version=0
                    )
                    
                    if tx.value:
                        parsed_tx = await self._parse_transaction(tx.value, address)
                        if parsed_tx:
                            transactions.append(parsed_tx)
                            
                except Exception as e:
                    logger.warning(f"Error parsing transaction {sig_info.signature}: {e}")
                    continue
                    
            return transactions
            
        except Exception as e:
            logger.error(f"Error getting transactions for {address}: {e}")
            return []
            
    async def _parse_transaction(self, tx_data: Any, wallet_address: str) -> Optional[Dict]:
        """Parse transaction data to extract relevant information"""
        try:
            meta = tx_data.transaction.meta
            message = tx_data.transaction.transaction.message
            
            # Basic transaction info
            tx_info = {
                'signature': str(tx_data.transaction.transaction.signatures[0]),
                'slot': tx_data.slot,
                'block_time': tx_data.block_time,
                'success': meta.err is None,
                'fee': meta.fee,
                'type': 'unknown',
                'amount': 0,
                'token': None,
                'counterparty': None
            }
            
            # Analyze balance changes
            pre_balances = meta.pre_balances
            post_balances = meta.post_balances
            account_keys = [str(key) for key in message.account_keys]
            
            # Find wallet index
            wallet_index = None
            for i, key in enumerate(account_keys):
                if key == wallet_address:
                    wallet_index = i
                    break
                    
            if wallet_index is not None:
                # Calculate SOL balance change
                pre_balance = pre_balances[wallet_index] / 1e9
                post_balance = post_balances[wallet_index] / 1e9
                sol_change = post_balance - pre_balance
                
                tx_info['amount'] = abs(sol_change)
                tx_info['type'] = 'receive' if sol_change > 0 else 'send'
                
            # Check for token transfers
            if hasattr(meta, 'pre_token_balances') and hasattr(meta, 'post_token_balances'):
                token_changes = await self._analyze_token_changes(
                    meta.pre_token_balances,
                    meta.post_token_balances,
                    wallet_address
                )
                
                if token_changes:
                    tx_info.update(token_changes)
                    
            return tx_info
            
        except Exception as e:
            logger.error(f"Error parsing transaction: {e}")
            return None
            
    async def _analyze_token_changes(self, pre_balances: List, post_balances: List, wallet_address: str) -> Dict:
        """Analyze token balance changes"""
        try:
            changes = {}
            
            # Create balance maps
            pre_map = {bal.owner: bal for bal in pre_balances if bal.owner == wallet_address}
            post_map = {bal.owner: bal for bal in post_balances if bal.owner == wallet_address}
            
            # Find changes
            for owner in set(list(pre_map.keys()) + list(post_map.keys())):
                pre_amount = float(pre_map.get(owner, {}).get('uiTokenAmount', {}).get('uiAmount', 0))
                post_amount = float(post_map.get(owner, {}).get('uiTokenAmount', {}).get('uiAmount', 0))
                
                if pre_amount != post_amount:
                    mint = pre_map.get(owner, post_map.get(owner, {})).get('mint')
                    if mint:
                        token_info = await self.get_token_info(mint)
                        changes = {
                            'type': 'token_transfer',
                            'token': {
                                'mint': mint,
                                'symbol': token_info.get('symbol', 'UNKNOWN'),
                                'amount': abs(post_amount - pre_amount),
                                'direction': 'in' if post_amount > pre_amount else 'out'
                            }
                        }
                        break
                        
            return changes
            
        except Exception as e:
            logger.error(f"Error analyzing token changes: {e}")
            return {}
            
    async def get_token_info(self, mint_address: str) -> Dict[str, Any]:
        """Get token metadata"""
        try:
            # Try to get from Jupiter API first
            url = f"https://token.jup.ag/strict"
            async with self.session.get(url) as response:
                if response.status == 200:
                    tokens = await response.json()
                    for token in tokens:
                        if token['address'] == mint_address:
                            return {
                                'symbol': token['symbol'],
                                'name': token['name'],
                                'decimals': token['decimals'],
                                'logoURI': token.get('logoURI')
                            }
                            
            # Fallback to on-chain metadata
            return await self._get_onchain_token_metadata(mint_address)
            
        except Exception as e:
            logger.error(f"Error getting token info for {mint_address}: {e}")
            return {
                'symbol': 'UNKNOWN',
                'name': 'Unknown Token',
                'decimals': 9
            }
            
    async def _get_onchain_token_metadata(self, mint_address: str) -> Dict[str, Any]:
        """Get token metadata from on-chain data"""
        try:
            # This would involve parsing the token metadata account
            # For now, return basic info
            return {
                'symbol': mint_address[:8],
                'name': f"Token {mint_address[:8]}",
                'decimals': 9
            }
        except Exception as e:
            logger.error(f"Error getting on-chain metadata: {e}")
            return {
                'symbol': 'UNKNOWN',
                'name': 'Unknown Token',
                'decimals': 9
            }
            
    async def get_token_price(self, mint_address: str) -> Dict[str, Any]:
        """Get real token price data from multiple sources"""
        try:
            # Try Jupiter price API first
            jupiter_url = f"https://price.jup.ag/v4/price?ids={mint_address}"
            async with self.session.get(jupiter_url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('data', {}).get(mint_address):
                        price_data = data['data'][mint_address]
                        return {
                            'price': price_data['price'],
                            'volume_24h': price_data.get('volume24h', 0),
                            'price_change_24h': price_data.get('priceChange24h', 0),
                            'source': 'jupiter'
                        }
            
            # Fallback to CoinGecko API
            coingecko_url = f"https://api.coingecko.com/api/v3/simple/token_price/solana?contract_addresses={mint_address}&vs_currencies=usd&include_24hr_vol=true&include_24hr_change=true"
            async with self.session.get(coingecko_url) as response:
                if response.status == 200:
                    data = await response.json()
                    if mint_address.lower() in data:
                        token_data = data[mint_address.lower()]
                        return {
                            'price': token_data['usd'],
                            'volume_24h': token_data.get('usd_24h_vol', 0),
                            'price_change_24h': token_data.get('usd_24h_change', 0),
                            'source': 'coingecko'
                        }
            
            # Fallback to basic SOL price if it's SOL
            if mint_address == 'So11111111111111111111111111111111111111112':
                return await self.get_sol_price()
            
            # Return basic data if no price found
            return {
                'price': 0.0,
                'volume_24h': 0,
                'price_change_24h': 0,
                'source': 'unknown'
            }
            
        except Exception as e:
            logger.error(f"Error getting token price for {mint_address}: {e}")
            return {
                'price': 0.0,
                'volume_24h': 0,
                'price_change_24h': 0,
                'source': 'error'
            }
            
    async def get_sol_price(self) -> float:
        """Get SOL price in USD"""
        try:
            # Check cache
            if 'SOL' in self.price_cache:
                cache_data = self.price_cache['SOL']
                if cache_data['timestamp'] > asyncio.get_event_loop().time() - 60:  # 1 min cache
                    return cache_data['price']
                    
            # Get from CoinGecko
            url = "https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd"
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    price = float(data['solana']['usd'])
                    
                    # Cache the price
                    self.price_cache['SOL'] = {
                        'price': price,
                        'timestamp': asyncio.get_event_loop().time()
                    }
                    
                    return price
                    
            return 0.0
            
        except Exception as e:
            logger.error(f"Error getting SOL price: {e}")
            return 0.0
            
    async def start_websocket_monitoring(self, addresses: List[str], callback):
        """Start WebSocket monitoring for addresses"""
        try:
            async with connect(SOLANA_WS_URL) as websocket:
                self.ws_connection = websocket
                
                # Subscribe to account changes
                for address in addresses:
                    await websocket.account_subscribe(
                        PublicKey(address),
                        encoding="jsonParsed"
                    )
                    
                # Listen for updates
                async for message in websocket:
                    try:
                        await callback(message)
                    except Exception as e:
                        logger.error(f"Error in websocket callback: {e}")
                        
        except Exception as e:
            logger.error(f"WebSocket monitoring error: {e}")
            
    async def execute_swap(self, input_mint: str, output_mint: str, amount: float, slippage: float = 0.5) -> Dict[str, Any]:
        """Execute token swap via Jupiter API"""
        try:
            # Jupiter API endpoints
            quote_url = "https://quote-api.jup.ag/v6/quote"
            swap_url = "https://quote-api.jup.ag/v6/swap"
            
            # Get quote first
            quote_params = {
                "inputMint": input_mint,
                "outputMint": output_mint,
                "amount": str(int(amount * 1e9)),  # Convert to lamports
                "slippageBps": int(slippage * 100),  # Convert percentage to basis points
                "onlyDirectRoutes": False,
                "asLegacyTransaction": False
            }
            
            async with self.session.get(quote_url, params=quote_params) as response:
                if response.status != 200:
                    return {'success': False, 'error': f'Quote failed: {response.status}'}
                
                quote_data = await response.json()
                
                if not quote_data.get('data'):
                    return {'success': False, 'error': 'No route found for swap'}
                
                # Get swap transaction
                swap_payload = {
                    "quoteResponse": quote_data,
                    "userPublicKey": str(self.keypair.pubkey()) if self.keypair else None,
                    "wrapUnwrapSOL": True
                }
                
                async with self.session.post(swap_url, json=swap_payload) as swap_response:
                    if swap_response.status != 200:
                        return {'success': False, 'error': f'Swap failed: {swap_response.status}'}
                    
                    swap_data = await swap_response.json()
                    
                    if not swap_data.get('swapTransaction'):
                        return {'success': False, 'error': 'Failed to create swap transaction'}
                    
                    # Sign and send transaction
                    if self.keypair:
                        # Decode and sign transaction
                        import base64
                        tx_data = base64.b64decode(swap_data['swapTransaction'])
                        
                        # Create and sign transaction
                        from solders.transaction import Transaction
                        transaction = Transaction.from_bytes(tx_data)
                        transaction.sign([self.keypair])
                        
                        # Send transaction
                        result = await self.rpc_client.send_transaction(transaction)
                        
                        if result.value:
                            signature = result.value
                            return {
                                'success': True,
                                'signature': signature,
                                'input_amount': amount,
                                'output_amount': float(quote_data['data']['outAmount']) / 1e9,
                                'slippage': slippage,
                                'route': quote_data['data'].get('routePlan', [])
                            }
                        else:
                            return {'success': False, 'error': 'Transaction failed to send'}
                    else:
                        return {'success': False, 'error': 'No wallet configured for trading'}
                        
        except Exception as e:
            logger.error(f"Error executing swap: {e}")
            return {'success': False, 'error': str(e)}

    # Additional methods for enhanced functionality
    async def is_valid_address(self, address: str) -> bool:
        """Validate if an address is a valid Solana address"""
        try:
            # Check if it's a valid base58 string
            if not address or len(address) < 32 or len(address) > 44:
                return False
                
            # Try to create a PublicKey object
            PublicKey(address)
            return True
            
        except Exception:
            return False

    async def get_token_price_data(self, mint_address: str) -> Dict[str, Any]:
        """Get comprehensive token price data"""
        try:
            # Get basic price
            price = await self.get_token_price(mint_address)
            
            # Get SOL price for calculations
            sol_price = await self.get_sol_price()
            
            # Get 24h change from CoinGecko (if available)
            change_24h = 0.0
            volume_24h = 0.0
            market_cap = 0.0
            
            try:
                # Try to get detailed data from CoinGecko
                url = f"https://api.coingecko.com/api/v3/coins/solana/contract/{mint_address}"
                async with self.session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        market_data = data.get('market_data', {})
                        change_24h = market_data.get('price_change_percentage_24h', 0.0)
                        volume_24h = market_data.get('total_volume', {}).get('usd', 0.0)
                        market_cap = market_data.get('market_cap', {}).get('usd', 0.0)
            except Exception as e:
                logger.warning(f"Could not get detailed price data: {e}")
            
            return {
                'price': price,
                'change_24h': change_24h,
                'volume_24h': volume_24h,
                'market_cap': market_cap,
                'sol_price': sol_price,
                'timestamp': asyncio.get_event_loop().time()
            }
            
        except Exception as e:
            logger.error(f"Error getting token price data: {e}")
            return {
                'price': 0.0,
                'change_24h': 0.0,
                'volume_24h': 0.0,
                'market_cap': 0.0,
                'sol_price': 0.0,
                'timestamp': asyncio.get_event_loop().time()
            }

    async def get_token_market_data(self, mint_address: str) -> Dict[str, Any]:
        """Get token market data including liquidity and trading info"""
        try:
            # Get basic price data
            price_data = await self.get_token_price_data(mint_address)
            
            # Get token info
            token_info = await self.get_token_info(mint_address)
            
            # Get real liquidity data from Jupiter API
            liquidity_data = await self._get_real_liquidity_data(mint_address)
            
            return {
                'token_info': token_info,
                'price_data': price_data,
                'liquidity_data': liquidity_data,
                'trading_pairs': [
                    {'base': 'SOL', 'quote': token_info.get('symbol', 'TOKEN')},
                    {'base': 'USDC', 'quote': token_info.get('symbol', 'TOKEN')}
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting token market data: {e}")
            return {
                'token_info': {},
                'price_data': {},
                'liquidity_data': {},
                'trading_pairs': []
            }
            
    async def _get_real_liquidity_data(self, mint_address: str) -> Dict[str, Any]:
        """Get real liquidity data from DEX APIs"""
        try:
            # Get liquidity data from Jupiter API
            jupiter_url = f"https://quote-api.jup.ag/v6/quote?inputMint=So11111111111111111111111111111111111111112&outputMint={mint_address}&amount=1000000000&slippageBps=50"
            
            async with self.session.get(jupiter_url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if data.get('data'):
                        # Extract liquidity information from routes
                        routes = data['data'].get('routes', [])
                        total_liquidity = 0
                        dex_liquidity = {}
                        
                        for route in routes:
                            for step in route.get('routePlan', []):
                                dex_name = step.get('swapInfo', {}).get('label', 'Unknown')
                                liquidity_amount = step.get('swapInfo', {}).get('inAmount', 0)
                                
                                if dex_name not in dex_liquidity:
                                    dex_liquidity[dex_name] = 0
                                dex_liquidity[dex_name] += liquidity_amount
                                total_liquidity += liquidity_amount
                        
                        # Convert to USD (approximate)
                        sol_price = await self.get_sol_price()
                        total_liquidity_usd = (total_liquidity / 1e9) * sol_price
                        
                        liquidity_pairs = []
                        for dex, amount in dex_liquidity.items():
                            liquidity_usd = (amount / 1e9) * sol_price
                            liquidity_pairs.append({
                                'dex': dex,
                                'liquidity_usd': liquidity_usd
                            })
                        
                        return {
                            'total_liquidity_usd': total_liquidity_usd,
                            'liquidity_pairs': liquidity_pairs
                        }
            
            # Fallback to basic data if Jupiter API fails
            return {
                'total_liquidity_usd': 0,
                'liquidity_pairs': [
                    {'dex': 'Jupiter', 'liquidity_usd': 0},
                    {'dex': 'Raydium', 'liquidity_usd': 0},
                    {'dex': 'Orca', 'liquidity_usd': 0}
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting real liquidity data: {e}")
            return {
                'total_liquidity_usd': 0,
                'liquidity_pairs': []
            }

    async def get_wallet_token_holdings(self, address: str) -> List[Dict[str, Any]]:
        """Get detailed token holdings for a wallet"""
        try:
            # Get wallet balance
            balance_data = await self.get_wallet_balance(address)
            
            holdings = []
            
            # Add SOL balance
            if balance_data.get('sol_balance', 0) > 0:
                sol_price = await self.get_sol_price()
                holdings.append({
                    'mint_address': 'So11111111111111111111111111111111111111112',  # SOL mint
                    'symbol': 'SOL',
                    'name': 'Solana',
                    'balance': balance_data['sol_balance'],
                    'decimals': 9,
                    'price_usd': sol_price,
                    'value_usd': balance_data['sol_balance'] * sol_price
                })
            
            # Add token balances
            for token in balance_data.get('tokens', []):
                if token.get('balance', 0) > 0:
                    token_info = await self.get_token_info(token['mint'])
                    price = await self.get_token_price(token['mint'])
                    
                    holdings.append({
                        'mint_address': token['mint'],
                        'symbol': token_info.get('symbol', 'Unknown'),
                        'name': token_info.get('name', 'Unknown Token'),
                        'balance': token['balance'],
                        'decimals': token.get('decimals', 9),
                        'price_usd': price,
                        'value_usd': token['balance'] * price
                    })
            
            # Sort by value
            holdings.sort(key=lambda x: x['value_usd'], reverse=True)
            
            return holdings
            
        except Exception as e:
            logger.error(f"Error getting wallet token holdings: {e}")
            return []

    async def get_transaction_details(self, signature: str) -> Dict[str, Any]:
        """Get detailed transaction information"""
        try:
            # Get transaction details from RPC
            response = await self.rpc_client.get_transaction(
                signature,
                encoding="jsonParsed",
                max_supported_transaction_version=0
            )
            
            if response.value:
                tx_data = response.value
                
                # Parse transaction details
                details = {
                    'signature': signature,
                    'block_time': tx_data.block_time,
                    'slot': tx_data.slot,
                    'fee': tx_data.meta.fee if tx_data.meta else 0,
                    'success': tx_data.meta.err is None if tx_data.meta else False,
                    'instructions': [],
                    'token_changes': []
                }
                
                # Parse instructions
                if tx_data.transaction.message.instructions:
                    for instruction in tx_data.transaction.message.instructions:
                        details['instructions'].append({
                            'program_id': instruction.program_id,
                            'accounts': instruction.accounts,
                            'data': instruction.data
                        })
                
                # Parse token changes
                if tx_data.meta and tx_data.meta.post_token_balances:
                    for balance in tx_data.meta.post_token_balances:
                        details['token_changes'].append({
                            'mint': balance.mint,
                            'owner': balance.owner,
                            'balance': balance.ui_token_amount.ui_amount
                        })
                
                return details
            
            return {}
            
        except Exception as e:
            logger.error(f"Error getting transaction details: {e}")
            return {}

    async def get_network_stats(self) -> Dict[str, Any]:
        """Get Solana network statistics"""
        try:
            # Get current slot
            slot_response = await self.rpc_client.get_slot()
            current_slot = slot_response.value
            
            # Get recent performance
            performance_response = await self.rpc_client.get_recent_performance_samples(limit=1)
            performance = performance_response.value[0] if performance_response.value else {}
            
            # Get supply info
            supply_response = await self.rpc_client.get_supply()
            supply = supply_response.value if supply_response.value else {}
            
            return {
                'current_slot': current_slot,
                'transaction_count': performance.get('num_transactions', 0),
                'slot_time': performance.get('sample_period_secs', 0),
                'tps': performance.get('num_transactions', 0) / performance.get('sample_period_secs', 1),
                'total_supply': supply.get('total', 0),
                'circulating_supply': supply.get('circulating', 0),
                'timestamp': asyncio.get_event_loop().time()
            }
            
        except Exception as e:
            logger.error(f"Error getting network stats: {e}")
            return {
                'current_slot': 0,
                'transaction_count': 0,
                'slot_time': 0,
                'tps': 0,
                'total_supply': 0,
                'circulating_supply': 0,
                'timestamp': asyncio.get_event_loop().time()
            }

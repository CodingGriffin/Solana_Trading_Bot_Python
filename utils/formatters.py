"""
Message formatting utilities
"""

from typing import Dict, List, Any
from datetime import datetime

def format_wallet_info(wallet_data: Dict[str, Any]) -> str:
    """Format wallet information for display"""
    try:
        address = wallet_data.get('address', 'Unknown')
        sol_balance = wallet_data.get('sol_balance', 0)
        total_usd = wallet_data.get('total_usd_value', 0)
        token_count = wallet_data.get('token_count', 0)
        is_whale = wallet_data.get('is_whale', False)
        
        whale_emoji = "🐋" if is_whale else "👤"
        
        formatted = f"{whale_emoji} *Wallet Analysis*\n\n"
        formatted += f"📍 Address: `{address[:8]}...{address[-8:]}`\n"
        formatted += f"💰 SOL Balance: {sol_balance:.4f} SOL\n"
        formatted += f"💵 Total Value: ${total_usd:,.2f}\n"
        formatted += f"🪙 Tokens: {token_count}\n"
        
        if is_whale:
            formatted += f"🐋 Status: **WHALE WALLET**\n"
            
        # Add risk and profit scores if available
        analysis = wallet_data.get('analysis_data', {})
        if analysis:
            risk_score = analysis.get('risk_score', 0)
            profit_score = analysis.get('profit_score', 0)
            
            formatted += f"\n📊 *Analysis Scores*\n"
            formatted += f"⚠️ Risk Score: {risk_score}/100\n"
            formatted += f"📈 Profit Score: {profit_score}/100\n"
            
        return formatted
        
    except Exception as e:
        return f"❌ Error formatting wallet info: {str(e)}"

def format_trade_info(trade_data: Dict[str, Any]) -> str:
    """Format trade information for display"""
    try:
        trade_type = trade_data.get('trade_type', 'unknown').upper()
        amount = trade_data.get('amount', 0)
        status = trade_data.get('status', 'unknown').upper()
        created_at = trade_data.get('created_at')
        
        # Status emoji
        status_emojis = {
            'PENDING': '⏳',
            'EXECUTING': '⚡',
            'COMPLETED': '✅',
            'FAILED': '❌',
            'CANCELLED': '🚫'
        }
        
        status_emoji = status_emojis.get(status, '❓')
        
        formatted = f"{status_emoji} *Trade {trade_type}*\n\n"
        formatted += f"💰 Amount: {amount:.4f} SOL\n"
        formatted += f"📊 Status: {status}\n"
        
        if created_at:
            if isinstance(created_at, datetime):
                time_str = created_at.strftime('%Y-%m-%d %H:%M:%S')
            else:
                time_str = str(created_at)
            formatted += f"⏰ Created: {time_str}\n"
            
        # Add completion details if available
        if status == 'COMPLETED':
            output_amount = trade_data.get('output_amount', 0)
            signature = trade_data.get('signature', '')
            
            if output_amount:
                formatted += f"📤 Output: {output_amount:.4f} tokens\n"
            if signature:
                formatted += f"🔗 TX: `{signature[:16]}...`\n"
                
        elif status == 'FAILED':
            error = trade_data.get('error', 'Unknown error')
            formatted += f"❌ Error: {error}\n"
            
        return formatted
        
    except Exception as e:
        return f"❌ Error formatting trade info: {str(e)}"

def format_analysis_result(analysis_data: Dict[str, Any]) -> str:
    """Format analysis result for display"""
    try:
        formatted = "🔬 *Analysis Results*\n\n"
        
        # Basic metrics
        total_value = analysis_data.get('total_value_usd', 0)
        transaction_count = analysis_data.get('transaction_count', 0)
        token_diversity = analysis_data.get('token_diversity', 0)
        
        formatted += f"💵 Portfolio Value: ${total_value:,.2f}\n"
        formatted += f"📊 Transactions: {transaction_count}\n"
        formatted += f"🪙 Token Diversity: {token_diversity}\n\n"
        
        # Scores
        risk_score = analysis_data.get('risk_score', 0)
        profit_score = analysis_data.get('profit_score', 0)
        activity_score = analysis_data.get('activity_score', 0)
        
        formatted += f"*📊 Scores (0-100)*\n"
        formatted += f"⚠️ Risk: {risk_score}\n"
        formatted += f"📈 Profit: {profit_score}\n"
        formatted += f"⚡ Activity: {activity_score}\n\n"
        
        # Patterns
        patterns = analysis_data.get('patterns', [])
        if patterns:
            formatted += f"*🎯 Detected Patterns*\n"
            for pattern in patterns:
                pattern_name = pattern.replace('_', ' ').title()
                formatted += f"• {pattern_name}\n"
            formatted += "\n"
            
        # Risk factors
        risk_factors = analysis_data.get('risk_factors', [])
        if risk_factors:
            formatted += f"*⚠️ Risk Factors*\n"
            for factor in risk_factors:
                factor_name = factor.replace('_', ' ').title()
                formatted += f"• {factor_name}\n"
                
        return formatted
        
    except Exception as e:
        return f"❌ Error formatting analysis: {str(e)}"

def format_whale_activity(whale_data: List[Dict[str, Any]]) -> str:
    """Format whale activity for display"""
    try:
        if not whale_data:
            return "🐋 *Whale Activity*\n\nNo recent whale activity detected."
            
        formatted = "🐋 *Recent Whale Activity*\n\n"
        
        for i, activity in enumerate(whale_data[:10], 1):
            wallet = activity.get('wallet', '')
            amount = activity.get('amount', 0)
            amount_usd = activity.get('amount_usd', 0)
            token_symbol = activity.get('token_symbol', 'SOL')
            action = activity.get('action', 'unknown')
            timestamp = activity.get('timestamp', 'Unknown')
            
            action_emoji = "🟢" if action == "receive" else "🔴"
            
            formatted += f"{i}. {action_emoji} **{amount:.2f} {token_symbol}**\n"
            formatted += f"   💰 ${amount_usd:,.0f}\n"
            formatted += f"   📍 `{wallet[:8]}...{wallet[-8:]}`\n"
            formatted += f"   ⏰ {timestamp}\n\n"
            
        return formatted
        
    except Exception as e:
        return f"❌ Error formatting whale activity: {str(e)}"

def format_token_list(tokens: List[Dict[str, Any]]) -> str:
    """Format token list for display"""
    try:
        if not tokens:
            return "No tokens found."
            
        formatted = ""
        
        for token in tokens[:20]:  # Limit to 20 tokens
            symbol = token.get('symbol', 'UNKNOWN')
            amount = token.get('amount', 0)
            value_usd = token.get('value_usd', 0)
            
            formatted += f"🪙 **{symbol}**: {amount:.4f} (${value_usd:.2f})\n"
            
        return formatted
        
    except Exception as e:
        return f"❌ Error formatting token list: {str(e)}"

def format_price_change(current_price: float, previous_price: float) -> str:
    """Format price change with emoji"""
    try:
        if previous_price == 0:
            return "N/A"
            
        change_pct = ((current_price - previous_price) / previous_price) * 100
        
        if change_pct > 0:
            return f"📈 +{change_pct:.2f}%"
        elif change_pct < 0:
            return f"📉 {change_pct:.2f}%"
        else:
            return "➡️ 0.00%"
            
    except Exception as e:
        return "❌ Error"

def format_large_number(number: float) -> str:
    """Format large numbers with appropriate suffixes"""
    try:
        if number >= 1_000_000_000:
            return f"{number/1_000_000_000:.2f}B"
        elif number >= 1_000_000:
            return f"{number/1_000_000:.2f}M"
        elif number >= 1_000:
            return f"{number/1_000:.2f}K"
        else:
            return f"{number:.2f}"
            
    except Exception as e:
        return "0"

def format_time_ago(timestamp: datetime) -> str:
    """Format time ago string"""
    try:
        now = datetime.utcnow()
        diff = now - timestamp
        
        if diff.days > 0:
            return f"{diff.days}d ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours}h ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes}m ago"
        else:
            return "Just now"
            
    except Exception as e:
        return "Unknown"

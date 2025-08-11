# 🚀 Production Launch Checklist for Real Trading

## ⚠️ CRITICAL SECURITY CHECKS

### 1. **Environment Configuration**
- [ ] Copy `env.production` to `.env`
- [ ] Replace `YOUR_ACTUAL_BOT_TOKEN_HERE` with real Telegram bot token
- [ ] Replace `YOUR_ACTUAL_PRIVATE_KEY_HERE` with your Solana wallet private key
- [ ] Replace `YOUR_ADMIN_CHAT_ID_HERE` with your Telegram chat ID
- [ ] Verify all RPC URLs point to mainnet-beta.solana.com

### 2. **Wallet Security**
- [ ] Use a dedicated trading wallet (NOT your main wallet)
- [ ] Fund wallet with only the amount you're willing to risk
- [ ] Test wallet connection with small amount first
- [ ] Verify wallet has enough SOL for transaction fees

### 3. **Trading Limits (SAFETY FIRST)**
- [ ] MAX_TRADE_AMOUNT set to 5.0 SOL (conservative)
- [ ] MIN_TRADE_AMOUNT set to 0.1 SOL
- [ ] DEFAULT_SLIPPAGE set to 1.0% (higher for safety)
- [ ] Review all trading parameters in config/production.py

### 4. **Database Setup**
- [ ] Install MongoDB if not already installed
- [ ] Create database: `solana_bot`
- [ ] Test database connection
- [ ] Set up database backups

### 5. **System Requirements**
- [ ] Python 3.8+ installed
- [ ] All dependencies installed: `pip install -r requirements.txt`
- [ ] Virtual environment activated
- [ ] Sufficient disk space for logs
- [ ] Stable internet connection

## 🔧 PRE-LAUNCH TESTING

### 6. **Network Testing**
```bash
# Test Solana network connectivity
python test_network.py

# Test bot connectivity
python -c "from config.settings import BOT_TOKEN; print('Bot token configured')"
```

### 7. **Dry Run Testing**
- [ ] Test with testnet first (if available)
- [ ] Test all bot commands
- [ ] Test wallet connection
- [ ] Test database operations

## 🚀 LAUNCH PROCEDURE

### 8. **Final Launch Steps**
```bash
# 1. Check current status
./status.sh

# 2. Start the bot
./start_bot.sh

# 3. Monitor logs
tail -f /var/log/solana_bot.log

# 4. Test bot commands in Telegram
# Send /start to your bot
```

### 9. **Post-Launch Monitoring**
- [ ] Monitor bot logs for errors
- [ ] Test basic commands (/start, /help)
- [ ] Monitor wallet balance
- [ ] Check database connections
- [ ] Verify alerts are working

## ⚡ EMERGENCY PROCEDURES

### 10. **Emergency Stop**
```bash
# Stop the bot immediately
./restart_bot.sh

# Or kill the process
pkill -f "python main.py"
```

### 11. **Troubleshooting**
- [ ] Check logs: `tail -f /var/log/solana_bot.log`
- [ ] Check network: `python test_network.py`
- [ ] Check database: MongoDB connection
- [ ] Check wallet: Solana RPC connection

## 📊 MONITORING COMMANDS

```bash
# Check bot status
./status.sh

# View recent logs
tail -20 /var/log/solana_bot.log

# Check system resources
htop

# Check network connectivity
ping api.mainnet-beta.solana.com
```

## 🔒 SECURITY REMINDERS

- **NEVER share your private key**
- **Start with small amounts**
- **Monitor all transactions**
- **Keep backups of your configuration**
- **Use dedicated trading wallet only**
- **Set up alerts for all trades**

## 📞 SUPPORT

If issues occur:
1. Check logs first
2. Restart bot: `./restart_bot.sh`
3. Check network connectivity
4. Verify wallet balance
5. Contact support if needed

---

**⚠️ WARNING: Real trading involves financial risk. Only trade with amounts you can afford to lose.** 
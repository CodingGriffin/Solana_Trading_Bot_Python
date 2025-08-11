#!/bin/bash

echo "🚀 Setting up Solana Trading Bot for Production"
echo "================================================"

# Check if we're in the right directory
if [ ! -f "main.py" ]; then
    echo "❌ Error: main.py not found. Please run this script from the bot directory."
    exit 1
fi

# Step 1: Environment Setup
echo ""
echo "📝 Step 1: Environment Setup"
echo "----------------------------"

if [ ! -f ".env" ]; then
    if [ -f "env.production" ]; then
        echo "📋 Copying production environment template..."
        cp env.production .env
        echo "✅ Environment file created. Please edit .env with your actual values:"
        echo "   - BOT_TOKEN"
        echo "   - PRIVATE_KEY" 
        echo "   - ADMIN_CHAT_ID"
        echo ""
        echo "⚠️  IMPORTANT: Edit .env file before continuing!"
        read -p "Press Enter after editing .env file..."
    else
        echo "❌ No environment template found. Please create .env file manually."
        exit 1
    fi
else
    echo "✅ Environment file already exists"
fi

# Step 2: Virtual Environment
echo ""
echo "🐍 Step 2: Virtual Environment"
echo "------------------------------"

if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Step 3: Dependencies
echo ""
echo "📚 Step 3: Installing Dependencies"
echo "----------------------------------"

source venv/bin/activate
echo "🔧 Installing requirements..."
pip install -r requirements.txt

# Step 4: Database Setup
echo ""
echo "🗄️  Step 4: Database Setup"
echo "---------------------------"

echo "📊 Checking MongoDB..."
if command -v mongod &> /dev/null; then
    echo "✅ MongoDB is installed"
else
    echo "⚠️  MongoDB not found. Please install MongoDB:"
    echo "   Ubuntu/Debian: sudo apt install mongodb"
    echo "   Or use Docker: docker run -d -p 27017:27017 --name mongodb mongo"
fi

# Step 5: Network Test
echo ""
echo "🌐 Step 5: Network Connectivity Test"
echo "-----------------------------------"

if [ -f "test_network.py" ]; then
    echo "🔍 Testing Solana network connectivity..."
    python test_network.py
else
    echo "⚠️  test_network.py not found, skipping network test"
fi

# Step 6: Permissions
echo ""
echo "🔐 Step 6: Setting Permissions"
echo "-------------------------------"

chmod +x start_bot.sh
chmod +x restart_bot.sh
chmod +x status.sh
echo "✅ Script permissions set"

# Step 7: Log Directory
echo ""
echo "📝 Step 7: Log Directory Setup"
echo "------------------------------"

sudo mkdir -p /var/log
sudo touch /var/log/solana_bot.log
sudo chmod 666 /var/log/solana_bot.log
echo "✅ Log directory configured"

# Step 8: Final Checks
echo ""
echo "✅ Step 8: Final Configuration"
echo "------------------------------"

echo "🔍 Checking configuration..."
if [ -f ".env" ]; then
    echo "✅ Environment file exists"
else
    echo "❌ Environment file missing"
fi

if [ -d "venv" ]; then
    echo "✅ Virtual environment exists"
else
    echo "❌ Virtual environment missing"
fi

if [ -f "requirements.txt" ]; then
    echo "✅ Requirements file exists"
else
    echo "❌ Requirements file missing"
fi

echo ""
echo "🎉 Setup Complete!"
echo "=================="
echo ""
echo "📋 Next Steps:"
echo "1. Edit .env file with your actual values"
echo "2. Test the bot: ./status.sh"
echo "3. Start the bot: ./start_bot.sh"
echo "4. Monitor logs: tail -f /var/log/solana_bot.log"
echo ""
echo "⚠️  IMPORTANT REMINDERS:"
echo "- Use a dedicated trading wallet"
echo "- Start with small amounts"
echo "- Monitor all transactions"
echo "- Keep your private key secure"
echo ""
echo "🚀 Ready for production deployment!" 
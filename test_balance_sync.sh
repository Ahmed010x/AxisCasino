#!/bin/bash

# Balance Sync Test Script
# This script verifies that balance sync is working across all games and the main webapp

echo "🎰 Casino Balance Sync Test"
echo "==========================="

# Check if balance_sync.js exists
if [ -f "balance_sync.js" ]; then
    echo "✅ balance_sync.js found"
else
    echo "❌ balance_sync.js NOT found"
    exit 1
fi

# Check main webapp integration
if grep -q "balance_sync.js" casino_webapp_new.html; then
    echo "✅ Main webapp has balance_sync.js integration"
else
    echo "❌ Main webapp missing balance_sync.js integration"
fi

# Check games integration
echo ""
echo "Checking game integrations:"

games=("game_plinko.html" "game_mines.html" "game_blackjack.html" "game_crash.html" "game_limbo.html" "game_roulette.html" "game_hilo.html")

for game in "${games[@]}"; do
    if [ -f "$game" ]; then
        if grep -q "balance_sync.js" "$game"; then
            echo "✅ $game has balance_sync.js integration"
        else
            echo "⚠️  $game missing balance_sync.js integration"
        fi
    else
        echo "❓ $game not found"
    fi
done

# Check API endpoints in main.py
echo ""
echo "Checking API endpoints:"

if grep -q "/api/balance" main.py; then
    echo "✅ Balance API endpoints found in main.py"
else
    echo "❌ Balance API endpoints missing in main.py"
fi

if grep -q "/api/update_balance" main.py; then
    echo "✅ Update balance API endpoint found in main.py"
else
    echo "❌ Update balance API endpoint missing in main.py"
fi

echo ""
echo "🎯 Balance sync integration check complete!"
echo ""
echo "To test balance sync:"
echo "1. Open main webapp"
echo "2. Note current balance"
echo "3. Open any game in new tab"
echo "4. Place bet/win in game"
echo "5. Check if balance updated in main webapp tab"
echo "6. Refresh any page - balance should persist"

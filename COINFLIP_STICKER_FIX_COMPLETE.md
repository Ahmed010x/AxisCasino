# 🎯 Coinflip Sticker Fix - Complete Guide

## 🔴 Current Status

**Problem:** Coinflip game fails to send stickers with error:
```
telegram.error.BadRequest: Wrong file identifier/http url specified
```

**Cause:** Sticker file IDs in `COIN_STICKER_PACKS` have expired or become invalid.

**Temporary Fix:** ✅ Bot now uses dice animation fallback (working immediately!)

**Permanent Fix:** Need to collect fresh sticker file IDs from Telegram.

---

## ✅ Quick Start (Bot Works Now!)

The bot is already configured to use a dice animation fallback, so **your coinflip game works right now**:

```bash
cd "/Users/ahmed/Telegram Axis"
source .venv/bin/activate
export BOT_TOKEN="your_token_here"  # If needed
python main.py
```

Then in Telegram: `/coinflip` or use the game menu.

---

## 🎨 Get Fresh Stickers (For Better UX)

### Step 1: Verify Bot Token

```bash
cd "/Users/ahmed/Telegram Axis"
source .venv/bin/activate
export BOT_TOKEN="your_token_here"
python test_bot_token.py
```

Expected output:
```
✅ Bot is alive!
   Username: @your_bot
   Name: Your Bot Name
   ID: 123456789
```

### Step 2: Run Sticker Collector

```bash
python get_fresh_sticker_ids.py
```

You'll see:
```
🎯 STICKER FILE ID COLLECTOR
Instructions:
1. Start the bot (it should be running now)
2. Open Telegram and find your bot
3. Send a Bitcoin sticker to the bot (for HEADS)
4. Send an Ethereum sticker to the bot (for TAILS)
5. The file IDs will be printed below - copy them!

⏳ Waiting for stickers...
```

### Step 3: Send Stickers via Telegram

1. Open Telegram
2. Find your bot (from Step 1 output)
3. Search for crypto stickers:
   - Type "bitcoin" in sticker search
   - Type "ethereum" in sticker search
   - Or browse "Cryptocurrency" sticker packs
4. Send one Bitcoin sticker → This becomes HEADS
5. Send one Ethereum sticker → This becomes TAILS

### Step 4: Copy the Output

The script will print:
```
🎉 ALL STICKERS COLLECTED!

📋 Copy this configuration into coinflip.py:

COIN_STICKER_PACKS = {
    "heads": [
        "CAACAgEAAxk...NEW_VALID_ID_HERE",  # Bitcoin (Heads)
    ],
    "tails": [
        "CAACAgEAAxk...NEW_VALID_ID_HERE",  # Ethereum (Tails)
    ]
}
```

### Step 5: Update coinflip.py

Edit `/Users/ahmed/Telegram Axis/bot/games/coinflip.py`:

1. Replace the `COIN_STICKER_PACKS` dictionary with the new IDs (around line 22-30)
2. Change `USE_STICKERS = False` to `USE_STICKERS = True` (around line 34)

### Step 6: Restart and Test

```bash
# Stop the current bot (Ctrl+C if running)
python main.py

# In Telegram, test with:
/teststicker
```

---

## 🔧 Troubleshooting

### "BOT_TOKEN environment variable not set"
```bash
export BOT_TOKEN="123456:ABC-your-actual-token-here"
```

### Can't find crypto stickers in Telegram
- Open any chat in Telegram
- Click the sticker icon
- Search "bitcoin" or "cryptocurrency"
- Add a crypto sticker pack to your account
- Then send those stickers to your bot

### Want to use different stickers?
You can use ANY stickers! They don't have to be crypto-themed. The collector script works with any Telegram stickers:
- Coin stickers (🪙)
- Emoji stickers
- Cartoon stickers
- Custom sticker packs

Just send two different stickers - one for heads, one for tails!

### Stickers still not working after update
1. Check the file IDs are actually updated in `coinflip.py`
2. Verify `USE_STICKERS = True` is set
3. Check logs when you run `/teststicker`:
   ```bash
   python main.py 2>&1 | grep -i sticker
   ```

---

## 📁 Files Created

- ✅ `get_fresh_sticker_ids.py` - Collects sticker file IDs from Telegram
- ✅ `test_bot_token.py` - Verifies bot is working
- ✅ `GET_FRESH_STICKERS.md` - Detailed instructions
- ✅ `COINFLIP_STICKER_FIX_COMPLETE.md` - This guide

## 🎮 Current Configuration

**In `bot/games/coinflip.py`:**
- `USE_STICKERS = False` (temporary, until you get new IDs)
- `USE_DICE_ANIMATION = True` (fallback, works now!)

**After collecting new IDs:**
- `USE_STICKERS = True` (with fresh file IDs)
- `USE_DICE_ANIMATION = True` (keeps as fallback)

---

## ✨ Summary

**Right Now:** ✅ Bot works with dice animation
**After Fix:** 🎨 Bot will send beautiful Bitcoin/Ethereum stickers
**Time Needed:** ~5 minutes to collect and update sticker IDs

The coinflip game is fully functional immediately. Adding custom stickers is just a visual enhancement!

---

## 🚀 Next Steps

1. ✅ Bot is working now (dice animation)
2. 🎨 Optional: Collect fresh sticker IDs (better UX)
3. 🎯 Deploy and enjoy!

**Need help?** Check the logs or run `/teststicker` command in your bot.

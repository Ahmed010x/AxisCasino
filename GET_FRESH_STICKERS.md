# How to Get Fresh Sticker File IDs

## Problem
The sticker file IDs in your coinflip game have expired or become invalid. Telegram returns:
```
telegram.error.BadRequest: Wrong file identifier/http url specified
```

## Solution
Use the sticker collector script to get new, valid file IDs.

## Steps

### 1. Run the Sticker Collector Script

```bash
cd "/Users/ahmed/Telegram Axis"
source .venv/bin/activate  # Activate your virtual environment
export BOT_TOKEN="your_bot_token_here"  # If not already set
python get_fresh_sticker_ids.py
```

### 2. Send Stickers to Your Bot

Open Telegram and:
1. Find your bot
2. Search for and send a **Bitcoin** sticker (this will be used for HEADS)
3. Search for and send an **Ethereum** sticker (this will be used for TAILS)

**Finding crypto stickers:**
- Search "bitcoin" or "crypto" in Telegram's sticker search
- Look for sticker packs like:
  - "Cryptocurrency"
  - "Bitcoin & Crypto"
  - "Crypto Coins"

### 3. Copy the File IDs

The script will print output like:
```
COIN_STICKER_PACKS = {
    "heads": [
        "CAACAgEAAxkBAAEPfLto3fLKQk9KP9FaLSYjwZih82J-sQACIAYAAhUgyUYe7AYU47cPsDYE",  # Bitcoin (Heads)
    ],
    "tails": [
        "CAACAgEAAxkBAAEPfL1o3fOba1jsv5rN1Ojdu5f0DCp_6wACHwYAAhUgyUbBT2yx1FdJ7DYE",  # Ethereum (Tails)
    ]
}
```

### 4. Update coinflip.py

Replace the `COIN_STICKER_PACKS` dictionary in `bot/games/coinflip.py` with the new IDs.

### 5. Test the Stickers

After updating, test with:
```bash
# Restart your bot
python main.py

# In Telegram, use:
/teststicker
```

## Alternative: Use Popular Sticker Packs

If you want to use stickers from a specific pack:

1. Find a crypto sticker pack in Telegram (e.g., search "bitcoin stickers")
2. Add the pack to your account
3. Send stickers from that pack to your bot
4. The collector script will show you the file IDs

## Troubleshooting

### "BOT_TOKEN environment variable not set"
```bash
export BOT_TOKEN="your_actual_bot_token"
```

### Can't find crypto stickers
- Search "@sticker" in Telegram
- Browse "Trending" stickers
- Or use any coin/crypto themed stickers you like

### Need different stickers
You can use ANY stickers for heads/tails. Common alternatives:
- 🎲 Dice stickers
- 🎰 Casino themed stickers
- 🪙 Coin stickers
- Any two distinct stickers you prefer

## Quick Fix

If you just want to get the bot working quickly, you can:

1. Disable stickers temporarily:
   ```python
   USE_STICKERS = False
   USE_DICE_ANIMATION = True
   ```

2. Or use Telegram's built-in dice emoji (no file IDs needed)

But for the best user experience, fresh sticker IDs are recommended!

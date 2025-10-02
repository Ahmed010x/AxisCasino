# Coin Flip Sticker Troubleshooting Guide

## Issue: Stickers Not Showing in Coin Flip Game

### What I've Implemented

1. **Enhanced Logging**: The bot now logs detailed information about sticker sending attempts
2. **Fallback System**: If stickers fail, an emoji message is sent instead
3. **Better Error Handling**: Catches and logs all sticker-related errors
4. **Test Script**: Created `test_coinflip_sticker.py` to test stickers directly

### How to Diagnose the Problem

#### Step 1: Check the Bot Logs

After playing coin flip, check your bot logs (console output or `casino_bot.log`) for:

```
✅ Successfully sent bitcoin sticker to user XXX
```

or

```
❌ Failed to send sticker: [error details]
```

#### Step 2: Run the Test Script

Run the sticker test script to verify stickers work independently:

```bash
python test_coinflip_sticker.py
```

This will:
1. Connect to your bot
2. Ask for your chat_id
3. Send both Bitcoin and Ethereum stickers to you

#### Step 3: Check Common Issues

**Issue 1: Bot Token Invalid**
- Error: `Unauthorized` or connection errors
- Fix: Verify `BOT_TOKEN` in `.env` is correct

**Issue 2: Sticker IDs Invalid**
- Error: `Bad Request: wrong file identifier/http url specified`
- Fix: The sticker IDs may have expired or changed
- Solution: Get new sticker IDs (see below)

**Issue 3: Bot Permissions**
- Error: `Forbidden: bot can't send messages to the user`
- Fix: Start a conversation with the bot first

**Issue 4: Network/API Issues**
- Error: `Timeout` or `Connection error`
- Fix: Check internet connection, try again

### How to Get New Sticker IDs

If the current sticker IDs don't work, you need to get new ones:

1. **Find Bitcoin/Ethereum Stickers on Telegram**
   - Search for Bitcoin or Ethereum sticker packs
   - Or use any sticker you like

2. **Get the Sticker File ID**
   - Forward the sticker to @userinfobot
   - Or use this code:

```python
# Add this to your bot to log sticker IDs
@app.message_handler(content_types=['sticker'])
async def handle_sticker(update, context):
    sticker = update.message.sticker
    print(f"Sticker ID: {sticker.file_id}")
    print(f"Unique ID: {sticker.file_unique_id}")
    await update.message.reply_text(f"Sticker ID: `{sticker.file_id}`")
```

3. **Update the Sticker IDs**
   - Edit `bot/games/coinflip.py`
   - Replace the IDs at the top:

```python
BITCOIN_STICKER_ID = "YOUR_NEW_BITCOIN_STICKER_ID"
ETHEREUM_STICKER_ID = "YOUR_NEW_ETHEREUM_STICKER_ID"
```

### Current Sticker IDs

```python
BITCOIN_STICKER_ID = "CAACAgEAAxkBAAEPfLto3fLKQk9KP9FaLSYjwZih82J-sQACIAYAAhUgyUYe7AYU47cPsDYE"
ETHEREUM_STICKER_ID = "CAACAgEAAxkBAAEPfL1o3fOba1jsv5rN1Ojdu5f0DCp_6wACHwYAAhUgyUbBT2yx1FdJ7DYE"
```

### What Happens Now

When you play coin flip:

1. ✅ The betting menu appears
2. ✅ You choose Bitcoin or Ethereum
3. ✅ The old message is deleted
4. 🎯 **The bot attempts to send a sticker**
   - If successful: You see the Bitcoin/Ethereum sticker
   - If failed: You see an emoji message (₿ BITCOIN ₿)
5. ✅ You see the win/loss results

### Testing Steps

1. **Start your bot** (if not running)
2. **Play a coin flip game** in Telegram
3. **Check if you see**:
   - A sticker animation (Bitcoin or Ethereum)
   - OR an emoji message (if sticker failed)
   - Followed by the win/loss message

4. **Check the logs** for any errors
5. **If stickers still don't work**, run the test script

### Quick Fix

If you want to disable stickers temporarily and just use emojis:

Edit `bot/games/coinflip.py` and comment out the sticker sending:

```python
# # Send sticker animation for visual effect
# sticker_sent = False
# sticker_id = BITCOIN_STICKER_ID if result == "bitcoin" else ETHEREUM_STICKER_ID
# 
# try:
#     ... (comment out all sticker code)
```

The fallback emoji message will always show instead.

### Getting Help

If stickers still don't work after trying these steps:

1. **Share the bot logs** showing the error
2. **Confirm you can receive other stickers** from your bot
3. **Try the test script** and share the output
4. **Check if your bot has the right permissions** to send stickers

## Expected Behavior

✅ **Working correctly**: You see a Bitcoin or Ethereum sticker appear, followed by the results
⚠️ **Fallback mode**: You see "₿ BITCOIN ₿" or "Ξ ETHEREUM Ξ" emoji message, followed by results
❌ **Not working**: No sticker, no emoji, just results (check logs)

## Notes

- Sticker IDs can expire or become invalid over time
- The bot needs proper permissions to send stickers
- Network issues can cause sticker sending to fail
- The fallback system ensures the game still works even if stickers fail

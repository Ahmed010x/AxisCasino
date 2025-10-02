# Quick Fix: Add Sticker ID Command to Your Bot

If you want to quickly get sticker IDs to replace the current ones, add this to your `main.py`:

## Step 1: Add this handler function

```python
async def handle_sticker_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle sticker messages to get their file IDs"""
    if update.message and update.message.sticker:
        sticker = update.message.sticker
        sticker_id = sticker.file_id
        
        # Send the sticker ID back to the user
        await update.message.reply_text(
            f"📌 <b>Sticker Information</b>\n\n"
            f"<b>File ID:</b>\n<code>{sticker_id}</code>\n\n"
            f"<b>Unique ID:</b> <code>{sticker.file_unique_id}</code>\n\n"
            f"<i>Tap the File ID to copy it</i>",
            parse_mode=ParseMode.HTML
        )
        logger.info(f"User {update.effective_user.id} sent sticker: {sticker_id}")
```

## Step 2: Register the handler in main()

Find the `main()` function and add this handler:

```python
def main():
    # ...existing code...
    
    # Add sticker handler for getting sticker IDs
    app.add_handler(MessageHandler(filters.Sticker.ALL, handle_sticker_message))
    
    # ...rest of the code...
```

## Step 3: Get New Sticker IDs

1. Restart your bot
2. Send any Bitcoin sticker to your bot
3. The bot will reply with the sticker's File ID
4. Copy that ID
5. Send any Ethereum sticker to your bot
6. Copy that ID too

## Step 4: Update coinflip.py

Replace the old sticker IDs in `bot/games/coinflip.py`:

```python
# Old IDs (may be expired)
BITCOIN_STICKER_ID = "CAACAgEAAxkBAAEPfLto3fLKQk9KP9FaLSYjwZih82J-sQACIAYAAhUgyUYe7AYU47cPsDYE"
ETHEREUM_STICKER_ID = "CAACAgEAAxkBAAEPfL1o3fOba1jsv5rN1Ojdu5f0DCp_6wACHwYAAhUgyUbBT2yx1FdJ7DYE"

# Replace with new IDs
BITCOIN_STICKER_ID = "YOUR_NEW_BITCOIN_STICKER_ID_HERE"
ETHEREUM_STICKER_ID = "YOUR_NEW_ETHEREUM_STICKER_ID_HERE"
```

## Alternative: Use Coin Emojis Instead

If you don't want to deal with stickers at all, you can replace the sticker code with just sending an emoji:

In `bot/games/coinflip.py`, replace the sticker sending section with:

```python
# Send emoji animation instead of sticker
emoji = "🪙" if result == "bitcoin" else "💎"
animation_msg = f"{emoji} {emoji} {emoji}\n\n<b>{result_text}!</b>\n\n{emoji} {emoji} {emoji}"

await context.bot.send_message(
    chat_id=query.message.chat_id,
    text=animation_msg,
    parse_mode=ParseMode.HTML
)
```

This will show a simple but effective emoji animation instead of stickers.

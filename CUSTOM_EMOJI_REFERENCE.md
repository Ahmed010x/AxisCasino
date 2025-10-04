# 🎮 Quick Reference: Custom Emoji IDs

## Coin Flip Game Custom Emoji

### Emoji IDs
```
Heads: 5886663771962743061
Tails: 5886234567290918532
```

### Usage in Code
```python
# At top of file
HEADS_EMOJI_ID = "5886663771962743061"
TAILS_EMOJI_ID = "5886234567290918532"

# To display in Telegram message
heads_emoji = f'<tg-emoji emoji-id="{HEADS_EMOJI_ID}">🪙</tg-emoji>'
tails_emoji = f'<tg-emoji emoji-id="{TAILS_EMOJI_ID}">🪙</tg-emoji>'

# In message text (use ParseMode.HTML)
message = f"Result: {heads_emoji} HEADS"
await bot.send_message(chat_id=..., text=message, parse_mode=ParseMode.HTML)
```

### Visual Representation
- 🟡 HEADS - Yellow theme, ID: 5886663771962743061
- 🔵 TAILS - Blue theme, ID: 5886234567290918532

---

## Important Notes

1. **Parse Mode Required**: Must use `ParseMode.HTML` when sending messages with custom emoji
2. **Fallback**: The `🪙` inside the tag is the fallback emoji (shown if custom emoji fails)
3. **Testing**: Custom emoji only displays in actual Telegram clients, not in logs/console
4. **Format**: Always use `<tg-emoji emoji-id="ID">fallback</tg-emoji>` format

---

## File Location
`/Users/ahmed/Telegram Axis/bot/games/coinflip.py`

---

**Last Updated**: October 4, 2025

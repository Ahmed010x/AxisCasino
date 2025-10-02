# 🎭 HOW TO GET STICKER IDs FOR CRYPTO FLIP

## 📝 QUICK GUIDE

Follow these simple steps to get Bitcoin and Ethereum sticker IDs for your Crypto Flip game:

---

## 🔍 METHOD 1: Using @userinfobot (Recommended)

### **Step 1: Find or Create Stickers**
- Search for Bitcoin and Ethereum stickers in Telegram
- Or create your own custom crypto stickers
- Make sure they clearly represent each cryptocurrency

### **Step 2: Get Sticker File IDs**

#### For Bitcoin Sticker:
1. Send your chosen Bitcoin sticker to **@userinfobot**
2. The bot will reply with sticker information
3. Look for the line that says `File ID:` or `file_id:`
4. Copy the long string (looks like: `CAACAgQAAxkBAAE...`)

#### For Ethereum Sticker:
1. Send your chosen Ethereum sticker to **@userinfobot**
2. The bot will reply with sticker information
3. Copy the `File ID` from the response

### **Step 3: Update the Code**

Open `/Users/ahmed/Telegram Axis/bot/games/coinflip.py` and replace:

```python
# Current placeholders (lines 19-20):
BITCOIN_STICKER_ID = "CAACAgQAAxkBAAEBm7Rmh3K5_YOUR_BITCOIN_STICKER_ID"
ETHEREUM_STICKER_ID = "CAACAgQAAxkBAAEBm7Zmh3K5_YOUR_ETHEREUM_STICKER_ID"

# Replace with your actual IDs:
BITCOIN_STICKER_ID = "CAACAgQAAxkBAAE..."  # Your Bitcoin sticker file_id
ETHEREUM_STICKER_ID = "CAACAgQAAxkBAAE..."  # Your Ethereum sticker file_id
```

---

## 🔍 METHOD 2: Using Your Own Bot (Alternative)

### **Step 1: Forward Stickers to Your Bot**
1. Send Bitcoin sticker to your casino bot
2. Send Ethereum sticker to your casino bot

### **Step 2: Get File IDs from Logs**
Your bot logs will show:
```
Received sticker with file_id: CAACAgQAAxkBAAE...
```

### **Step 3: Update Code**
Copy those file_ids to `coinflip.py` as shown above

---

## 📋 STICKER RECOMMENDATIONS

### **Good Sticker Characteristics:**
- ✅ Clear Bitcoin symbol (₿) or Bitcoin logo
- ✅ Clear Ethereum symbol (Ξ) or Ethereum logo
- ✅ Distinctive colors (Bitcoin: Orange, Ethereum: Blue/Purple)
- ✅ Animated is nice but not required
- ✅ Professional looking
- ✅ Not too large (under 512x512)

### **Where to Find Stickers:**

1. **Telegram Sticker Packs:**
   - Search "Bitcoin stickers" in Telegram
   - Search "Ethereum stickers" in Telegram
   - Search "Crypto stickers" for bundles

2. **Popular Crypto Sticker Packs:**
   - @CryptoCurrencyStickers
   - @BitcoinStickers
   - @EthereumStickers

3. **Create Custom Stickers:**
   - Use @stickers bot to create custom pack
   - Design your own Bitcoin/Ethereum stickers
   - Upload and get file_ids

---

## 🧪 TESTING AFTER UPDATE

### **Step 1: Save Changes**
After updating the sticker IDs, save `coinflip.py`

### **Step 2: Restart Bot**
```bash
# Stop current bot process
# Then start again:
python main.py
```

### **Step 3: Test in Telegram**
1. Start a conversation with your bot
2. Go to Games → Crypto Flip
3. Place a bet
4. Choose Bitcoin or Ethereum
5. Check if sticker appears in result

### **Expected Behavior:**
- ✅ Sticker sends before text result
- ✅ Correct sticker for result (Bitcoin or Ethereum)
- ✅ Fallback to text-only if sticker fails
- ✅ Game continues normally

---

## 🐛 TROUBLESHOOTING

### **Problem: Sticker not appearing**

**Possible Causes:**
1. Incorrect file_id format
2. Sticker deleted or expired
3. Bot lacks permission to send stickers

**Solutions:**
- Verify file_id is complete (starts with `CAACAgQ...`)
- Test sticker exists by sending it manually
- Check bot permissions in chat
- Try different stickers

### **Problem: Error sending sticker**

**Expected:** Game falls back to text-only mode automatically

**Code handles this gracefully:**
```python
try:
    await context.bot.send_sticker(...)
    sticker_sent = True
except Exception as e:
    logger.debug(f"Could not send sticker: {e}")
    # Game continues with text only
```

---

## 📝 EXAMPLE STICKER FILE IDs

**Format:** 
```
CAACAgQAAxkBAAEBm7RmRXj8_v9-HqL8X9Z3K5J7Y2P0AAI9AANdS3hRq...
```

**Characteristics:**
- Always starts with `CAACAgQ` or similar
- Very long string (50-100+ characters)
- Contains letters, numbers, underscores, hyphens
- Case-sensitive

---

## ✅ VERIFICATION CHECKLIST

Before going live, verify:

- [ ] Bitcoin sticker ID copied correctly
- [ ] Ethereum sticker ID copied correctly
- [ ] Both IDs start with "CAACAgQ" or similar
- [ ] Code saved and bot restarted
- [ ] Tested game with Bitcoin choice
- [ ] Tested game with Ethereum choice
- [ ] Stickers appear for both outcomes
- [ ] Game works even if stickers fail
- [ ] Balance updates correctly
- [ ] Can play multiple rounds

---

## 🎨 VISUAL FLOW

```
User plays Crypto Flip
         ↓
    Selects Bitcoin
         ↓
    Coin flips...
         ↓
  Result: Bitcoin!
         ↓
[Bitcoin Sticker Appears] ← YOU NEED THE ID FOR THIS
         ↓
    Result message
         ↓
   Balance updated
```

---

## 💡 PRO TIPS

1. **Test Stickers First:** Send stickers manually to verify they work
2. **Keep Backup IDs:** Save sticker IDs in a text file
3. **Consistent Theme:** Use stickers from same pack for visual consistency
4. **Animated Stickers:** More engaging but not required
5. **Fallback Works:** Even without stickers, game is fully functional

---

## 📞 NEED HELP?

**File to Edit:** `/Users/ahmed/Telegram Axis/bot/games/coinflip.py`

**Lines to Update:** 19-20

**Current Placeholders:**
```python
BITCOIN_STICKER_ID = "CAACAgQAAxkBAAEBm7Rmh3K5_YOUR_BITCOIN_STICKER_ID"
ETHEREUM_STICKER_ID = "CAACAgQAAxkBAAEBm7Zmh3K5_YOUR_ETHEREUM_STICKER_ID"
```

**What to Replace:**
- Everything after the `=` sign
- Keep the quotes `""`
- Paste your actual sticker file_id

---

## 🎉 READY TO GO!

Once you have the sticker IDs:
1. Update the two lines in `coinflip.py`
2. Save the file
3. Restart your bot
4. Test the game
5. Enjoy enhanced crypto flip experience!

The game is already fully functional - stickers just add extra visual flair! 🚀

---

**Last Updated:** December 2024
**Status:** Waiting for Sticker IDs

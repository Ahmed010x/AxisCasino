# 🎮 CUSTOM BET FEATURE - IMPLEMENTATION GUIDE

## ✅ COMPLETED: Coin Flip Game

The Coin Flip game now has complete custom bet functionality including:
- ✅ Fixed bet buttons ($1, $5, $10, $25, $50, $100)
- ✅ Half balance button (bet 50% of balance)
- ✅ All-In button (bet entire balance)
- ✅ Custom amount input (enter any amount)
- ✅ Full validation (min/max/balance checks)
- ✅ Text input handler integrated

---

## 📋 FEATURES INCLUDED

### **1. Preset Bet Buttons**
Standard amounts for quick betting:
- $1, $5, $10, $25, $50, $100

### **2. Half Balance**
- Button shows: `💰 Half ($X.XX)`
- Dynamically calculated based on current balance
- Bets exactly 50% of user's balance

### **3. All-In**
- Button shows: `🎰 All-In ($X.XX)`
- Dynamically shows full balance
- Bets everything the user has

### **4. Custom Amount**
- Button shows: `✏️ Custom Amount`
- User types any amount they want
- Full validation applied:
  - Minimum: $1.00
  - Maximum: $1000.00
  - Must not exceed balance
  - Must be valid number

---

## 🎯 HOW IT WORKS

### **User Flow:**

```
1. User clicks "Crypto Flip" from games menu
   ↓
2. Sees bet options menu with:
   - Preset amounts ($1, $5, $10, etc.)
   - Half balance button
   - All-In button
   - Custom amount button
   ↓
3. If they click "Custom Amount":
   - Bot asks them to type amount
   - Sets state: awaiting_coinflip_custom_bet = True
   ↓
4. User types amount (e.g., "15.50")
   ↓
5. Bot validates:
   - Is it a number?
   - Is it >= $1.00?
   - Is it <= $1000.00?
   - Do they have enough balance?
   ↓
6. If valid:
   - Shows Bitcoin vs Ethereum choice
   - Game proceeds normally
   ↓
7. If invalid:
   - Shows error message
   - Asks them to try again
```

---

## 🔧 TECHNICAL IMPLEMENTATION

### **Files Modified:**

1. **`bot/games/coinflip.py`**
   - Added `request_custom_bet()` function
   - Added `handle_custom_bet_input()` function  
   - Updated `show_coinflip_menu()` with new buttons
   - Exported both functions

2. **`main.py`**
   - Imported `handle_custom_bet_input` as `handle_coinflip_custom_bet`
   - Added check in `handle_text_input_main()` for custom bet state

### **Key Functions:**

#### **1. show_coinflip_menu()**
```python
# Calculate dynamic amounts
half_balance = user['balance'] / 2
all_balance = user['balance']

# Add buttons
keyboard = [
    [
        InlineKeyboardButton("$1", callback_data="coinflip_bet_1"),
        InlineKeyboardButton("$5", callback_data="coinflip_bet_5"),
        # ... more preset amounts
    ],
    [
        InlineKeyboardButton(f"💰 Half (${half_balance:.2f})", 
                           callback_data=f"coinflip_bet_{half_balance:.2f}"),
        InlineKeyboardButton(f"🎰 All-In (${all_balance:.2f})", 
                           callback_data=f"coinflip_bet_{all_balance:.2f}")
    ],
    [InlineKeyboardButton("✏️ Custom Amount", callback_data="coinflip_custom_bet")]
]
```

#### **2. request_custom_bet()**
```python
async def request_custom_bet(update, context):
    # Set awaiting state
    context.user_data['awaiting_coinflip_custom_bet'] = True
    
    # Show input prompt
    await query.edit_message_text("Please enter your bet amount...")
```

#### **3. handle_custom_bet_input()**
```python
async def handle_custom_bet_input(update, context):
    # Check if we're waiting for input
    if not context.user_data.get('awaiting_coinflip_custom_bet'):
        return
    
    # Parse and validate amount
    bet_amount = float(update.message.text.strip())
    
    # Validate min/max/balance
    if bet_amount < MIN_BET:
        # Show error
        return
    
    # Clear state
    context.user_data['awaiting_coinflip_custom_bet'] = False
    
    # Continue to game
    await show_coinflip_choice(...)
```

#### **4. main.py Integration:**
```python
# Import
from bot.games.coinflip import handle_coinflip_callback, handle_custom_bet_input as handle_coinflip_custom_bet

# Handle text input
async def handle_text_input_main(update, context):
    if 'awaiting_coinflip_custom_bet' in context.user_data:
        await handle_coinflip_custom_bet(update, context)
        return
    # ... other handlers
```

---

## 📊 VALIDATION RULES

### **Amount Validation:**
| Check | Rule | Error Message |
|-------|------|---------------|
| **Minimum** | >= $1.00 | "Bet amount too low! Minimum: $1.00" |
| **Maximum** | <= $1000.00 | "Bet amount too high! Maximum: $1000.00" |
| **Balance** | <= user balance | "Insufficient balance!" |
| **Format** | Valid number | "Invalid input! Please enter a valid number" |

### **State Management:**
- State stored in: `context.user_data['awaiting_coinflip_custom_bet']`
- Set to `True` when waiting for input
- Set to `False` after successful input
- Cleared when user navigates away

---

## 🎮 TO-DO: Apply to Other Games

The same pattern needs to be applied to:

### **1. Slots Game** (`bot/games/slots.py`)
- Add Half/All-In/Custom buttons
- Add `request_custom_bet()` function
- Add `handle_custom_bet_input()` function
- State: `awaiting_slots_custom_bet`

### **2. Dice Game** (`bot/games/dice.py`)
- Add Half/All-In/Custom buttons
- Add `request_custom_bet()` function
- Add `handle_custom_bet_input()` function
- State: `awaiting_dice_custom_bet`

### **3. Blackjack Game** (`bot/games/blackjack.py`)
- Add Half/All-In/Custom buttons
- Add `request_custom_bet()` function
- Add `handle_custom_bet_input()` function
- State: `awaiting_blackjack_custom_bet`

### **4. Roulette Game** (`bot/games/roulette.py`)
- Add Half/All-In/Custom buttons
- Add `request_custom_bet()` function
- Add `handle_custom_bet_input()` function
- State: `awaiting_roulette_custom_bet`

### **5. Poker Game** (`bot/games/poker.py`)
- Add Half/All-In/Custom buttons
- Add `request_custom_bet()` function
- Add `handle_custom_bet_input()` function
- State: `awaiting_poker_custom_bet`

---

## 📝 TEMPLATE FOR OTHER GAMES

Use this template to add custom bets to other games:

### **Step 1: Update Game Menu Function**
```python
async def show_GAME_menu(update, context):
    # ... existing code ...
    
    # Calculate dynamic amounts
    half_balance = user['balance'] / 2
    all_balance = user['balance']
    
    keyboard = [
        # Existing preset buttons
        [
            InlineKeyboardButton("$1", callback_data="GAME_bet_1"),
            InlineKeyboardButton("$5", callback_data="GAME_bet_5"),
            InlineKeyboardButton("$10", callback_data="GAME_bet_10")
        ],
        # Add these new buttons
        [
            InlineKeyboardButton(f"💰 Half (${half_balance:.2f})", 
                               callback_data=f"GAME_bet_{half_balance:.2f}"),
            InlineKeyboardButton(f"🎰 All-In (${all_balance:.2f})", 
                               callback_data=f"GAME_bet_{all_balance:.2f}")
        ],
        [InlineKeyboardButton("✏️ Custom Amount", callback_data="GAME_custom_bet")],
        # ... existing back button ...
    ]
```

### **Step 2: Add Request Function**
```python
async def request_custom_bet(update, context):
    """Request custom bet amount from user"""
    query = update.callback_query
    user_id = query.from_user.id
    
    # Get user info
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from main import get_user, format_usd
    
    user = await get_user(user_id)
    if not user:
        await query.edit_message_text("❌ User not found")
        return
    
    balance_str = await format_usd(user['balance'])
    
    # Set state
    context.user_data['awaiting_GAME_custom_bet'] = True
    
    text = f"""
✏️ <b>CUSTOM BET AMOUNT</b> ✏️

💰 <b>Your Balance:</b> {balance_str}

Please enter your custom bet amount in USD.

<b>Bet Limits:</b>
• Minimum: ${MIN_BET:.2f}
• Maximum: ${MAX_BET:.2f}

💡 <i>Type a number (e.g., "15.50")</i>
"""
    
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="game_GAME")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
```

### **Step 3: Add Input Handler**
```python
async def handle_custom_bet_input(update, context):
    """Handle custom bet amount input"""
    if not context.user_data.get('awaiting_GAME_custom_bet'):
        return
    
    user_id = update.message.from_user.id
    
    # Import functions
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from main import get_user, format_usd
    
    try:
        # Parse amount
        bet_amount = float(update.message.text.strip().replace('$', '').replace(',', ''))
        
        # Validate
        if bet_amount < MIN_BET:
            await update.message.reply_text(f"❌ Minimum bet: ${MIN_BET:.2f}")
            return
        
        if bet_amount > MAX_BET:
            await update.message.reply_text(f"❌ Maximum bet: ${MAX_BET:.2f}")
            return
        
        user = await get_user(user_id)
        if bet_amount > user['balance']:
            await update.message.reply_text("❌ Insufficient balance!")
            return
        
        # Clear state
        context.user_data['awaiting_GAME_custom_bet'] = False
        
        # Continue to game (game-specific)
        await show_GAME_play_screen(update, context, bet_amount)
        
    except ValueError:
        await update.message.reply_text("❌ Invalid input! Please enter a number.")
```

### **Step 4: Update Main Callback Handler**
```python
async def handle_GAME_callback(update, context):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == "game_GAME":
        await show_GAME_menu(update, context)
    elif data == "GAME_custom_bet":
        await request_custom_bet(update, context)  # Add this
    elif data.startswith("GAME_bet_"):
        # ... existing bet handling ...
```

### **Step 5: Export Handlers**
```python
# At end of file
__all__ = ['handle_GAME_callback', 'handle_custom_bet_input']
```

### **Step 6: Update main.py**
```python
# Import
from bot.games.GAME import handle_GAME_callback, handle_custom_bet_input as handle_GAME_custom_bet

# Add to text handler
async def handle_text_input_main(update, context):
    # ... existing handlers ...
    elif 'awaiting_GAME_custom_bet' in context.user_data:
        await handle_GAME_custom_bet(update, context)
        return
    # ... rest ...
```

---

## ✅ BENEFITS

### **For Players:**
- ✅ More betting flexibility
- ✅ Quick half/all-in options
- ✅ Custom amounts for precise betting
- ✅ Better user experience

### **For Casino:**
- ✅ Higher engagement
- ✅ More bets per session
- ✅ Professional feature set
- ✅ Competitive with major casinos

---

## 🚀 STATUS

| Game | Custom Bets | Half Button | All-In | Custom Input | Status |
|------|------------|-------------|---------|--------------|--------|
| **Coin Flip** | ✅ | ✅ | ✅ | ✅ | **COMPLETE** |
| **Slots** | ❌ | ❌ | ❌ | ❌ | TODO |
| **Dice** | ❌ | ❌ | ❌ | ❌ | TODO |
| **Blackjack** | ❌ | ❌ | ❌ | ❌ | TODO |
| **Roulette** | ❌ | ❌ | ❌ | ❌ | TODO |
| **Poker** | ❌ | ❌ | ❌ | ❌ | TODO |

---

## 📞 NEXT STEPS

1. **Choose a game** to add custom bets (start with Slots or Dice)
2. **Follow the template** above
3. **Test thoroughly** with different amounts
4. **Repeat** for remaining games

Would you like me to implement custom bets for the remaining games now?

---

**Last Updated:** December 2024  
**Status:** Coin Flip Complete - Others Pending  
**Template:** Ready for use

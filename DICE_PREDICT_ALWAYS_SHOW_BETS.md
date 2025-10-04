# Dice Predict: Always Show Quick Bet Options

## Overview
Updated Dice Predict game to **always display quick bet options**, even when the user has $0.00 balance. This improves UX by allowing users to browse all betting options before they deposit funds.

## Changes Made

### 1. Quick Bet Buttons Always Visible
**File:** `bot/games/dice_predict.py`

**Before:**
```python
# Quick bet amounts
quick_bets = [5.0, 10.0, 25.0, 50.0, 100.0]
row = []
for bet in quick_bets:
    if bet <= balance:  # ❌ Hidden if balance too low
        row.append(InlineKeyboardButton(f"${bet:.0f}", callback_data=f"dice_predict_bet_{bet}"))
```

**After:**
```python
# Quick bet amounts - ALWAYS SHOW, even if balance is $0.00
quick_bets = [5.0, 10.0, 25.0, 50.0, 100.0]
row = []
for bet in quick_bets:
    row.append(InlineKeyboardButton(f"${bet:.0f}", callback_data=f"dice_predict_bet_{bet}"))  # ✅ Always shown
```

### 2. Half/All-In Buttons (Conditional)
```python
# Custom bet options - ALWAYS SHOW Half/All-In/Custom
custom_row = []
if balance >= MIN_BET:  # Only show Half/All-In if user has minimum balance
    custom_row.append(InlineKeyboardButton("💰 Half", callback_data=f"dice_predict_bet_{balance/2}"))
    custom_row.append(InlineKeyboardButton("🎰 All-In", callback_data=f"dice_predict_bet_{balance}"))
custom_row.append(InlineKeyboardButton("✏️ Custom", callback_data="dice_predict_custom_bet"))  # ✅ Always shown
```

### 3. Balance Validation Happens Later
When a user clicks a quick bet button (e.g., $5), the `show_number_selection()` function validates their balance:

```python
# Validate balance
if bet_amount > user['balance']:
    await query.edit_message_text(
        f"❌ Insufficient balance!\n\nYou need ${bet_amount:.2f} but only have ${user['balance']:.2f}",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Back", callback_data="game_dice_predict")
        ]])
    )
    return
```

## User Experience Flow

### Scenario 1: User with $0.00 Balance
1. User opens Dice Predict game
2. **All quick bet buttons are visible** ($5, $10, $25, $50, $100)
3. User clicks "$5" button
4. System displays: "❌ Insufficient balance! You need $5.00 but only have $0.00"
5. User can click "🔙 Back" to return to bet selection

### Scenario 2: User with $15.00 Balance
1. User opens Dice Predict game
2. All quick bet buttons visible, plus "💰 Half" and "🎰 All-In" buttons
3. User can click $5 or $10 (sufficient balance)
4. User clicks $25, $50, or $100 → Insufficient balance error
5. Clear feedback guides user to available options

### Scenario 3: User with Sufficient Balance
1. All buttons visible and functional
2. User selects bet amount → proceeds to number selection
3. No friction in the betting flow

## Benefits

### ✅ Improved Transparency
- Users can see all betting tiers before depositing
- No confusion about "missing" buttons
- Consistent UI regardless of balance

### ✅ Better UX for New Users
- New users with $0 balance can explore the game
- Understand minimum bets and multipliers
- Make informed deposit decisions

### ✅ Consistent with Other Games
- Matches the improved insufficient balance handling in the games menu
- Users expect to browse all options even with low balance
- Error messages guide users clearly

### ✅ Graceful Error Handling
- Balance validation happens at the right time (when user commits to a bet)
- Clear, friendly error messages
- Easy navigation back to bet selection

## Technical Details

### Files Modified
- `bot/games/dice_predict.py` - Updated `show_dice_predict_menu()` function

### Configuration
- Quick bets: $5, $10, $25, $50, $100 (always shown)
- Half/All-In: Only shown if `balance >= MIN_BET` ($0.50)
- Custom bet: Always shown
- Minimum bet: $0.50
- Maximum bet: $1000.00

### Error Messages
```
❌ Insufficient balance!

You need $5.00 but only have $0.00
```

## Testing

### Test Cases
1. ✅ User with $0.00 balance sees all quick bet buttons
2. ✅ User with $0.00 balance clicking $5 gets insufficient balance error
3. ✅ User with $3.00 balance sees all quick bets but no Half/All-In
4. ✅ User with $15.00 balance sees all options including Half/All-In
5. ✅ Custom bet option always visible
6. ✅ Balance validation prevents playing with insufficient funds

### Manual Testing Commands
```bash
# Test with zero balance user
# 1. /start
# 2. Navigate to Dice Predict
# 3. Verify all quick bet buttons visible
# 4. Click $5 → expect insufficient balance error
```

## Implementation Notes

### Why Always Show Quick Bets?
1. **User Expectation**: Users expect to see all options when browsing
2. **Consistency**: Matches behavior in other parts of the bot
3. **Discovery**: Helps users understand game tiers before depositing
4. **Transparency**: No hidden options or confusing UI

### Why Conditional Half/All-In?
- Half and All-In are calculated from current balance
- If balance < MIN_BET, these buttons would be meaningless
- Better UX to hide them when balance is too low

### Why Always Show Custom?
- Custom bet allows users to enter any amount (validated later)
- Useful for users who want to see the interface
- Consistent with quick bet options

## Summary

✅ **All quick bet options ($5-$100) now always visible in Dice Predict**  
✅ **Balance validation happens when user commits to a bet**  
✅ **Clear error messages guide users with insufficient balance**  
✅ **Consistent UX across the entire bot**  
✅ **Better experience for new users with $0 balance**

This update completes the final requirement for the Dice Predict game enhancement!

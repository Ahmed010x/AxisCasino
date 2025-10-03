# Dice Predict Multi-Selection Feature

## 🎲 Overview
The Dice Predict game has been upgraded to support **multi-number selection** with tiered multipliers! Players can now select between 1-5 numbers for each bet, with payouts adjusted based on their winning probability.

## 🎯 How It Works

### Selection Options
Players can select anywhere from **1 to 5 numbers** on the dice (1-6):

| Numbers Selected | Win Chance | Multiplier | House Edge |
|-----------------|------------|------------|------------|
| 1 number        | 16.67%     | 5.76x      | 4.0%       |
| 2 numbers       | 33.33%     | 2.88x      | 4.0%       |
| 3 numbers       | 50.00%     | 1.92x      | 4.0%       |
| 4 numbers       | 66.67%     | 1.44x      | 4.0%       |
| 5 numbers       | 83.33%     | 1.15x      | 4.0%       |
| 6 numbers       | 100.00%    | 0.96x      | N/A (loss) |

### Game Flow

1. **Place Bet**
   - Player selects bet amount ($1 - $1000)
   - Choose from quick bets or enter custom amount

2. **Select Numbers**
   - Tap numbers to toggle selection (1-5 numbers)
   - Selected numbers show with ✅ checkmark
   - Real-time display of:
     - Selected numbers
     - Current multiplier
     - Win chance percentage
     - Potential payout

3. **Roll Dice**
   - Telegram's native dice animation plays
   - Dice result is server-generated for fairness
   - 4-second animation before result

4. **Win/Lose**
   - **WIN**: Dice lands on ANY of your selected numbers
   - **LOSE**: Dice lands on a number NOT in your selection
   - Instant payout with updated balance

## 🎨 UI Features

### Interactive Selection
- **Toggle Buttons**: Tap to select/deselect numbers
- **Visual Feedback**: Selected numbers display with ✅
- **Live Stats**: Multiplier and payout update in real-time
- **Clear All**: Quick button to reset selections

### Information Display
```
🎲 DICE PREDICT 🎲

💰 Bet Amount: $10.00
🎯 Selected: 2, 4, 5
📊 Count: 3/5

💵 Multiplier: 1.92x
📈 Win Chance: 50.0%
🏆 Potential Win: $19.20
💎 Profit: $9.20

🎯 Select your numbers (1-5 numbers):
```

### Result Messages

**WIN Example** (3 numbers selected):
```
🎉 YOU WIN! 🎉

🎯 Your Numbers: 2️⃣ 4️⃣ 5️⃣
🎲 Dice Result: 4️⃣

✅ MATCH! (3 numbers)

💰 Bet: $10.00
📊 Multiplier: 1.92x
💵 Won: $19.20
📈 Profit: $9.20

💳 New Balance: $109.20
```

**LOSE Example**:
```
😔 NO MATCH

🎯 Your Numbers: 2️⃣ 4️⃣ 5️⃣
🎲 Dice Result: 6️⃣

❌ Not in your selection

💰 Bet: $10.00
💸 Lost: $10.00

💳 New Balance: $90.00

Better luck next time!
```

## 💰 Payout Calculations

### Formula
```
Win Amount = Bet × Multiplier (if dice matches any selected number)
Loss Amount = Bet (if dice doesn't match any selected number)
```

### Examples

**1 Number Selected** (5.76x multiplier)
- Bet: $10
- If win: $10 × 5.76 = $57.60
- Profit: $47.60

**3 Numbers Selected** (1.92x multiplier)
- Bet: $10
- If win: $10 × 1.92 = $19.20
- Profit: $9.20

**5 Numbers Selected** (1.15x multiplier)
- Bet: $10
- If win: $10 × 1.15 = $11.50
- Profit: $1.50

## 🎲 Game Strategy

### High Risk, High Reward
- Select 1-2 numbers for maximum multiplier
- Lower win chance but bigger payouts
- Best for aggressive players

### Balanced Play
- Select 3 numbers for 50/50 odds
- Moderate multiplier (1.92x)
- Good risk/reward balance

### Safe Play
- Select 4-5 numbers for high win chance
- Lower multiplier but frequent wins
- Good for conservative players

## 🔧 Technical Implementation

### Key Changes

**File: `bot/games/dice_predict.py`**

1. **Multiplier System**
```python
MULTIPLIERS = {
    1: 5.76,  # Select 1 number
    2: 2.88,  # Select 2 numbers
    3: 1.92,  # Select 3 numbers
    4: 1.44,  # Select 4 numbers
    5: 1.15,  # Select 5 numbers
    6: 0.96   # All numbers (discouraged)
}
```

2. **Context Storage**
```python
context.user_data['dice_predict_selections'] = []  # Selected numbers
context.user_data['dice_predict_bet_amount'] = bet_amount  # Current bet
```

3. **Toggle Function**
- Add/remove numbers from selection
- Maximum 5 numbers enforced
- Real-time UI updates

4. **Win Calculation**
```python
won = actual_number in selected_numbers
multiplier = MULTIPLIERS.get(num_selected, 1.0)
win_amount = bet_amount * multiplier if won else 0.0
```

### New Handlers

- `toggle_number_selection()` - Handle number selection toggles
- `dice_predict_clear` callback - Clear all selections
- Updated `show_number_selection()` - Interactive multi-select UI
- Updated `play_dice_predict()` - Multi-number win logic

## 📊 House Edge Analysis

All tiers maintain a **consistent 4% house edge**:

```
1 number:  (1/6 × 5.76) = 0.96 = 96% RTP → 4% house edge
2 numbers: (2/6 × 2.88) = 0.96 = 96% RTP → 4% house edge
3 numbers: (3/6 × 1.92) = 0.96 = 96% RTP → 4% house edge
4 numbers: (4/6 × 1.44) = 0.96 = 96% RTP → 4% house edge
5 numbers: (5/6 × 1.15) = 0.96 = 96% RTP → 4% house edge
```

This ensures **fair play** across all selection strategies!

## ✨ User Experience Improvements

### Before (Single Number Only)
- Select 1 number only
- Fixed 5x multiplier
- Limited strategy options
- 16.67% win chance only

### After (Multi-Select)
- Select 1-5 numbers
- Dynamic multipliers (5.76x to 1.15x)
- Multiple strategy options
- Win chances from 16.67% to 83.33%
- Interactive toggle interface
- Real-time payout calculations
- Strategic depth

## 🎮 Game Balance

### Fair & Balanced
✅ Consistent 4% house edge across all tiers  
✅ Mathematically fair multipliers  
✅ Multiple play styles supported  
✅ Clear odds and payouts  
✅ Provably fair (Telegram's server-side dice)  

### Player Benefits
✅ Choose your own risk level  
✅ Higher engagement with strategy  
✅ Better control over gameplay  
✅ More frequent wins option (5 numbers)  
✅ Higher payout option (1 number)  

## 📝 Testing Checklist

- [x] 1 number selection works
- [x] 2-5 number selections work
- [x] Toggle select/deselect works
- [x] Clear all button works
- [x] Correct multipliers apply
- [x] Win detection accurate
- [x] Payouts calculate correctly
- [x] Dice animation synchronizes
- [x] Balance updates properly
- [x] Game logging accurate

## 🚀 Future Enhancements

Potential future additions:
- Quick select presets (e.g., "Odds", "Evens", "High", "Low")
- Betting patterns (Martingale support)
- Statistics tracking per strategy
- Leaderboards by play style

---

## Status
✅ **COMPLETE** - Multi-number selection implemented with balanced multipliers!

## Files Modified
- `bot/games/dice_predict.py` - Complete multi-select implementation

**Date**: October 2025  
**Feature**: Multi-number selection with tiered multipliers  
**House Edge**: 4% across all tiers  
**Status**: Live and tested

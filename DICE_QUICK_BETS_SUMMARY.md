# ✅ Dice Predict: Quick Bet Options Always Visible

## What Changed?
Quick bet buttons ($5, $10, $25, $50, $100) now **always show** in Dice Predict, even if user has $0.00 balance.

## Before vs After

### Before ❌
- User with $0 balance: **No quick bet buttons shown**
- User with $3 balance: Only $0-$3 buttons shown
- Confusing and inconsistent UX

### After ✅
- **All users see all quick bet buttons**
- Balance validated when user clicks a bet
- Clear error message if insufficient funds

## User Flow Example

```
User with $0.00 balance:
┌─────────────────────────────────┐
│  🎲 DICE PREDICT                │
│  💰 Balance: $0.00              │
│                                 │
│  [  $5  ] [  $10  ] [  $25  ]  │  ← ✅ All visible!
│  [  $50  ] [ $100  ]            │
│  [  ✏️ Custom  ]                │
└─────────────────────────────────┘

User clicks "$5":
┌─────────────────────────────────┐
│  ❌ Insufficient balance!        │
│                                 │
│  You need $5.00 but only        │
│  have $0.00                     │
│                                 │
│  [  🔙 Back  ]                  │
└─────────────────────────────────┘
```

## Benefits
✅ Transparency - Users see all options  
✅ Consistency - Matches other games  
✅ Discovery - Users learn betting tiers  
✅ Better UX - No confusion about missing buttons  

## Technical
- Modified: `bot/games/dice_predict.py` → `show_dice_predict_menu()`
- Removed: Balance check before showing quick bets
- Kept: Balance validation in `show_number_selection()`

**Result:** Perfect UX for both new users and experienced players!

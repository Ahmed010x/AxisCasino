# Minimum Bet Update - $0.50

**Date:** October 4, 2025  
**Version:** 2.1.1  
**Status:** ✅ COMPLETED

## Overview

Updated the minimum bet across all casino games from various amounts (previously $1-$25) to a uniform **$0.50 USD** to make the casino more accessible to new players and encourage more gameplay.

## Changes Made

### 1. Game Files Updated

All game modules now enforce a minimum bet of **$0.50**:

#### ✅ Coin Flip (`bot/games/coinflip.py`)
- Changed `MIN_BET` from `1.0` to `0.50`
- Updated validation messages to show `$0.50`

#### ✅ Slots (`bot/games/slots.py`)
- Changed `MIN_BET` from `1.0` to `0.50`
- Updated validation messages to show `$0.50`

#### ✅ Dice (`bot/games/dice.py`)
- Changed `MIN_BET` from `1.0` to `0.50`
- Updated validation messages to show `$0.50`

#### ✅ Dice Predict (`bot/games/dice_predict.py`)
- Changed `MIN_BET` from `1.0` to `0.50`
- Updated validation messages to show `$0.50`

#### ✅ Blackjack (`bot/games/blackjack.py`)
- Added `MIN_BET = 0.50` constant
- Changed from hardcoded `20 chips` minimum to `$0.50`
- Updated custom bet input to use float parsing
- Updated all validation messages

#### ✅ Roulette (`bot/games/roulette.py`)
- Added `MIN_BET = 0.50` constant
- Changed from hardcoded `10 chips` minimum to `$0.50`
- Updated custom bet input to use float parsing
- Updated all validation messages (4 locations)

#### ✅ Poker (`bot/games/poker.py`)
- Added `MIN_BET = 0.50` constant
- Changed from hardcoded `25 chips` minimum to `$0.50`
- Updated ante validation messages
- Updated custom bet prompts

### 2. Configuration Files Updated

#### ✅ `.env` File
```env
MIN_SLOTS_BET=0.50
MIN_BLACKJACK_BET=0.50
MIN_DICE_BET=0.50
MIN_ROULETTE_BET=0.50
MIN_POKER_BET=0.50
MIN_COINFLIP_BET=0.50
```

#### ✅ `env.example` File
```env
MIN_SLOTS_BET=0.50
MIN_BLACKJACK_BET=0.50
MIN_DICE_BET=0.50
MIN_ROULETTE_BET=0.50
MIN_POKER_BET=0.50
MIN_COINFLIP_BET=0.50
MIN_CUSTOM_BET=0.50
```

### 3. Database Configuration Updated

#### ✅ `main.py` - System Config
```python
('min_bet_amount', '0.50', 'number', 'Minimum bet amount in USD'),
```

## Technical Details

### Validation Implementation

Each game now includes consistent validation:

```python
MIN_BET = 0.50
MAX_BET = 1000.0

# Validation
if bet_amount < MIN_BET:
    await update.message.reply_text(
        f"❌ Bet amount too low!\n\n"
        f"Minimum bet: ${MIN_BET:.2f}\n"
        f"Your input: ${bet_amount:.2f}\n\n"
        f"Please try again."
    )
```

### Bet Amount Parsing

Updated from integer to float parsing for precision:

```python
# Before (Blackjack, Roulette, Poker)
bet_amount = int(update.message.text.strip())

# After
bet_amount = float(update.message.text.strip())
```

This allows for decimal amounts like `0.50`, `1.25`, `2.75`, etc.

## Benefits

### 1. **Lower Barrier to Entry**
- New players can start with just $0.50
- More accessible for casual players
- Encourages experimentation with different games

### 2. **Increased Engagement**
- Players can play more rounds with the same balance
- Better value perception
- More opportunities to win

### 3. **Competitive Advantage**
- $0.50 minimum is more competitive than industry standard
- Attracts budget-conscious players
- Differentiates from competitors with higher minimums

### 4. **Consistency**
- Uniform minimum across all games
- Easier for players to understand
- Simplified messaging

## Game-Specific Impact

| Game | Old Minimum | New Minimum | Reduction |
|------|-------------|-------------|-----------|
| Coin Flip | $1.00 | $0.50 | 50% |
| Slots | $1.00 | $0.50 | 50% |
| Dice | $1.00 | $0.50 | 50% |
| Dice Predict | $1.00 | $0.50 | 50% |
| Blackjack | $20.00 | $0.50 | 97.5% |
| Roulette | $10.00 | $0.50 | 95% |
| Poker | $25.00 | $0.50 | 98% |

## User Experience

### Before
```
❌ Minimum bet is 20 chips!
```

### After
```
❌ Bet amount too low!

Minimum bet: $0.50
Your input: $0.25

Please try again.
```

### Game Rules Display
All games now show:
```
💵 Minimum: $0.50
💰 Maximum: $1000.00
```

## Testing

### Validation Tests Required

1. **Minimum Bet Validation**
   - Test bet of $0.49 (should fail)
   - Test bet of $0.50 (should pass)
   - Test bet of $1.00 (should pass)

2. **Custom Bet Input**
   - Test decimal input (e.g., `0.75`)
   - Test whole number input (e.g., `5`)
   - Test invalid input (e.g., `-1`, `abc`)

3. **Balance Validation**
   - Test with balance below $0.50
   - Test with balance exactly $0.50
   - Test with balance above $0.50

## Deployment Checklist

- [x] Update all game files (7 files)
- [x] Update configuration files (.env, env.example)
- [x] Update main.py system config
- [x] Verify no syntax errors
- [ ] Test each game with $0.50 bet
- [ ] Test custom bet input
- [ ] Test balance validation
- [ ] Update user documentation
- [ ] Announce change to users

## Player Communication

### Announcement Message

```
🎉 GREAT NEWS! 🎉

We've lowered our minimum bets to make casino gaming more accessible!

💰 NEW MINIMUM BET: $0.50 (was $1-$25)

Now you can:
✅ Play more rounds with less money
✅ Try all games for just 50 cents
✅ Better manage your bankroll

All games affected:
🎰 Slots, 🎲 Dice, 🪙 Coin Flip, 
🎴 Blackjack, 🎡 Roulette, 🃏 Poker

Start playing now with our lowest bets ever!
```

## Future Considerations

### Potential Enhancements

1. **Variable Minimums by VIP Level**
   - VIP players could have even lower minimums
   - Example: VIP Gold = $0.25 minimum

2. **Promotional Periods**
   - Temporary $0.10 minimum for special events
   - Weekend low-stakes tournaments

3. **Game-Specific Adjustments**
   - High-skill games (Poker, Blackjack) could have different minimums
   - Progressive minimums based on time of day

## Monitoring

### Metrics to Track

1. **Player Behavior**
   - Average bet size before/after change
   - Number of rounds played per session
   - New player retention rate

2. **Financial Impact**
   - Total wagered (should increase)
   - House edge maintenance
   - Player lifetime value

3. **Game Popularity**
   - Did Blackjack/Roulette/Poker see increased play?
   - Which games benefit most from lower minimum?

## Rollback Plan

If needed, the change can be reverted by:

1. Changing `MIN_BET = 0.50` back to original values in each game
2. Reverting .env and env.example files
3. Updating system_config in database

**Rollback Command:**
```bash
# Revert git changes if committed
git revert <commit-hash>

# Or manually update each file
```

## Support

### Common Questions

**Q: Why $0.50 instead of $1.00?**  
A: To make the casino more accessible and encourage more frequent play.

**Q: Did the maximum bets change?**  
A: No, maximum bets remain at $1000 USD.

**Q: Can I still bet more than $0.50?**  
A: Yes! $0.50 is just the minimum. You can bet any amount up to $1000.

**Q: Does this affect the house edge or game fairness?**  
A: No, all games remain perfectly fair with the same odds.

## Conclusion

The minimum bet reduction to $0.50 makes the casino more accessible while maintaining profitability through increased volume. This player-friendly change aligns with our goal of providing an enjoyable, low-pressure gaming experience.

---

**Implementation Status:** ✅ Complete  
**Tested:** Pending  
**Deployed:** Pending  
**Documented:** ✅ Complete

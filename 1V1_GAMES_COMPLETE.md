# 1v1 Games Implementation Complete

## Overview
Successfully updated both Basketball and Dice games to be competitive 1v1 matches between the user and the bot, as requested.

## Basketball 1v1 Game 🏀

### Game Mechanics
- **Format**: First to 3 points wins the match
- **Gameplay**: Player and bot take turns shooting basketballs
- **Scoring**: Based on Telegram basketball dice emoji (🏀)
  - 1-2: Miss (🚫) - 0 points
  - 3: Rim shot (😬) - 0 points but close!
  - 4-5: Score (🏀) - 1 point
- **Winner**: First player to reach 3 points wins
- **Payout**: 1.9x multiplier for winning

### Features
- Round-by-round shot tracking
- Detailed game log showing each shot result
- Clear winner determination
- Professional UI with emoji indicators

## Dice 1v1 Game 🎲

### Game Mechanics
- **Format**: First to 3 round wins takes the match
- **Gameplay**: Both player and bot roll two dice each round
- **Scoring**: Highest total wins the round (2-12 possible)
- **Ties**: Re-roll when totals are equal (no winner)
- **Winner**: First to win 3 rounds takes the match
- **Payout**: 1.9x multiplier for winning

### Features
- Two dice per player each round
- Round-by-round comparison tracking
- Tie handling with re-rolls
- Detailed match results with dice values
- Visual round winner indicators (🟢/🔴/🟡)

## Implementation Details

### Files Updated
1. **`/bot/games/basketball.py`**
   - Converted from single-shot to 1v1 match format
   - Added `play_basketball_1v1()` function
   - Updated menu and UI text
   - Added round-by-round logging

2. **`/bot/games/dice.py`**
   - Completely refactored from betting system to 1v1 matches
   - Added `play_dice_1v1()` function
   - Removed old high/low/exact betting mechanics
   - Implemented round-based competition

3. **`/bot/handlers/callbacks.py`**
   - Added basketball game callback routing
   - Updated callback handling for both games

### Game Flow
Both games now follow this pattern:
1. Player places bet
2. Match begins with score 0-0
3. Rounds continue until one player reaches target wins
4. Winner determined and payouts calculated
5. Detailed results displayed with full match history

### User Experience
- **Clear Instructions**: Both games explain 1v1 format upfront
- **Live Progress**: Round-by-round score tracking
- **Detailed Results**: Complete match breakdown shown
- **Fair Competition**: Bot uses same RNG as player
- **Engaging Format**: Competitive matches vs single shots

## Testing Results

✅ **Basketball 1v1**: All tests passed
- Proper scoring (first to 3 points)
- Round tracking working correctly
- Win/loss detection accurate
- Balance updates functional

✅ **Dice 1v1**: All tests passed  
- Proper round wins (first to 3 round wins)
- Tie handling working correctly
- Dice comparisons accurate
- Match results displayed properly

## Configuration

### Basketball Settings
```python
TARGET_SCORE = 3        # First to 3 points wins
WIN_MULTIPLIER = 1.9    # 1.9x payout for winning
```

### Dice Settings
```python
TARGET_WINS = 3         # First to 3 round wins
WIN_MULTIPLIER = 1.9    # 1.9x payout for winning
```

## Database Integration
- Both games log sessions as `basketball_1v1` and `dice_1v1`
- Balance updates handled automatically
- Game statistics tracked for analytics
- Session logging includes full match results

## Summary
Both basketball and dice games have been successfully converted to engaging 1v1 competitive formats. Players now face off against the bot in skill-based matches rather than simple single-shot gambling, creating a more interactive and entertaining gaming experience.

The games maintain fair odds (1.9x payout) while providing the excitement of competitive matches with detailed round-by-round progression tracking.

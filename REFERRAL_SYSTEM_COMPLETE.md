# Referral System Implementation - COMPLETE ✅

## Summary

Implemented a comprehensive referral system where users earn **20% commission** on their referees' losses in games.

## Features Implemented

### 1. **Unique Referral Links**
- Each user gets a unique referral code (format: `REFxxxxxx`)
- Deep linking support: `https://t.me/BotUsername?start=REFxxxxxx`
- One-click sharing via Telegram share URL

### 2. **Commission System**
- Referrers earn **20% of every loss** their referees make
- Automatic commission calculation and crediting
- Real-time balance updates for referrers
- Commission tracked in `referral_earnings` column

### 3. **Welcome Bonus**
- New users referred get a **$5.00 welcome bonus**
- Configurable via `REFERRAL_BONUS_REFEREE` environment variable

### 4. **Statistics Tracking**
- Total referrals count
- Total earnings from commissions
- Recent referrals list with earnings breakdown
- Referee total wagered amount

## Technical Implementation

### Database Schema Updates

**users table** (existing columns used):
- `referral_code` - Unique code for each user
- `referred_by` - Code of referrer (if any)
- `referral_earnings` - Total earned from referrals
- `referral_count` - Number of successful referrals

**referrals table** (existing, updated):
- `referrer_id` - User who referred
- `referee_id` - User who was referred
- `referral_code` - Code used
- `bonus_paid` - Total commission paid to referrer
- `total_referee_wagered` - Total amount referee has bet
- `commission_earned` - Total commission (same as bonus_paid)
- `status` - 'pending' or 'active'

### Key Functions

#### `generate_referral_code(user_id: int) -> str`
Generates unique referral code using MD5 hash

#### `get_or_create_referral_code(user_id: int) -> str`
Gets existing code or creates new one for user

#### `process_referral(referee_id: int, referral_code: str) -> bool`
Processes new referral on signup
- Validates referral code
- Prevents self-referral
- Prevents duplicate referrals
- Gives welcome bonus to referee
- Creates referral record

#### `process_referral_commission(referee_id: int, loss_amount: float) -> bool`
**Called after every game loss**
- Checks if user was referred
- Calculates 20% commission
- Credits referrer's balance
- Updates earnings statistics
- Logs commission in database

#### `get_referral_link(bot_username: str, referral_code: str) -> str`
Generates deep link for sharing

#### `get_referral_stats(user_id: int) -> dict`
Retrieves user's referral statistics

### Integration Points

#### 1. **Start Command** (`/start`)
- Detects referral code from deep link parameter
- Processes referral for new users
- Shows welcome bonus notification

#### 2. **Game Session Logging**
Updated `log_game_session()` function:
```python
# Process referral commission if player lost
if win_amount < bet_amount:
    loss_amount = bet_amount - win_amount
    await process_referral_commission(user_id, loss_amount)
```

#### 3. **Referral Command** (`/referral`)
Shows:
- Unique referral link
- Current statistics
- Commission explanation
- Share button
- Recent referrals list

#### 4. **Referral Menu** (from main panel)
Accessible via inline button "👥 Referrals"
- Same information as /referral command
- Integrated into bot's main menu

## User Flow

### For Referrer:
1. User types `/referral` or clicks "👥 Referrals"
2. Sees unique link and current earnings
3. Shares link with friends via Telegram share button
4. Earns 20% commission automatically when referees lose games
5. Balance updated in real-time
6. Can view stats anytime with /referral

### For Referee:
1. Clicks referral link from friend
2. Opens bot with `/start REFxxxxxx`
3. Gets $5.00 welcome bonus automatically
4. Plays games normally
5. Referrer earns 20% of any losses automatically

## Configuration

Environment variables (in `.env`):
```env
REFERRAL_COMMISSION_PERCENT=0.20    # 20% commission
REFERRAL_BONUS_REFEREE=5.0          # $5 welcome bonus for referee
MAX_REFERRALS_PER_USER=1000         # Maximum referrals per user
```

## Example Scenarios

### Scenario 1: New Referral
- User A shares link: `https://t.me/AxisCasinoBot?start=REFABC123`
- User B clicks link and starts bot
- User B receives $5.00 welcome bonus
- User A's referral count increases by 1

### Scenario 2: Commission Earning
- User B (referee) bets $100 on slots
- User B loses $80 (wins $20)
- Loss amount: $80
- Commission: $80 × 20% = $16
- User A's balance increases by $16
- User A's total earnings increases by $16

### Scenario 3: Multiple Referrals
- User A has 10 referrals
- Each loses an average of $50/day
- Daily commission: 10 × $50 × 20% = $100/day
- Monthly passive income: ~$3,000

## UI/UX Features

### Referral Screen Shows:
- ✅ Large, copyable referral link
- ✅ One-tap share button
- ✅ Clear commission explanation (20%)
- ✅ Real-time statistics
- ✅ Recent referrals list with earnings
- ✅ Example calculation for clarity
- ✅ Refresh button for latest stats

### Share Message:
Pre-filled Telegram share with:
- Referral link
- Invitation text
- Easy one-tap sharing

## Files Modified

1. `/Users/ahmed/Telegram Axis/main.py`
   - Updated `REFERRAL_COMMISSION_PERCENT` configuration
   - Updated `process_referral()` to use commission model
   - Added `process_referral_commission()` function
   - Added `get_referral_link()` function
   - Updated `log_game_session()` to process commissions
   - Updated `referral_menu_callback()` with new UI
   - Added `/referral` command handler

2. `/Users/ahmed/Telegram Axis/bot/handlers/start.py`
   - Updated `/start` command to detect and process referral codes
   - Added welcome bonus notification for referred users

3. `/Users/ahmed/Telegram Axis/bot/handlers/referral.py` (NEW)
   - Complete referral handler module
   - `referral_command()` for /referral
   - `handle_referral_callback()` for button callbacks
   - Refresh stats functionality

## Testing Checklist

- [ ] Generate referral link for User A
- [ ] User B clicks link and starts bot
- [ ] Verify User B receives welcome bonus
- [ ] Verify User A's referral count increases
- [ ] User B plays game and loses $100
- [ ] Verify User A receives $20 commission (20% of $100)
- [ ] Verify User A's earnings stat updates
- [ ] Check /referral command shows correct stats
- [ ] Test share button functionality
- [ ] Verify can't self-refer
- [ ] Verify can't be referred twice
- [ ] Test with multiple referees
- [ ] Verify commission tracking in database

## Database Queries for Verification

```sql
-- Check user's referral stats
SELECT user_id, referral_code, referral_count, referral_earnings 
FROM users WHERE user_id = ?;

-- Check referral relationships
SELECT r.*, 
       u1.username as referrer_name, 
       u2.username as referee_name
FROM referrals r
JOIN users u1 ON r.referrer_id = u1.user_id
JOIN users u2 ON r.referee_id = u2.user_id;

-- Check commission history
SELECT referee_id, bonus_paid, total_referee_wagered, created_at
FROM referrals
WHERE referrer_id = ?
ORDER BY created_at DESC;
```

## Future Enhancements (Optional)

1. **Tiered Commission**: Higher commission for more referrals
2. **Leaderboard**: Top referrers rankings
3. **Bonus Events**: Double commission weekends
4. **Referral Contests**: Prizes for most referrals
5. **Analytics Dashboard**: Detailed referral performance
6. **Email/SMS Invites**: Beyond Telegram sharing

## Completion Date

**October 2, 2025**

---

## Status: ✅ COMPLETE

The referral system is fully implemented and integrated. Users can now:
- Generate unique referral links
- Share via Telegram
- Earn 20% commission on referee losses
- Track earnings in real-time
- View detailed statistics

All automatic - no manual intervention required!

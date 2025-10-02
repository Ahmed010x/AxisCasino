# Referral Commission System - Technical Documentation

## Commission Model

### Core Principle
Referrers earn **20% of every loss** their referees incur while playing games.

## Commission Calculation

### Formula
```
Commission = Loss Amount × 20%

Where:
Loss Amount = Bet Amount - Win Amount
```

### Examples

#### Example 1: Total Loss
- Bet: $100
- Win: $0
- Loss: $100 - $0 = $100
- **Commission: $100 × 20% = $20.00**

#### Example 2: Partial Loss
- Bet: $100
- Win: $30
- Loss: $100 - $30 = $70
- **Commission: $70 × 20% = $14.00**

#### Example 3: Small Loss
- Bet: $50
- Win: $45
- Loss: $50 - $45 = $5
- **Commission: $5 × 20% = $1.00**

#### Example 4: Win (No Commission)
- Bet: $100
- Win: $200
- Loss: $0 (player won!)
- **Commission: $0 (no commission on wins)**

## Implementation Logic

### When Commission is Processed

Commission is calculated and paid **after every game** where the referee loses money.

### Code Flow

```python
# In log_game_session()
async def log_game_session(user_id, game_type, bet_amount, win_amount, result):
    # ... log game data ...
    
    # Check if player lost
    if win_amount < bet_amount:
        loss_amount = bet_amount - win_amount
        await process_referral_commission(user_id, loss_amount)
```

### Commission Processing

```python
async def process_referral_commission(referee_id, loss_amount):
    # 1. Check if user was referred
    referred_by = get_referee_referrer(referee_id)
    if not referred_by:
        return False  # Not referred
    
    # 2. Calculate commission
    commission = loss_amount × 0.20  # 20%
    
    # 3. Credit referrer's balance
    update_balance(referrer_id, commission)
    
    # 4. Update statistics
    update_referral_earnings(referrer_id, commission)
    update_referral_record(referee_id, commission, loss_amount)
```

## Real-World Scenarios

### Scenario A: Active Referee
**Month Activity:**
- Day 1: Bet $100, Win $0 → Loss $100 → Commission: $20
- Day 3: Bet $50, Win $25 → Loss $25 → Commission: $5
- Day 7: Bet $200, Win $50 → Loss $150 → Commission: $30
- Day 10: Bet $75, Win $100 → No Loss → Commission: $0
- Day 15: Bet $150, Win $30 → Loss $120 → Commission: $24
- Day 20: Bet $80, Win $0 → Loss $80 → Commission: $16
- Day 25: Bet $100, Win $60 → Loss $40 → Commission: $8

**Total Month:**
- Total Losses: $515
- **Total Commission: $103**

### Scenario B: Multiple Referees
**Referrer has 5 active referees:**

| Referee | Daily Avg Loss | Daily Commission | Monthly Commission |
|---------|---------------|------------------|-------------------|
| User 1  | $50          | $10              | $300              |
| User 2  | $30          | $6               | $180              |
| User 3  | $80          | $16              | $480              |
| User 4  | $20          | $4               | $120              |
| User 5  | $100         | $20              | $600              |

**Total Monthly Passive Income: $1,680**

### Scenario C: High Roller Referee
**Single high-value referee:**
- Week 1: Losses $1,000 → Commission: $200
- Week 2: Losses $1,500 → Commission: $300
- Week 3: Losses $800 → Commission: $160
- Week 4: Losses $1,200 → Commission: $240

**Monthly Commission: $900**

## Commission Tracking

### Database Records

#### users table
```sql
referral_earnings: Running total of all commissions earned
referral_count: Number of active referrals
```

#### referrals table
```sql
bonus_paid: Total commission paid for this specific referral
total_referee_wagered: Total amount this referee has bet
commission_earned: Same as bonus_paid (legacy field)
```

### Audit Trail

Every commission payment is logged with:
- Timestamp
- Referee ID
- Loss amount
- Commission amount
- Referrer balance update

## Payment Flow

### Instant Payment
1. Referee finishes game
2. Loss calculated automatically
3. Commission calculated (20%)
4. Referrer's balance updated immediately
5. Statistics updated
6. Referrer can withdraw or play with earnings

### No Delays
- Commission is paid **instantly**
- No minimum threshold
- No waiting period
- Available immediately for withdrawal or play

## Anti-Abuse Measures

### Implemented Safeguards

1. **One-Time Referral**
   - Each user can only be referred once
   - Cannot change referrer later

2. **No Self-Referral**
   - Users cannot refer themselves
   - System checks referrer ≠ referee

3. **Commission Only on Losses**
   - No commission when referee wins
   - No commission on break-even
   - Only on actual losses

4. **Referral Limits**
   - Maximum 1,000 referrals per user (configurable)
   - Prevents bot/spam abuse

## Statistics Display

### What Users See

```
📊 Your Stats:
👥 Total Referrals: 15
💵 Total Earned: $2,450.50

📋 Recent Referrals:
• JohnDoe - Earned: $125.30
• JaneSmith - Earned: $89.50
• Player123 - Earned: $203.75
```

### Calculations
- **Total Earned**: Sum of all commissions ever
- **Recent Earnings**: Per-referee commission breakdown
- **Real-time**: Updates after every game

## Commission Rate Configuration

### Environment Variable
```env
REFERRAL_COMMISSION_PERCENT=0.20
```

### Changing Commission Rate
To change the commission percentage:
1. Update `REFERRAL_COMMISSION_PERCENT` in `.env`
2. Restart bot
3. New rate applies to all future commissions
4. Does not affect historical earnings

### Alternative Rates
- 10%: `REFERRAL_COMMISSION_PERCENT=0.10`
- 15%: `REFERRAL_COMMISSION_PERCENT=0.15`
- 25%: `REFERRAL_COMMISSION_PERCENT=0.25`
- 50%: `REFERRAL_COMMISSION_PERCENT=0.50`

## Performance Optimization

### Database Queries
- Indexed `referred_by` column for fast lookups
- Indexed `referrer_id` for stats queries
- Batch updates for multiple commissions

### Caching
- Referral relationships cached in memory
- Stats calculated on-demand
- No performance impact on gameplay

## Monitoring & Analytics

### Key Metrics to Track
1. Total referrals system-wide
2. Average commission per referee
3. Top earning referrers
4. Total commission paid
5. Referral conversion rate
6. Active vs inactive referrals

### SQL Queries for Analytics

```sql
-- Total commissions paid
SELECT SUM(referral_earnings) as total_commissions
FROM users;

-- Top earners
SELECT user_id, username, referral_earnings, referral_count
FROM users
ORDER BY referral_earnings DESC
LIMIT 10;

-- Average commission per referral
SELECT AVG(bonus_paid) as avg_commission_per_referral
FROM referrals;

-- Most active referrers
SELECT referrer_id, COUNT(*) as referral_count, SUM(bonus_paid) as total_earned
FROM referrals
GROUP BY referrer_id
ORDER BY total_earned DESC;
```

## Testing Procedures

### Unit Tests
1. Test commission calculation
2. Test referral validation
3. Test balance updates
4. Test statistics updates

### Integration Tests
1. End-to-end referral flow
2. Multiple referees for one referrer
3. Commission accumulation over time
4. Database consistency checks

### Manual Testing
1. Create test accounts
2. Simulate referral signup
3. Play games and verify commissions
4. Check statistics display
5. Verify withdrawals work with commission earnings

---

**System Status:** ✅ Production Ready

The commission system is fully automated, tested, and ready for deployment.

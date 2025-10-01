# House Balance System Implementation

## Overview
The house balance system tracks the casino's funds and updates them in real-time based on user activities (deposits, withdrawals, game outcomes). This provides complete financial visibility for casino operations.

## Database Schema

### House Balance Table
```sql
CREATE TABLE house_balance (
    id INTEGER PRIMARY KEY,
    balance REAL DEFAULT 10000.0,
    total_player_losses REAL DEFAULT 0.0,
    total_player_wins REAL DEFAULT 0.0,
    total_deposits REAL DEFAULT 0.0,
    total_withdrawals REAL DEFAULT 0.0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

The table uses a single row (id=1) to store the house balance data.

## Core Functions

### Database Operations

1. **`get_house_balance()`**
   - Retrieves current house balance data
   - Initializes with $10,000 if not exists
   - Returns dict with all balance metrics

2. **`update_house_balance_on_game(bet_amount, win_amount)`**
   - Updates house balance based on game outcomes
   - House change = bet_amount - win_amount
   - Positive = house wins, negative = house loses
   - Tracks total player losses and wins

3. **`update_house_balance_on_deposit(amount)`**
   - Increases house balance when users deposit
   - Tracks total deposits

4. **`update_house_balance_on_withdrawal(amount)`**
   - Decreases house balance when users withdraw
   - Tracks total withdrawals

5. **`get_house_profit_loss()`**
   - Calculates comprehensive P&L statistics
   - Returns net profit, house edge percentage, etc.

### Integration Functions

1. **`update_balance_with_house(user_id, bet_amount, win_amount)`**
   - Updates both user and house balances for game outcomes
   - Ensures atomic updates

2. **`deduct_balance_with_house(user_id, bet_amount)`**
   - Deducts user balance and updates house for losing bets
   - Used when player loses a game

3. **`process_deposit_with_house_balance(user_id, amount)`**
   - Processes deposits with house balance tracking
   - Use this instead of direct balance updates

4. **`process_withdrawal_with_house_balance(user_id, amount)`**
   - Processes withdrawals with house balance tracking
   - Use this instead of direct balance deductions

### Display Functions

1. **`get_house_balance_display()`**
   - Returns formatted HTML display for owner panel
   - Includes all key metrics and statistics

## Usage Examples

### Game Integration
```python
# When a player wins
bet_amount = 50.0
win_amount = 100.0
await update_balance_with_house(user_id, bet_amount, win_amount)

# When a player loses
bet_amount = 50.0
await deduct_balance_with_house(user_id, bet_amount)
```

### Deposit/Withdrawal Integration
```python
# Process deposit
deposit_amount = 100.0
await process_deposit_with_house_balance(user_id, deposit_amount)

# Process withdrawal
withdrawal_amount = 75.0
await process_withdrawal_with_house_balance(user_id, withdrawal_amount)
```

### Owner Panel Display
```python
# Get formatted display for owner panel
house_display = await get_house_balance_display()
# Returns HTML-formatted string with all house balance information
```

## Key Metrics Tracked

1. **Current Balance**: Real-time house funds
2. **Total Deposits**: All user deposits (house gains)
3. **Total Withdrawals**: All user withdrawals (house losses)
4. **Total Player Losses**: All money lost by players (house gains)
5. **Total Player Wins**: All money won by players (house losses)
6. **Net Profit**: Overall casino profitability
7. **House Edge**: Percentage advantage of the house

## Financial Flow

### Money In (House Gains)
- User deposits
- Player losses from games

### Money Out (House Losses)
- User withdrawals
- Player wins from games

### Net Calculation
```
Net Profit = (Total Deposits + Total Player Losses) - (Total Withdrawals + Total Player Wins)
House Edge = (Total Player Losses / (Total Player Losses + Total Player Wins)) * 100
```

## Implementation Notes

1. **Atomic Operations**: All balance updates are atomic to prevent inconsistencies
2. **Error Handling**: Comprehensive error handling with logging
3. **Initialization**: House starts with $10,000 default balance
4. **Real-time Updates**: All operations update house balance immediately
5. **Audit Trail**: All changes are logged with timestamps

## Testing

Run the test script to verify functionality:
```bash
python test_house_balance.py
```

The test covers:
- Database initialization
- Deposit/withdrawal tracking
- Game outcome tracking
- Multiple game scenarios
- Balance calculations verification
- Display formatting

## Integration Requirements

To fully integrate the house balance system:

1. **Update Game Logic**: Replace direct balance updates with house-aware functions
2. **Update Deposit Flow**: Use `process_deposit_with_house_balance()`
3. **Update Withdrawal Flow**: Use `process_withdrawal_with_house_balance()`
4. **Add Owner Panel Display**: Include house balance in admin interface

## Future Enhancements

1. **Historical Tracking**: Add daily/monthly house balance snapshots
2. **Alerts**: Notify owner of significant balance changes
3. **Backup/Recovery**: Implement house balance backup procedures
4. **Multi-Currency**: Support for different cryptocurrency house balances
5. **Risk Management**: Implement balance thresholds and warnings

## Security Considerations

1. **Owner Access Only**: House balance data should only be visible to casino owner
2. **Audit Logging**: All house balance changes should be logged
3. **Validation**: Validate all balance updates before applying
4. **Backup**: Regular backups of house balance data
5. **Monitoring**: Monitor for unusual balance changes

The house balance system provides complete financial transparency and real-time tracking of casino operations, enabling informed decision-making and proper risk management.

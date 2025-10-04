#!/bin/bash

# Update basketball.py to support configurable target scores

echo "Updating basketball.py for configurable target scores..."

# Update function signatures
sed -i '' 's/async def play_basketball_1v1_interactive(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, bet_amount: float) -> dict:/async def play_basketball_1v1_interactive(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, bet_amount: float, target_score: int = DEFAULT_TARGET_SCORE) -> dict:/' bot/games/basketball.py

sed -i '' 's/async def play_basketball_1v1(user_id: int, bet_amount: float) -> dict:/async def play_basketball_1v1(user_id: int, bet_amount: float, target_score: int = DEFAULT_TARGET_SCORE) -> dict:/' bot/games/basketball.py

# Replace TARGET_SCORE with target_score in function bodies
sed -i '' 's/TARGET_SCORE/target_score/g' bot/games/basketball.py

# Fix the constant definition that got changed
sed -i '' 's/DEFAULT_target_score = 3/DEFAULT_TARGET_SCORE = 3/' bot/games/basketball.py

# Fix function parameter references
sed -i '' 's/target_score: int = DEFAULT_target_score/target_score: int = DEFAULT_TARGET_SCORE/g' bot/games/basketball.py

echo "Basketball.py updated successfully!"

# Monkey Stacks Game Logic for Telegram Bot
# Difficulty: Easy, Medium, Hard
# This module is for integration with the Telegram bot only (not the mini app)

import random
from enum import Enum
from dataclasses import dataclass
from typing import Literal

class Difficulty(str, Enum):
    EASY = 'easy'
    MEDIUM = 'medium'
    HARD = 'hard'

STACK_LEVELS = {
    Difficulty.EASY: 5,
    Difficulty.MEDIUM: 7,
    Difficulty.HARD: 10
}

@dataclass
class MonkeyStacksResult:
    success: bool
    final_level: int
    reward: float
    message: str

async def play_monkey_stacks(user_id: int, bet: float, difficulty: Literal['easy','medium','hard']) -> MonkeyStacksResult:
    """
    Simulate a Monkey Stacks game for the Telegram bot.
    Returns the result and reward (if any).
    """
    levels = STACK_LEVELS[Difficulty(difficulty)]
    win_chance = {
        'easy': 0.8,
        'medium': 0.6,
        'hard': 0.4
    }[difficulty]
    payout_multiplier = {
        'easy': 2.0,
        'medium': 3.5,
        'hard': 6.0
    }[difficulty]
    current_level = 0
    for lvl in range(1, levels+1):
        if random.random() < win_chance:
            current_level = lvl
        else:
            return MonkeyStacksResult(
                success=False,
                final_level=current_level,
                reward=0.0,
                message=f"You reached level {current_level}. Stack collapsed!"
            )
    reward = round(bet * payout_multiplier, 2)
    return MonkeyStacksResult(
        success=True,
        final_level=levels,
        reward=reward,
        message=f"Congratulations! You stacked all {levels} monkeys and won {reward}!"
    )

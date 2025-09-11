<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

# Telegram Casino Bot Instructions

This is a Python-based Telegram casino bot project. When working on this codebase:

## Code Style & Structure
- Use async/await patterns for all bot handlers and database operations
- Follow PEP 8 style guidelines
- Use type hints for function parameters and return values
- Implement proper error handling with try/catch blocks
- Use the python-telegram-bot library's latest async API (v20+)

## Architecture Guidelines
- Keep game logic separate from bot handlers
- Use modular design with separate files for each game
- Implement database operations using aiosqlite for async support
- Use dataclasses or Pydantic models for data structures
- Maintain clear separation between business logic and presentation

## Bot Development Best Practices
- Always validate user input before processing
- Implement proper rate limiting for games
- Use inline keyboards for better user experience
- Provide clear error messages to users
- Log important events for debugging
- Handle bot restarts gracefully

## Game Implementation
- Each game should have its own module in the games/ directory
- Implement fair random number generation
- Validate all bets against user balance
- Update user balance atomically
- Provide clear game rules and instructions

## Database Design
- Use SQLite with aiosqlite for development
- Implement proper database migrations
- Use transactions for balance updates
- Index frequently queried columns
- Implement proper backup strategies

## Security Considerations
- Validate all user inputs
- Prevent SQL injection with parameterized queries
- Implement rate limiting to prevent abuse
- Don't store sensitive data in plain text
- Use environment variables for configuration

"""
Global task and state management for the bot.
"""

# A dictionary to hold references to all active asyncio tasks
# Key: scan_id (str), Value: asyncio.Task object
ACTIVE_TASKS = {}

# A dictionary to hold the state of user conversations (e.g., for /settings)
# Key: user_id (int), Value: state (str)
USER_STATES = {}

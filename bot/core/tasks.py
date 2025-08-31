"""
Global task management for the bot.
"""

# A dictionary to hold references to all active asyncio tasks
# Key: scan_id (str), Value: asyncio.Task object
ACTIVE_TASKS = {}

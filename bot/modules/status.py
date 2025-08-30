"""
Status command for tracking processing progress
"""

import logging
from datetime import datetime
from bot.helpers.message_utils import send_message
from bot.helpers.keyboard_utils import build_status_keyboard

LOGGER = logging.getLogger(__name__)

# Global processing state (in production, use database)
processing_states = {}

async def status_handler(client, message):
    """Handler for /status command"""
    try:
        user_id = message.from_user.id
        user_processes = {k: v for k, v in processing_states.items() 
                         if v.get('user_id') == user_id}
        
        if not user_processes:
            await send_message(message,
                "📊 **Status:** Bot is idle\n\n"
                "No active operations running.\n\n"
                "**Available Commands:**\n"
                "• `/updatemediainfo` - Extract MediaInfo\n"
                "• `/indexfiles` - Organize content\n\n"
                "Use `/help` for detailed instructions.")
            return
        
        # Show active processes
        for process_id, state in user_processes.items():
            status_text = build_status_message(state)
            keyboard = build_status_keyboard(process_id)
            await send_message(message, status_text, keyboard)
            
    except Exception as e:
        LOGGER.error(f"Status handler error: {e}")
        await send_message(message, f"❌ Error retrieving status: {e}")

def build_status_message(state):
    """Build detailed status message"""
    operation = state.get('operation', 'Unknown')
    channel = state.get('channel_name', 'Unknown')
    current = state.get('current', 0)
    total = state.get('total', 0)
    processed = state.get('processed', 0)
    errors = state.get('errors', 0)
    
    # Calculate progress
    progress = (current / total * 100) if total > 0 else 0
    
    # Build progress bar
    bar_length = 20
    filled = int(bar_length * progress / 100)
    progress_bar = f"[{'█' * filled}{'░' * (bar_length - filled)}] {progress:.1f}%"
    
    return f"""📊 **Media Processing Status**

**Operation:** {operation.title()}
📺 **Channel:** {channel}
📈 **Progress:** {current:,} / {total:,}

{progress_bar}

**Details:**
├─ ✅ **Processed:** {processed:,}
├─ ❌ **Errors:** {errors:,}
└─ 🔄 **Status:** {'🟢 Running' if state.get('status') == 'running' else '⏸️ Paused'}

⏱️ **Last Update:** {datetime.now().strftime('%H:%M:%S')}"""
  

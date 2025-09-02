"""
Utility commands for bot administration, including logs and server stats.
"""
import logging
import psutil
import shutil
import aiofiles
from bot.helpers.message_utils import send_reply

LOGGER = logging.getLogger(__name__)

def format_bytes(byte_count):
    """Helper function to format bytes into KB, MB, GB, etc."""
    if byte_count is None:
        return "N/A"
    power = 1024
    n = 0
    power_labels = {0: '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while byte_count >= power and n < len(power_labels) -1 :
        byte_count /= power
        n += 1
    return f"{byte_count:.2f} {power_labels[n]}B"

async def log_handler(client, message):
    """Handler for the /log command to show the bot's log."""
    try:
        async with aiofiles.open('log.txt', 'r') as f: # Changed from bot.log
            lines = await f.readlines()
            last_lines = "".join(lines[-20:])
        
        if not last_lines:
            await send_reply(message, "Log file is empty.")
            return
            
        await send_reply(message, f"**Last 20 lines of log:**\n\n`{last_lines}`")

    except FileNotFoundError:
        await send_reply(message, "Log file not found. Make sure logging is configured correctly.")
    except Exception as e:
        LOGGER.error(f"Log handler error: {e}")
        await send_reply(message, f"Error reading log file: {e}")

async def stats_handler(client, message):
    """Handler for the /stats command to show server resource usage."""
    try:
        # CPU Usage
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Memory Usage
        memory = psutil.virtual_memory()
        mem_total = format_bytes(memory.total)
        mem_used = format_bytes(memory.used)
        mem_percent = memory.percent
        
        # Disk Usage
        disk = shutil.disk_usage('/')
        disk_total = format_bytes(disk.total)
        disk_used = format_bytes(disk.used)
        disk_percent = disk.percent
        
        # Network Usage
        net = psutil.net_io_counters()
        net_sent = format_bytes(net.bytes_sent)
        net_recv = format_bytes(net.bytes_recv)
        
        stats_text = (
            f"**Server Resource Stats**\n\n"
            f"**CPU:** `{cpu_percent:.1f}%`\n"
            f"**RAM:** `{mem_used} / {mem_total} ({mem_percent}%)`\n"
            f"**Disk:** `{disk_used} / {disk_total} ({disk_percent}%)`\n\n"
            f"**Network Traffic (since boot)**\n"
            f" Uploaded: `{net_sent}`\n"
            f" Downloaded: `{net_recv}`"
        )
        
        await send_reply(message, stats_text)

    except Exception as e:
        LOGGER.error(f"Stats handler error: {e}")
        await send_reply(message, f"Error getting server stats: {e}")

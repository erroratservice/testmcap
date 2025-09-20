import asyncio
import logging
from collections import Counter
import re

from bot.core.client import TgClient
from bot.helpers.channel_utils import stream_messages_by_id_batches
from bot.helpers.message_utils import send_reply
from bot.helpers.indexing_parser import KNOWN_ENCODERS, IGNORED_TAGS

LOGGER = logging.getLogger(__name__)

async def findencoders_handler(client, message):
    """
    Handler for the /findencoders command.
    """
    try:
        if not message.reply_to_message and len(message.command) < 2:
            await send_reply(message, "<b>Please reply to a message or provide a channel ID.</b>")
            return

        if message.reply_to_message:
            channel_id = message.reply_to_message.chat.id
        else:
            try:
                channel_id = int(message.command[1])
            except (ValueError, IndexError):
                await send_reply(message, "<b>Invalid Channel ID.</b>")
                return

        await send_reply(message, f"<b>🔍 Started finding encoders in channel {channel_id}...</b>")

        potential_encoders = Counter()
        processed_files = 0

        async for message_batch in stream_messages_by_id_batches(channel_id):
            for msg in message_batch:
                if msg.document or msg.video:
                    file_name = getattr(msg.document, 'file_name', getattr(msg.video, 'file_name', None))
                    if file_name:
                        processed_files += 1
                        tags = extract_potential_encoder_tags(file_name)
                        potential_encoders.update(tags)

        if not potential_encoders:
            await send_reply(message, f"<b>No potential encoders found in {processed_files} files.</b>")
            return

        response_text = f"<b>🔎 Found {len(potential_encoders)} potential encoders from {processed_files} files in channel {channel_id}:</b>\n\n"
        for tag, count in potential_encoders.most_common(50):
            response_text += f"<code>{tag}</code> ({count} times)\n"

        await send_reply(message, response_text)

    except Exception as e:
        LOGGER.error(f"Error in findencoders_handler: {e}")
        await send_reply(message, f"<b>Error:</b> {e}")

def extract_potential_encoder_tags(filename):
    """
    Extracts potential encoder tags from a filename.
    """
    # Remove file extension
    filename_without_ext = re.sub(r'\.\w+$', '', filename)
    # Split filename into parts
    parts = re.split(r'[ ._\[\]()\-]+', filename_without_ext)
    
    potential_tags = []
    for part in parts:
        part_upper = part.upper()
        if (
            part_upper
            and part_upper not in KNOWN_ENCODERS
            and part_upper not in IGNORED_TAGS
            and not part_upper.isdigit()
            and len(part_upper) > 2
            and not re.match(r'S\d{1,2}(E\d{1,3})?', part_upper)
            and not re.match(r'\d{3,4}P', part_upper)
            and not re.match(r'\d{4}', part_upper) # Year
        ):
            potential_tags.append(part)
            
    return potential_tags

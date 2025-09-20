import asyncio
import logging
from collections import Counter
import re
import os
import aiofiles

from bot.core.client import TgClient
from bot.helpers.channel_utils import stream_messages_by_id_batches
from bot.helpers.message_utils import send_reply
from bot.helpers.indexing_parser import KNOWN_ENCODERS, IGNORED_TAGS

LOGGER = logging.getLogger(__name__)

async def findencoders_handler(client, message):
    """
    Handler for the /findencoders command.
    Scans a channel for potential new encoder tags and sends the result as a text file.
    """
    try:
        if not message.reply_to_message and len(message.command) < 2:
            await send_reply(message, "<b>Usage:</b> `/findencoders <channel_id>` or reply to a message from the channel.")
            return

        if message.reply_to_message:
            channel_id = message.reply_to_message.chat.id
        else:
            try:
                channel_id = int(message.command[1])
            except (ValueError, IndexError):
                await send_reply(message, "<b>Invalid Channel ID provided.</b>")
                return

        status_message = await send_reply(message, f"<b>🔍 Scanning channel `{channel_id}` for new encoder tags...</b>")

        potential_encoders = Counter()
        processed_files = 0

        async for message_batch in stream_messages_by_id_batches(channel_id):
            for msg in message_batch:
                file_name = getattr(msg.document, 'file_name', getattr(msg.video, 'file_name', None))
                if file_name:
                    processed_files += 1
                    tags = extract_potential_encoder_tags(file_name)
                    potential_encoders.update(tags)

        if not potential_encoders:
            await status_message.edit_text(f"✅ **Scan complete.** No new potential encoders found in {processed_files} files.")
            return

        # Prepare the text file content
        file_content = f"# Potential New Encoders Found in Channel: {channel_id}\n"
        file_content += f"# Total Files Scanned: {processed_files}\n"
        file_content += f"# Found {len(potential_encoders)} unique potential encoders.\n\n"
        
        # Sort by count, descending
        for tag, count in potential_encoders.most_common():
            file_content += f"{tag}    ({count} times)\n"
            
        output_file_path = f"encoders_{channel_id}.txt"
        
        async with aiofiles.open(output_file_path, 'w', encoding='utf-8') as f:
            await f.write(file_content)

        await client.send_document(
            chat_id=message.chat.id,
            document=output_file_path,
            caption=f"**✅ Scan Complete!**\nFound **{len(potential_encoders)}** potential new encoders from **{processed_files}** files."
        )
        
        await status_message.delete()

    except Exception as e:
        LOGGER.error(f"Error in findencoders_handler: {e}", exc_info=True)
        await send_reply(message, f"<b>An error occurred:</b> <code>{e}</code>")
    finally:
        # Clean up the created file
        if os.path.exists(output_file_path):
            os.remove(output_file_path)


def extract_potential_encoder_tags(filename):
    """
    Extracts potential encoder tags from a filename, excluding known and ignored tags.
    """
    # Remove file extension and split into parts
    filename_without_ext = os.path.splitext(filename)[0]
    parts = re.split(r'[ ._\[\]()\-]+', filename_without_ext)
    
    potential_tags = []
    
    # Create sets for faster lookups
    known_encoders_set = {enc.upper() for enc in KNOWN_ENCODERS}
    ignored_tags_set = {tag.upper() for tag in IGNORED_TAGS}

    for part in reversed(parts): # Check from the end of the filename first
        if not part:
            continue
            
        part_upper = part.upper()
        
        # Filtering logic
        if (
            part_upper not in known_encoders_set and
            part_upper not in ignored_tags_set and
            not part_upper.isdigit() and
            len(part) > 2 and
            not re.match(r'S\d{1,2}(E\d{1,3})?$', part_upper) and # S01E01
            not re.match(r'\d{3,4}P$', part_upper) and # 1080p
            not re.match(r'\d{4}$', part_upper) and # Year
            not any(audio_codec in part_upper for audio_codec in ['5.1', '7.1', 'DDP', 'EAC3'])
        ):
            potential_tags.append(part)
            
    return potential_tags

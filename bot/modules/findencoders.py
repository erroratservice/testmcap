import asyncio
import logging
from collections import Counter
import re
import os
import aiofiles

from bot.core.client import TgClient
from bot.helpers.channel_utils import stream_messages_by_id_batches
from bot.helpers.message_utils import send_reply
from bot.helpers.indexing_parser import KNOWN_ENCODERS, IGNORED_TAGS, parse_media_info

LOGGER = logging.getLogger(__name__)

async def findencoders_handler(client, message):
    """
    Handler for the /findencoders command.
    Scans a channel for potential new encoder tags using advanced parsing and sends the result as a text file.
    """
    output_file_path = ""
    try:
        if not message.reply_to_message and len(message.command) < 2:
            await send_reply(message, "<b>Usage:</b> `/findencoders <channel_id>` or reply to a message from the channel.")
            return

        channel_id = 0
        if message.reply_to_message:
            channel_id = message.reply_to_message.chat.id
        else:
            try:
                channel_id = int(message.command[1])
            except (ValueError, IndexError):
                await send_reply(message, "<b>Invalid Channel ID provided.</b>")
                return

        status_message = await send_reply(message, f"<b>🔍 Smart scanning channel `{channel_id}` for new encoder tags...</b>")

        potential_encoders = Counter()
        processed_files = 0
        batch_count = 0

        async for message_batch in stream_messages_by_id_batches(channel_id):
            batch_count += 1
            for msg in message_batch:
                file_name = getattr(msg.document, 'file_name', getattr(msg.video, 'file_name', None))
                if file_name:
                    processed_files += 1
                    # --- IMPROVEMENT: Use the full parsing logic to get the exclusion set ---
                    info = parse_media_info(file_name)
                    words_to_exclude = set()
                    if info and info.get('title'):
                        # Re-create the exclusion set from the official title words
                        for word in re.split(r'[\s._-]+', info['title'].upper()):
                            words_to_exclude.add(word)

                    tags = extract_potential_encoder_tags(file_name, words_to_exclude)
                    potential_encoders.update(tags)

            # Update status message periodically
            if batch_count % 10 == 0:
                try:
                    await status_message.edit_text(
                        f"<b>🔍 Smart scanning channel `{channel_id}`...</b>\n\n"
                        f"Processed <b>{processed_files}</b> files."
                    )
                except Exception:
                    pass  # Ignore errors like MessageNotModified

        if not potential_encoders:
            await status_message.edit_text(f"✅ **Scan complete.** No new potential encoders found in {processed_files} files.")
            return

        # Prepare the text file content
        file_content = f"# Potential New Encoders Found in Channel: {channel_id}\n"
        file_content += f"# Total Files Scanned: {processed_files}\n"
        file_content += f"# Found {len(potential_encoders)} unique potential encoders.\n\n"
        
        for tag, count in potential_encoders.most_common():
            file_content += f"{tag.strip()}    ({count} times)\n"
            
        output_file_path = f"encoders_{channel_id}.txt"
        
        async with aiofiles.open(output_file_path, 'w', encoding='utf-8') as f:
            await f.write(file_content)

        await client.send_document(
            chat_id=message.chat.id,
            document=output_file_path,
            caption=f"**✅ Smart Scan Complete!**\nFound **{len(potential_encoders)}** potential new encoders from **{processed_files}** files."
        )
        
        await status_message.delete()

    except Exception as e:
        LOGGER.error(f"Error in findencoders_handler: {e}", exc_info=True)
        await send_reply(message, f"<b>An error occurred:</b> <code>{e}</code>")
    finally:
        if os.path.exists(output_file_path):
            os.remove(output_file_path)


def extract_potential_encoder_tags(filename, words_to_exclude=None):
    """
    Extracts potential encoder tags from a filename, excluding known, ignored, and title-related tags.
    """
    if words_to_exclude is None:
        words_to_exclude = set()

    filename_without_ext = os.path.splitext(filename)[0]
    parts = re.split(r'[ ._\[\]()\-]+', filename_without_ext)
    
    potential_tags = []
    
    known_encoders_set = {enc.upper() for enc in KNOWN_ENCODERS}
    ignored_tags_set = {tag.upper() for tag in IGNORED_TAGS}

    for part in reversed(parts):
        if not part:
            continue
            
        part_upper = part.upper()
        
        # --- IMPROVEMENT: Check against the dynamic exclusion set from the parser ---
        if (
            part_upper not in known_encoders_set and
            part_upper not in ignored_tags_set and
            part_upper not in words_to_exclude and # The crucial new check
            not part_upper.isdigit() and
            len(part) > 2 and
            not re.match(r'S\d{1,2}(E\d{1,3})?$', part_upper) and
            not re.match(r'\d{3,4}P$', part_upper) and
            not re.match(r'\d{4}$', part_upper) and # Year
            not any(audio_codec in part_upper for audio_codec in ['5.1', '7.1', 'DDP', 'EAC3'])
        ):
            potential_tags.append(part)
            
    return potential_tags

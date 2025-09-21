import asyncio
import logging
from collections import Counter
import re
import os
import aiofiles

from bot.core.client import TgClient
from bot.helpers.channel_utils import stream_messages_by_id_batches
from bot.helpers.message_utils import send_reply, edit_message
from bot.helpers.indexing_parser import KNOWN_ENCODERS, IGNORED_TAGS
from bot.database.mongodb import MongoDB

LOGGER = logging.getLogger(__name__)

# --- CONFIGURATION ---
FILES_PER_UPDATE = 10000  # Send an update file after this many files are scanned

async def findencoders_handler(client, message):
    """
    Handler for the /findencoders command.
    Scans a channel for potential new encoder tags with high precision and sends results in batches.
    """
    output_file_path = ""
    try:
        is_force_rescan = '-rescan' in message.command
        args = [arg for arg in message.command[1:] if arg != '-rescan']

        if not message.reply_to_message and not args:
            await send_reply(message, "<b>Usage:</b> `/findencoders <channel_id> [-rescan]` or reply to a message.")
            return

        channel_id = 0
        if message.reply_to_message:
            channel_id = message.reply_to_message.chat.id
        else:
            try:
                channel_id = int(args[0])
            except (ValueError, IndexError):
                await send_reply(message, "<b>Invalid Channel ID provided.</b>")
                return

        if is_force_rescan:
            await MongoDB.clear_cached_message_ids(channel_id)
            LOGGER.info(f"Forced rescan for channel {channel_id}. Cache cleared.")

        status_message = await send_reply(message, f"<b>🔍 Precision scanning channel `{channel_id}` for new encoders...</b>")

        potential_encoders = Counter()
        total_processed_files = 0
        batch_count = 0
        update_file_count = 1

        async for message_batch in stream_messages_by_id_batches(channel_id, force=is_force_rescan):
            batch_count += 1
            for msg in message_batch:
                # --- NEW LOGIC: Prioritize caption's first line ---
                text_to_scan = ""
                if msg.caption and '.' in msg.caption.split('\n')[0]:
                    text_to_scan = msg.caption.split('\n')[0]
                else:
                    file_name = getattr(msg.document, 'file_name', getattr(msg.video, 'file_name', None))
                    if file_name:
                        text_to_scan = file_name

                if text_to_scan:
                    total_processed_files += 1
                    tags = extract_potential_encoder_tags(text_to_scan)
                    potential_encoders.update(tags)

                # --- NEW LOGIC: Send incremental update files ---
                if total_processed_files > 0 and total_processed_files % FILES_PER_UPDATE == 0:
                    await send_update_file(client, message, channel_id, potential_encoders, total_processed_files, update_file_count)
                    potential_encoders.clear() # Reset for the next batch
                    update_file_count += 1
            
            # Update status message with progress
            if batch_count % 10 == 0:
                try:
                    await edit_message(
                        status_message,
                        f"<b>🔍 Precision scanning channel `{channel_id}`...</b>\n\n"
                        f"Processed <b>{total_processed_files}</b> files so far."
                    )
                except Exception:
                    pass

        # Send the final file with any remaining encoders
        if potential_encoders:
            await send_update_file(client, message, channel_id, potential_encoders, total_processed_files, update_file_count, is_final=True)
        else:
            await edit_message(status_message, f"✅ **Scan complete.** No new potential encoders found in {total_processed_files} files.")


    except Exception as e:
        LOGGER.error(f"Error in findencoders_handler: {e}", exc_info=True)
        await send_reply(message, f"<b>An error occurred:</b> <code>{e}</code>")


async def send_update_file(client, message, channel_id, encoders, processed_count, file_num, is_final=False):
    """Generates and sends an encoder list file."""
    output_file_path = f"encoders_{channel_id}_part_{file_num}.txt"
    try:
        file_content = f"# Potential New Encoders Found in Channel: {channel_id}\n"
        file_content += f"# Part {file_num} - Scanned up to {processed_count} files.\n"
        file_content += f"# Found {len(encoders)} unique potential encoders in this batch.\n\n"
        
        for tag, count in encoders.most_common():
            file_content += f"{tag.strip()}    ({count} times)\n"

        async with aiofiles.open(output_file_path, 'w', encoding='utf-8') as f:
            await f.write(file_content)
        
        final_caption = f"**📦 Encoder List - Part {file_num}**\nResults after scanning **{processed_count}** files."
        if is_final:
            final_caption = f"**✅ Final Encoder List**\nFound a total of **{len(encoders)}** new potential encoders from **{processed_count}** files."

        await client.send_document(
            chat_id=message.chat.id,
            document=output_file_path,
            caption=final_caption
        )
    finally:
        if os.path.exists(output_file_path):
            os.remove(output_file_path)


def extract_potential_encoder_tags(text):
    """
    Extracts potential encoder tags by focusing only on the last two words of a filename.
    """
    # Remove file extension and split into parts
    filename_without_ext = os.path.splitext(text)[0]
    parts = re.split(r'[ ._\[\]()\-]+', filename_without_ext)
    
    # --- NEW LOGIC: Only consider the last two non-empty parts ---
    potential_parts = [p for p in parts if p][-2:]
    
    potential_tags = []
    
    known_encoders_set = {enc.upper() for enc in KNOWN_ENCODERS}
    ignored_tags_set = {tag.upper() for tag in IGNORED_TAGS}

    for part in potential_parts:
        part_upper = part.upper()
        
        if (
            part_upper not in known_encoders_set and
            part_upper not in ignored_tags_set and
            not part_upper.isdigit() and
            len(part) > 2 and
            not re.match(r'S\d{1,2}(E\d{1,3})?$', part_upper) and
            not re.match(r'\d{3,4}P$', part_upper) and
            not re.match(r'\d{4}$', part_upper) and # Year
            not any(audio_codec in part_upper for audio_codec in ['5.1', '7.1', 'DDP', 'EAC3'])
        ):
            potential_tags.append(part)
            
    return potential_tags

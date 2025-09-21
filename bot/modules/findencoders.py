import asyncio
import logging
from collections import Counter, defaultdict
import re
import os
import aiofiles

from bot.core.client import TgClient
from bot.helpers.channel_utils import stream_messages_by_id_batches
from bot.helpers.message_utils import send_reply, edit_message
from bot.helpers.indexing_parser import KNOWN_ENCODERS, IGNORED_TAGS, get_base_name
from bot.database.mongodb import MongoDB

LOGGER = logging.getLogger(__name__)

# --- CONFIGURATION ---
FILES_PER_UPDATE = 1000  # Send an update file after this many files are scanned

async def findencoders_handler(client, message):
    """
    Handler for the /findencoders command.
    Correctly handles multi-part files and scans for potential new encoder tags with high precision.
    """
    output_file_path = ""
    try:
        is_force_rescan = '-rescan' in message.command
        args = [arg for arg in message.command[1:] if arg != '-rescan']

        channel_id = 0
        if message.reply_to_message:
            channel_id = message.reply_to_message.chat.id
        elif args:
            try:
                channel_id = int(args[0])
            except (ValueError, IndexError):
                await send_reply(message, "<b>Invalid Channel ID provided.</b>")
                return
        else:
            await send_reply(message, "<b>Usage:</b> `/findencoders <channel_id> [-rescan]` or reply to a message.")
            return

        if is_force_rescan:
            await MongoDB.clear_cached_message_ids(channel_id)
            LOGGER.info(f"Forced rescan for channel {channel_id}. Cache cleared.")

        status_message = await send_reply(message, f"<b>🎯 Ultra-precision scan initiated for channel `{channel_id}`...</b>")

        found_encoders_counter = Counter()
        total_processed_files = 0
        batch_count = 0
        update_file_count = 1

        async for message_batch in stream_messages_by_id_batches(channel_id, force=is_force_rescan):
            batch_count += 1
            
            # --- NEW: Logic to group multi-part files ---
            message_groups = defaultdict(list)
            for msg in message_batch:
                text_to_scan = ""
                # Prioritize caption's first line
                if msg.caption and '.' in msg.caption.split('\n')[0]:
                    text_to_scan = msg.caption.split('\n')[0].strip()
                else:
                    file_name = getattr(msg.document, 'file_name', getattr(msg.video, 'file_name', None))
                    if file_name:
                        text_to_scan = file_name.strip()
                
                if text_to_scan:
                    base_name, _ = get_base_name(text_to_scan)
                    message_groups[base_name].append(msg)
            
            # Process each unique file group once
            for base_name, msg_group in message_groups.items():
                total_processed_files += len(msg_group)
                tags = extract_potential_encoder_tags(base_name)
                if tags:
                    found_encoders_counter.update(tags)

            # Send incremental update files
            if total_processed_files > 0 and update_file_count * FILES_PER_UPDATE <= total_processed_files:
                await send_encoder_file(client, message, channel_id, found_encoders_counter, total_processed_files, update_file_count)
                found_encoders_counter.clear()
                update_file_count += 1
            
            if batch_count % 5 == 0:
                try:
                    await edit_message(
                        status_message,
                        f"<b>🎯 Ultra-precision scan for `{channel_id}`...</b>\n\n"
                        f"Files Scanned: <b>{total_processed_files}</b>"
                    )
                except Exception:
                    pass

        # Send the final file with any remaining data
        if found_encoders_counter:
            await send_encoder_file(client, message, channel_id, found_encoders_counter, total_processed_files, update_file_count, is_final=True)
        
        final_message = f"✅ **Scan complete.**\nProcessed a total of {total_processed_files} files."
        if update_file_count > 1 or (update_file_count == 1 and found_encoders_counter):
             final_message += f"\nGenerated {update_file_count} encoder list files."

        await edit_message(status_message, final_message)


    except Exception as e:
        LOGGER.error(f"Error in findencoders_handler: {e}", exc_info=True)
        await send_reply(message, f"<b>An error occurred:</b> <code>{e}</code>")


async def send_encoder_file(client, message, channel_id, encoders, processed_count, file_num, is_final=False):
    """Generates and sends a clean encoder list file."""
    output_file_path = f"encoders_{channel_id}_part_{file_num}.txt"
    try:
        file_content = f"# Potential New Encoders Found in Channel: {channel_id}\n"
        file_content += f"# Part {file_num} - Based on {processed_count} total scanned files.\n\n"
        
        if encoders:
            for tag, count in encoders.most_common():
                file_content += f"{tag.strip():<20} ({count} times)\n"
        else:
            file_content += "No new potential encoders found in this batch.\n"

        async with aiofiles.open(output_file_path, 'w', encoding='utf-8') as f:
            await f.write(file_content)
        
        caption = f"**📦 Encoder List - Part {file_num}**\nCumulative files scanned: **{processed_count}**."
        if is_final:
            caption = f"**✅ Final Encoder List**\nTotal files scanned: **{processed_count}**."

        await client.send_document(
            chat_id=message.chat.id,
            document=output_file_path,
            caption=caption
        )
    finally:
        if os.path.exists(output_file_path):
            os.remove(output_file_path)


def extract_potential_encoder_tags(text):
    """
    Extracts potential encoder tags by strictly focusing on the last two words of a filename.
    """
    filename_without_ext = os.path.splitext(text)[0]
    parts = re.split(r'[ ._\[\]()\-]+', filename_without_ext)
    
    # --- NEW LOGIC: Only consider the last two non-empty parts ---
    potential_parts = [p for p in parts if p][-2:]
    
    potential_tags = []
    
    known_encoders_set = {enc.upper() for enc in KNOWN_ENCODERS}
    ignored_tags_set = {tag.upper() for tag in IGNORED_TAGS}

    for part in potential_parts:
        cleaned_part = re.sub(r'[._\[\]()\-]+$', '', part)
        if not cleaned_part:
            continue
            
        part_upper = cleaned_part.upper()
        
        if (
            part_upper not in known_encoders_set and
            part_upper not in ignored_tags_set and
            not part_upper.isdigit() and
            len(cleaned_part) > 2 and
            not re.match(r'S\d{1,2}(E\d{1,3})?$', part_upper) and
            not re.match(r'\d{3,4}P$', part_upper) and
            not re.match(r'\d{4}$', part_upper) and # Year
            not any(audio_codec in part_upper for audio_codec in ['5.1', '7.1', 'DDP', 'EAC3'])
        ):
            potential_tags.append(cleaned_part)
            
    return potential_tags

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
# Set to 1000 for your testing, can be increased to 10000 for production
FILES_PER_UPDATE = 1000 

async def findencoders_handler(client, message):
    """
    Handler for the /findencoders command.
    Scans a channel for potential new encoder tags with high precision and sends results in batches.
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

        # --- Lists for the detailed analysis file ---
        found_encoders_counter = Counter()
        scanned_full_names = []

        total_processed_files = 0
        batch_count = 0
        update_file_count = 1

        async for message_batch in stream_messages_by_id_batches(channel_id, force=is_force_rescan):
            batch_count += 1
            for msg in message_batch:
                text_to_scan = ""
                # --- LOGIC: Prioritize caption's first line ---
                if msg.caption and '.' in msg.caption.split('\n')[0]:
                    text_to_scan = msg.caption.split('\n')[0].strip()
                else:
                    file_name = getattr(msg.document, 'file_name', getattr(msg.video, 'file_name', None))
                    if file_name:
                        text_to_scan = file_name.strip()

                if text_to_scan:
                    total_processed_files += 1
                    scanned_full_names.append(text_to_scan)  # Store full name for analysis
                    tag = extract_potential_encoder_tag(text_to_scan)
                    if tag:
                        found_encoders_counter.update([tag])

                # --- LOGIC: Send incremental update files ---
                if total_processed_files > 0 and total_processed_files % FILES_PER_UPDATE == 0:
                    await send_analysis_file(client, message, channel_id, found_encoders_counter, scanned_full_names, total_processed_files, update_file_count)
                    # Reset lists for the next batch
                    found_encoders_counter.clear()
                    scanned_full_names = []
                    update_file_count += 1
            
            # Update status message with progress
            if batch_count % 10 == 0:
                try:
                    await edit_message(
                        status_message,
                        f"<b>🎯 Ultra-precision scan for `{channel_id}`...</b>\n\n"
                        f"Files Scanned: <b>{total_processed_files}</b>"
                    )
                except Exception:
                    pass

        # Send the final file with any remaining data
        if found_encoders_counter or scanned_full_names:
            await send_analysis_file(client, message, channel_id, found_encoders_counter, scanned_full_names, total_processed_files, update_file_count, is_final=True)
        
        final_message = f"✅ **Scan complete.**\nProcessed a total of {total_processed_files} files."
        if update_file_count > 1 or (update_file_count == 1 and (found_encoders_counter or scanned_full_names)):
             final_message += f"\nGenerated {update_file_count} analysis files."

        await edit_message(status_message, final_message)


    except Exception as e:
        LOGGER.error(f"Error in findencoders_handler: {e}", exc_info=True)
        await send_reply(message, f"<b>An error occurred:</b> <code>{e}</code>")


async def send_analysis_file(client, message, channel_id, encoders, full_names, processed_count, file_num, is_final=False):
    """Generates and sends a detailed analysis file with two sections."""
    output_file_path = f"encoder_analysis_{channel_id}_part_{file_num}.txt"
    try:
        # --- NEW: Two-section format for analysis ---
        file_content = f"# Encoder Analysis for Channel: {channel_id}\n"
        file_content += f"# Part {file_num} - Based on {processed_count} total scanned files.\n\n"
        
        file_content += "--- Potential Encoders Found ---\n"
        if encoders:
            for tag, count in encoders.most_common():
                file_content += f"{tag.strip():<20} ({count} times)\n"
        else:
            file_content += "No new potential encoders found in this batch.\n"
            
        file_content += "\n--- Full Names Scanned in This Batch ---\n"
        if full_names:
            for name in full_names:
                file_content += f"{name}\n"
        else:
            file_content += "No files processed in this batch.\n"

        async with aiofiles.open(output_file_path, 'w', encoding='utf-8') as f:
            await f.write(file_content)
        
        caption = f"**📦 Encoder Analysis - Part {file_num}**\nCumulative files scanned: **{processed_count}**."
        if is_final:
            caption = f"**✅ Final Encoder Analysis**\nTotal files scanned: **{processed_count}**."

        await client.send_document(
            chat_id=message.chat.id,
            document=output_file_path,
            caption=caption
        )
    finally:
        if os.path.exists(output_file_path):
            os.remove(output_file_path)


def extract_potential_encoder_tag(text):
    """
    Extracts a potential encoder tag by strictly focusing on the last word of a filename
    and cleaning it of trailing special characters.
    Returns the tag as a string or None if no valid tag is found.
    """
    filename_without_ext = os.path.splitext(text)[0]
    
    # --- NEW LOGIC: More robust splitting and cleaning ---
    parts = re.split(r'[ ._\[\]()\-]+', filename_without_ext)
    
    last_part = next((p for p in reversed(parts) if p), None)
    
    if not last_part:
        return None
    
    # --- CRUCIAL FIX: Strip trailing special characters ---
    cleaned_part = re.sub(r'[._\[\]()\-]+$', '', last_part)
    
    if not cleaned_part:
        return None

    part_upper = cleaned_part.upper()
    
    known_encoders_set = {enc.upper() for enc in KNOWN_ENCODERS}
    ignored_tags_set = {tag.upper() for tag in IGNORED_TAGS}

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
        return cleaned_part
            
    return None

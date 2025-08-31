"""
MediaInfo update with head+tail chunk download and metadata merging
"""

import asyncio
import logging
import os
import tempfile
import json
import re
from datetime import datetime
from pyrogram.errors import MessageNotModified
from bot.core.client import TgClient
from bot.helpers.message_utils import send_message, edit_message

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)

async def updatemediainfo_handler(client, message):
    """Handler with head+tail metadata merging strategy"""
    try:
        LOGGER.info("🚀 Starting updatemediainfo with head+tail merge strategy")
        
        channels = await get_target_channels(message)
        if not channels:
            await send_message(message, 
                "❌ **Usage:**\n• `/updatemediainfo -1001234567890`")
            return
        
        for channel_id in channels:
            await process_channel_with_head_tail_merge(channel_id, message)
            
    except Exception as e:
        LOGGER.error(f"💥 Handler error: {e}", exc_info=True)
        await send_message(message, f"❌ **Error:** {e}")

async def process_channel_with_head_tail_merge(channel_id, message):
    """Process channel with head+tail metadata merging"""
    try:
        # Access channel
        chat = await TgClient.user.get_chat(channel_id)
        LOGGER.info(f"✅ Accessing channel: {chat.title}")
        
        progress_msg = await send_message(message,
            f"🔄 **Processing:** {chat.title}\n"
            f"📊 **Method:** Head+Tail MediaInfo Merge\n"
            f"🎯 **Strategy:** 10MB Head + 5MB Tail → Merge Metadata\n"
            f"🔍 **Status:** Scanning messages...")
        
        processed = 0
        errors = 0
        skipped = 0
        head_only_success = 0
        tail_success = 0
        merge_success = 0
        total_messages = 0
        media_found = 0
        
        message_count = 0
        async for msg in TgClient.user.get_chat_history(chat_id=channel_id, limit=100):
            message_count += 1
            total_messages += 1
            
            # Check for media
            if not await has_media(msg):
                skipped += 1
                continue
            
            # Check if already processed
            if await already_has_mediainfo(msg):
                skipped += 1
                continue
            
            media_found += 1
            LOGGER.info(f"🎯 Processing media message {msg.id}")
            
            try:
                success, method = await process_with_head_tail_merge(TgClient.user, msg)
                if success:
                    processed += 1
                    if method == "head_only":
                        head_only_success += 1
                    elif method == "tail":
                        tail_success += 1
                    elif method == "merge":
                        merge_success += 1
                    LOGGER.info(f"✅ Updated message {msg.id} using {method}")
                else:
                    errors += 1
                    LOGGER.error(f"❌ Failed to update message {msg.id}")
            except Exception as e:
                LOGGER.error(f"💥 Exception processing {msg.id}: {e}")
                errors += 1
            
            # Progress update
            if message_count % 5 == 0:
                await edit_message(progress_msg,
                    f"🔄 **Processing:** {chat.title}\n"
                    f"📊 **Messages:** {total_messages} | **Media:** {media_found}\n"
                    f"✅ **Updated:** {processed} | ❌ **Errors:** {errors}\n"
                    f"🎯 **Head:** {head_only_success} | 🎯 **Tail:** {tail_success} | 🔗 **Merge:** {merge_success}")
                await asyncio.sleep(0.5)
        
        # Final results
        final_stats = (
            f"✅ **Completed:** {chat.title}\n"
            f"📊 **Total Messages:** {total_messages}\n"
            f"📁 **Media Found:** {media_found}\n"
            f"✅ **Updated:** {processed} files\n"
            f"❌ **Errors:** {errors} files\n"
            f"⏭️ **Skipped:** {skipped} files\n\n"
            f"🎯 **Head Only:** {head_only_success}\n"
            f"🎯 **Tail Success:** {tail_success}\n"
            f"🔗 **Merge Success:** {merge_success}"
        )
        
        await edit_message(progress_msg, final_stats)
        
    except Exception as e:
        LOGGER.error(f"💥 Channel processing error: {e}")
        await send_message(message, f"❌ **Error:** {str(e)}")

async def process_with_head_tail_merge(client, message):
    """Process message with head+tail merge strategy"""
    try:
        media = None
        if message.video:
            media = message.video
        elif message.audio:
            media = message.audio
        elif message.document:
            media = message.document
        else:
            return False, "none"
        
        filename = str(media.file_name) if media.file_name else f"media_{message.id}"
        size = media.file_size
        
        LOGGER.info(f"📁 Processing: {filename} ({size/1024/1024:.1f}MB)")
        
        # Strategy 1: Try head chunk first (10MB)
        LOGGER.info("🎯 Strategy 1: Trying 10MB head chunk")
        head_metadata = await extract_metadata_from_chunk(client, message, filename, "head", 10)
        
        if head_metadata and has_video_audio_streams(head_metadata):
            LOGGER.info("✅ Head chunk has complete metadata")
            success = await update_caption_with_metadata(message, head_metadata)
            if success:
                return True, "head_only"
        
        # Strategy 2: Try tail chunk (5MB)
        LOGGER.info("🎯 Strategy 2: Trying 5MB tail chunk")  
        tail_metadata = await extract_metadata_from_chunk(client, message, filename, "tail", 5, size)
        
        if tail_metadata and has_video_audio_streams(tail_metadata):
            LOGGER.info("✅ Tail chunk has complete metadata")
            success = await update_caption_with_metadata(message, tail_metadata)
            if success:
                return True, "tail"
        
        # Strategy 3: Merge head + tail metadata
        LOGGER.info("🎯 Strategy 3: Merging head + tail metadata")
        merged_metadata = merge_mediainfo_metadata(head_metadata, tail_metadata)
        
        if merged_metadata and has_video_audio_streams(merged_metadata):
            LOGGER.info("✅ Merged metadata has complete streams")
            success = await update_caption_with_metadata(message, merged_metadata)
            if success:
                return True, "merge"
        
        LOGGER.warning("⚠️ All strategies failed - no usable metadata found")
        return False, "failed"
        
    except Exception as e:
        LOGGER.error(f"💥 Head+tail processing error: {e}")
        return False, "error"

async def extract_metadata_from_chunk(client, message, filename, chunk_type, size_mb, total_size=None):
    """Extract MediaInfo metadata from head or tail chunk"""
    download_path = None
    try:
        LOGGER.debug(f"📥 Downloading {size_mb}MB {chunk_type} chunk")
        
        # Create temp file
        rand_str = f"{chunk_type}_{message.id}"
        download_path = f"/tmp/{rand_str}_{filename.replace('/', '_')}"
        
        if chunk_type == "head":
            # Download head chunk
            success = await download_head_chunk(client, message, download_path, size_mb)
        else:
            # Download tail chunk
            success = await download_tail_chunk(client, message, download_path, size_mb, total_size)
        
        if not success:
            LOGGER.warning(f"⚠️ {chunk_type} chunk download failed")
            return None
        
        # Extract MediaInfo
        mediainfo_json_text = await async_subprocess(f"mediainfo '{download_path}' --Output=JSON")
        
        if not mediainfo_json_text:
            LOGGER.warning(f"⚠️ MediaInfo produced no output for {chunk_type} chunk")
            return None
        
        try:
            metadata = json.loads(mediainfo_json_text)
            tracks = metadata.get("media", {}).get("track", [])
            LOGGER.debug(f"📊 {chunk_type} chunk: {len(tracks)} tracks found")
            return metadata
        except json.JSONDecodeError as e:
            LOGGER.warning(f"⚠️ MediaInfo JSON parse failed for {chunk_type} chunk: {e}")
            return None
        
    except Exception as e:
        LOGGER.error(f"💥 {chunk_type} chunk processing error: {e}")
        return None
    finally:
        if download_path and os.path.exists(download_path):
            try:
                os.remove(download_path)
            except:
                pass

async def download_head_chunk(client, message, download_path, size_mb):
    """Download head chunk from beginning of file"""
    try:
        chunk_size = 100 * 1024  # 100KB per chunk
        max_chunks = int((size_mb * 1024 * 1024) / chunk_size)
        
        chunk_count = 0
        async for chunk in client.stream_media(message, limit=max_chunks):
            with open(download_path, "ab") as f:
                f.write(chunk)
            chunk_count += 1
            if chunk_count >= max_chunks:
                break
        
        if chunk_count > 0 and os.path.exists(download_path):
            file_size = os.path.getsize(download_path)
            LOGGER.debug(f"✅ Head chunk downloaded: {file_size/1024/1024:.1f}MB")
            return True
        
        return False
        
    except Exception as e:
        LOGGER.error(f"💥 Head chunk download error: {e}")
        return False

async def download_tail_chunk(client, message, download_path, size_mb, total_size):
    """Download tail chunk from end of file"""
    try:
        chunk_size = 100 * 1024  # 100KB per chunk
        tail_size = size_mb * 1024 * 1024
        
        if total_size <= tail_size:
            # File is smaller than tail size, download all
            return await download_head_chunk(client, message, download_path, total_size // (1024 * 1024) + 1)
        
        # Calculate chunks to skip for tail
        start_offset = total_size - tail_size
        chunks_to_skip = int(start_offset / chunk_size)
        chunks_to_download = int(tail_size / chunk_size)
        
        LOGGER.debug(f"📊 Tail: skip {chunks_to_skip}, download {chunks_to_download}")
        
        chunk_count = 0
        downloaded_count = 0
        
        async for chunk in client.stream_media(message, limit=chunks_to_skip + chunks_to_download):
            chunk_count += 1
            
            # Skip chunks until tail section
            if chunk_count <= chunks_to_skip:
                continue
            
            # Download tail chunks
            with open(download_path, "ab") as f:
                f.write(chunk)
            downloaded_count += 1
            
            if downloaded_count >= chunks_to_download:
                break
        
        if downloaded_count > 0 and os.path.exists(download_path):
            file_size = os.path.getsize(download_path)
            LOGGER.debug(f"✅ Tail chunk downloaded: {file_size/1024/1024:.1f}MB")
            return True
        
        return False
        
    except Exception as e:
        LOGGER.error(f"💥 Tail chunk download error: {e}")
        return False

def merge_mediainfo_metadata(head_metadata, tail_metadata):
    """Intelligently merge MediaInfo metadata from head and tail chunks"""
    try:
        LOGGER.debug("🔗 Merging head and tail metadata")
        
        if not head_metadata and not tail_metadata:
            return None
        
        if not head_metadata:
            LOGGER.debug("📊 Using tail metadata only")
            return tail_metadata
        
        if not tail_metadata:
            LOGGER.debug("📊 Using head metadata only") 
            return head_metadata
        
        # Start with head metadata as base
        merged = json.loads(json.dumps(head_metadata))  # Deep copy
        
        head_tracks = head_metadata.get("media", {}).get("track", [])
        tail_tracks = tail_metadata.get("media", {}).get("track", [])
        
        LOGGER.debug(f"📊 Head tracks: {len(head_tracks)}, Tail tracks: {len(tail_tracks)}")
        
        # Merge tracks intelligently
        merged_tracks = []
        added_stream_types = set()
        
        # Add all head tracks
        for track in head_tracks:
            track_type = track.get("@type", "").lower()
            merged_tracks.append(track)
            added_stream_types.add(track_type)
        
        # Add missing stream types from tail
        for track in tail_tracks:
            track_type = track.get("@type", "").lower()
            
            # Add if stream type not already present
            if track_type not in added_stream_types:
                merged_tracks.append(track)
                added_stream_types.add(track_type)
                LOGGER.debug(f"📊 Added {track_type} track from tail")
            else:
                # Update existing track with missing fields from tail
                for existing_track in merged_tracks:
                    if existing_track.get("@type", "").lower() == track_type:
                        # Merge missing fields
                        for key, value in track.items():
                            if key not in existing_track or not existing_track[key]:
                                existing_track[key] = value
                                LOGGER.debug(f"📊 Updated {key} in {track_type} track from tail")
        
        # Update merged metadata
        if "media" not in merged:
            merged["media"] = {}
        merged["media"]["track"] = merged_tracks
        
        LOGGER.info(f"✅ Merged metadata: {len(merged_tracks)} tracks, types: {list(added_stream_types)}")
        return merged
        
    except Exception as e:
        LOGGER.error(f"💥 Metadata merge error: {e}")
        return head_metadata or tail_metadata

def has_video_audio_streams(metadata):
    """Check if metadata contains actual video or audio streams"""
    try:
        if not metadata:
            return False
        
        tracks = metadata.get("media", {}).get("track", [])
        
        has_video = False
        has_audio = False
        
        for track in tracks:
            track_type = track.get("@type", "").lower()
            if track_type == "video":
                has_video = True
            elif track_type == "audio":
                has_audio = True
        
        result = has_video or has_audio
        LOGGER.debug(f"📊 Stream check: Video={has_video}, Audio={has_audio}, HasStreams={result}")
        return result
        
    except Exception as e:
        LOGGER.error(f"💥 Stream check error: {e}")
        return False

async def update_caption_with_metadata(message, metadata):
    """Update caption with MediaInfo metadata"""
    try:
        caption_data = extract_caption_metadata(metadata)
        if not caption_data:
            LOGGER.warning("⚠️ No caption data extracted")
            return False
        
        current_caption = message.caption or ""
        enhanced_caption = generate_mediainfo_caption(current_caption, caption_data)
        
        if current_caption == enhanced_caption:
            LOGGER.warning("⚠️ No caption changes generated")
            return False
        
        return await safe_edit_caption(message, current_caption, enhanced_caption)
        
    except Exception as e:
        LOGGER.error(f"💥 Caption update error: {e}")
        return False

async def async_subprocess(cmd):
    """Run subprocess command"""
    try:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        return stdout.decode() if stdout else ""
    except Exception as e:
        LOGGER.error(f"Subprocess error: {e}")
        return ""

def extract_caption_metadata(mediainfo_json):
    """Extract metadata from MediaInfo JSON"""
    try:
        tracks = mediainfo_json.get("media", {}).get("track", [])
        
        video_info = None
        audio_tracks = []
        
        for track in tracks:
            track_type = track.get("@type", "").lower()
            
            if track_type == "video" and not video_info:
                codec = track.get("Format", "Unknown")
                width = track.get("Width")
                height = track.get("Height")
                
                video_info = {
                    "codec": codec,
                    "width": int(width) if width else None,
                    "height": int(height) if height else None
                }
                
            elif track_type == "audio":
                codec = track.get("Format", "Unknown")
                language = track.get("Language", "Unknown")
                channels = track.get("Channels")
                
                audio_tracks.append({
                    "codec": codec,
                    "language": language,
                    "channels": int(channels) if channels else 1
                })
        
        return {
            "video": video_info,
            "audio": audio_tracks
        }
        
    except Exception as e:
        LOGGER.error(f"Metadata extraction error: {e}")
        return None

def generate_mediainfo_caption(original_caption, metadata):
    """Generate enhanced caption"""
    try:
        enhanced = original_caption.strip() if original_caption else ""
        mediainfo_lines = []
        
        # Video info
        video = metadata.get("video")
        if video and video.get("codec"):
            codec = video["codec"]
            height = video.get("height")
            
            resolution = ""
            if height:
                if height >= 2160:
                    resolution = "4K"
                elif height >= 1440:
                    resolution = "1440p"
                elif height >= 1080:
                    resolution = "1080p"
                elif height >= 720:
                    resolution = "720p"
                else:
                    resolution = f"{height}p"
            
            video_line = f"Video: {codec}"
            if resolution:
                video_line += f" {resolution}"
            
            mediainfo_lines.append(video_line)
        
        # Audio info
        audio_tracks = metadata.get("audio", [])
        if audio_tracks:
            count = len(audio_tracks)
            
            languages = []
            for audio in audio_tracks:
                lang = audio.get("language", "Unknown").upper()
                if lang and lang not in ["UNKNOWN", "UND"] and lang not in languages:
                    lang_map = {"EN": "ENG", "HI": "HIN", "ES": "SPA"}
                    lang = lang_map.get(lang, lang)
                    languages.append(lang)
            
            audio_line = f"Audio: {count}"
            if languages:
                audio_line += f" ({', '.join(languages[:3])})"
            
            mediainfo_lines.append(audio_line)
        
        # Combine
        if mediainfo_lines:
            mediainfo_section = "\n\n" + "\n".join(mediainfo_lines)
            enhanced_caption = enhanced + mediainfo_section
            
            if len(enhanced_caption) > 1020:
                max_original = 1020 - len(mediainfo_section) - 5
                if max_original > 0:
                    enhanced_caption = enhanced[:max_original] + "..." + mediainfo_section
                else:
                    enhanced_caption = mediainfo_section
            
            return enhanced_caption
        
        return enhanced
        
    except Exception as e:
        LOGGER.error(f"Caption generation error: {e}")
        return original_caption or ""

# Helper functions
async def has_media(msg):
    return bool(msg.video or msg.audio or msg.document)

async def already_has_mediainfo(msg):
    caption = msg.caption or ""
    return "Video:" in caption and "Audio:" in caption

async def safe_edit_caption(msg, current_caption, new_caption):
    try:
        if current_caption == new_caption:
            return False
        
        if "Video:" not in new_caption and "Audio:" not in new_caption:
            return False
        
        await TgClient.user.edit_message_caption(
            chat_id=msg.chat.id,
            message_id=msg.id,
            caption=new_caption
        )
        return True
        
    except MessageNotModified:
        return False
    except Exception as e:
        LOGGER.error(f"Caption edit error: {e}")
        return False

async def get_target_channels(message):
    try:
        if len(message.command) > 1:
            channel_id = message.command[1]
            if channel_id.startswith('-100'):
                return [int(channel_id)]
            elif channel_id.isdigit():
                return [int(f"-100{channel_id}")]
            else:
                return [channel_id]
        return []
    except:
        return []

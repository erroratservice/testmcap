"""
MediaInfo update using WZML-X WZV3 proven approach
"""

import asyncio
import logging
import os
import tempfile
from datetime import datetime
from aiofiles import open as aiopen
from aiofiles.os import remove as aioremove
from pyrogram.errors import MessageNotModified
from bot.core.client import TgClient
from bot.helpers.message_utils import send_message, edit_message

LOGGER = logging.getLogger(__name__)

# WZML-X WZV3 Configuration
FULL_DOWNLOAD_LIMIT = 50 * 1024 * 1024  # 50MB like wzv3
PARTIAL_CHUNK_LIMIT = 5  # 5 chunks like wzv3

async def updatemediainfo_handler(client, message):
    """WZML-X WZV3 style handler"""
    try:
        LOGGER.info("🚀 Starting WZML-X WZV3 style MediaInfo processing")
        
        channels = await get_target_channels(message)
        if not channels:
            await send_message(message, "❌ **Usage:** `/updatemediainfo -1001234567890`")
            return
        
        for channel_id in channels:
            await process_channel_wzv3_style(channel_id, message)
            
    except Exception as e:
        LOGGER.error(f"💥 Handler error: {e}", exc_info=True)
        await send_message(message, f"❌ **Error:** {e}")

async def process_channel_wzv3_style(channel_id, message):
    """Process channel using WZML-X WZV3 methodology"""
    try:
        chat = await TgClient.user.get_chat(channel_id)
        LOGGER.info(f"✅ Processing channel: {chat.title}")
        
        progress_msg = await send_message(message,
            f"🔄 **Processing:** {chat.title}\n"
            f"📊 **Method:** WZML-X WZV3 Style\n"
            f"🎯 **Strategy:** 50MB Full | 5-Chunk Partial\n"
            f"🔧 **Tool:** MediaInfo CLI\n"
            f"🔍 **Status:** Starting...")
        
        stats = {"processed": 0, "errors": 0, "skipped": 0, 
                "full_downloads": 0, "partial_downloads": 0, "total": 0, "media": 0}
        
        message_count = 0
        async for msg in TgClient.user.get_chat_history(chat_id=channel_id, limit=100):
            message_count += 1
            stats["total"] += 1
            
            if not await has_media(msg):
                stats["skipped"] += 1
                continue
            
            if await already_has_mediainfo(msg):
                stats["skipped"] += 1
                continue
            
            stats["media"] += 1
            LOGGER.info(f"🎯 Processing media message {msg.id}")
            
            try:
                success, method = await process_message_wzv3_style(TgClient.user, msg)
                if success:
                    stats["processed"] += 1
                    if method == "full":
                        stats["full_downloads"] += 1
                    elif method == "partial":
                        stats["partial_downloads"] += 1
                    LOGGER.info(f"✅ Updated message {msg.id} using {method}")
                else:
                    stats["errors"] += 1
                    LOGGER.warning(f"⚠️ Failed to update message {msg.id}")
            except Exception as e:
                LOGGER.error(f"❌ Error processing {msg.id}: {e}")
                stats["errors"] += 1
            
            # Progress update
            if message_count % 5 == 0:
                await edit_message(progress_msg,
                    f"🔄 **Processing:** {chat.title}\n"
                    f"📊 **Messages:** {stats['total']} | **Media:** {stats['media']}\n"
                    f"✅ **Updated:** {stats['processed']} | ❌ **Errors:** {stats['errors']}\n"
                    f"📥 **Full:** {stats['full_downloads']} | 📦 **Partial:** {stats['partial_downloads']}")
                await asyncio.sleep(0.5)
        
        # Final results
        final_stats = (
            f"✅ **Completed:** {chat.title}\n"
            f"📊 **Total Messages:** {stats['total']}\n"
            f"📁 **Media Found:** {stats['media']}\n"
            f"✅ **Updated:** {stats['processed']} files\n"
            f"❌ **Errors:** {stats['errors']} files\n"
            f"⏭️ **Skipped:** {stats['skipped']} files\n\n"
            f"📥 **Full Downloads:** {stats['full_downloads']}\n"
            f"📦 **Partial Downloads:** {stats['partial_downloads']}"
        )
        
        await edit_message(progress_msg, final_stats)
        LOGGER.info(f"🎉 WZML-X WZV3 style processing complete")
        
    except Exception as e:
        LOGGER.error(f"💥 Channel processing error: {e}")

async def process_message_wzv3_style(client, message):
    """Process message using exact WZML-X WZV3 approach"""
    temp_file_path = None
    try:
        # Get media info
        media = message.video or message.audio or message.document
        if not media:
            return False, "none"
        
        filename = str(media.file_name) if media.file_name else f"media_{message.id}"
        file_size = media.file_size
        
        LOGGER.info(f"📁 Processing: {filename} ({file_size/1024/1024:.1f}MB)")
        
        # Create mediainfo directory (like wzv3)
        mediainfo_dir = "mediainfo"
        if not os.path.exists(mediainfo_dir):
            os.makedirs(mediainfo_dir)
        
        # Create temp file path
        safe_filename = filename.replace('/', '_').replace(' ', '_')
        temp_file_path = os.path.join(mediainfo_dir, f"wzv3_{message.id}_{safe_filename}")
        
        # WZML-X WZV3 download strategy
        if file_size <= FULL_DOWNLOAD_LIMIT:
            LOGGER.info(f"📥 Full download (WZV3 style): {file_size/1024/1024:.1f}MB <= 50MB")
            
            # Full download like wzv3
            try:
                await asyncio.wait_for(
                    message.download(temp_file_path), 
                    timeout=300.0  # 5 minute timeout
                )
                method = "full"
            except asyncio.TimeoutError:
                LOGGER.warning(f"⚠️ Full download timed out")
                return False, "timeout"
                
        else:
            LOGGER.info(f"📦 Partial download (WZV3 style): 5 chunks")
            
            # Partial download exactly like wzv3
            try:
                chunk_count = 0
                async for chunk in client.stream_media(message, limit=PARTIAL_CHUNK_LIMIT):
                    async with aiopen(temp_file_path, "ab") as f:
                        await f.write(chunk)
                    chunk_count += 1
                
                if chunk_count == 0:
                    return False, "no_chunks"
                    
                method = "partial"
                LOGGER.info(f"✅ Downloaded {chunk_count} chunks")
                
            except Exception as e:
                LOGGER.error(f"❌ Partial download error: {e}")
                return False, "download_error"
        
        # Verify file exists
        if not os.path.exists(temp_file_path):
            return False, "file_not_found"
        
        downloaded_size = os.path.getsize(temp_file_path)
        LOGGER.info(f"✅ Downloaded: {downloaded_size/1024/1024:.1f}MB")
        
        # Extract MediaInfo using wzv3 approach
        success = await extract_mediainfo_wzv3_style(temp_file_path, message)
        return success, method
        
    except Exception as e:
        LOGGER.error(f"💥 WZV3 style processing error: {e}")
        return False, "error"
    finally:
        # Cleanup like wzv3
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                await aioremove(temp_file_path)
                LOGGER.debug(f"🗑️ Cleaned up: {temp_file_path}")
            except:
                pass

async def extract_mediainfo_wzv3_style(file_path, message):
    """Extract MediaInfo exactly like WZML-X WZV3"""
    try:
        LOGGER.debug(f"🔍 Running MediaInfo CLI on: {file_path}")
        
        # Run MediaInfo CLI exactly like wzv3
        proc = await asyncio.create_subprocess_shell(
            f'mediainfo "{file_path}"',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30.0)
        
        if proc.returncode != 0:
            LOGGER.warning(f"⚠️ MediaInfo returned code: {proc.returncode}")
            if stderr:
                LOGGER.warning(f"MediaInfo stderr: {stderr.decode()}")
        
        if not stdout:
            LOGGER.warning("⚠️ MediaInfo produced no output")
            return False
        
        mediainfo_output = stdout.decode()
        LOGGER.debug(f"📊 MediaInfo output length: {len(mediainfo_output)}")
        
        # Parse MediaInfo output like wzv3 parseinfo function
        video_info, audio_info = parse_mediainfo_wzv3_style(mediainfo_output)
        
        if not video_info and not audio_info:
            LOGGER.warning("⚠️ No video or audio streams found")
            return False
        
        LOGGER.info(f"✅ MediaInfo extracted: Video={bool(video_info)}, Audio={bool(audio_info)}")
        
        # Update caption
        return await update_caption_wzv3_style(message, video_info, audio_info)
        
    except asyncio.TimeoutError:
        LOGGER.warning("⚠️ MediaInfo CLI timed out")
        return False
    except Exception as e:
        LOGGER.error(f"💥 MediaInfo extraction error: {e}")
        return False

def parse_mediainfo_wzv3_style(mediainfo_output):
    """Parse MediaInfo output like wzv3"""
    try:
        video_info = None
        audio_info = None
        
        current_section = None
        lines = mediainfo_output.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Detect sections
            if line.startswith('Video'):
                current_section = 'video'
                continue
            elif line.startswith('Audio'):
                current_section = 'audio'
                continue
            elif line.startswith('General') or line.startswith('Text') or line.startswith('Menu'):
                current_section = 'other'
                continue
            
            # Parse video info
            if current_section == 'video' and not video_info:
                codec = None
                width = None
                height = None
                
                if 'Format' in line and ':' in line:
                    codec = line.split(':')[1].strip()
                elif 'Width' in line and ':' in line:
                    try:
                        width = int(line.split(':')[1].strip().split()[0])
                    except:
                        pass
                elif 'Height' in line and ':' in line:
                    try:
                        height = int(line.split(':')[1].strip().split()[0])
                    except:
                        pass
                
                if codec or width or height:
                    video_info = {'codec': codec, 'width': width, 'height': height}
            
            # Parse audio info  
            elif current_section == 'audio' and not audio_info:
                if 'Format' in line and ':' in line:
                    codec = line.split(':')[1].strip()
                    audio_info = {'codec': codec}
        
        return video_info, audio_info
        
    except Exception as e:
        LOGGER.error(f"💥 MediaInfo parsing error: {e}")
        return None, None

async def update_caption_wzv3_style(message, video_info, audio_info):
    """Update caption like wzv3 style"""
    try:
        current_caption = message.caption or ""
        mediainfo_lines = []
        
        # Video line
        if video_info and video_info.get('codec'):
            codec = video_info['codec']
            height = video_info.get('height')
            
            resolution = ""
            if height:
                try:
                    h = int(height)
                    if h >= 2160:
                        resolution = "4K"
                    elif h >= 1440:
                        resolution = "1440p"
                    elif h >= 1080:
                        resolution = "1080p"
                    elif h >= 720:
                        resolution = "720p"
                    else:
                        resolution = f"{h}p"
                except:
                    pass
            
            video_line = f"Video: {codec}"
            if resolution:
                video_line += f" {resolution}"
            mediainfo_lines.append(video_line)
        
        # Audio line
        if audio_info and audio_info.get('codec'):
            audio_line = f"Audio: {audio_info['codec']}"
            mediainfo_lines.append(audio_line)
        
        if not mediainfo_lines:
            LOGGER.warning("⚠️ No MediaInfo lines generated")
            return False
        
        # Create enhanced caption
        enhanced = current_caption.strip()
        mediainfo_section = "\n\n" + "\n".join(mediainfo_lines)
        enhanced_caption = enhanced + mediainfo_section
        
        # Telegram length limit
        if len(enhanced_caption) > 1020:
            max_original = 1020 - len(mediainfo_section) - 5
            if max_original > 0:
                enhanced_caption = enhanced[:max_original] + "..." + mediainfo_section
            else:
                enhanced_caption = mediainfo_section
        
        # Update caption if changed
        if current_caption == enhanced_caption:
            LOGGER.warning("⚠️ Caption unchanged")
            return False
        
        try:
            await TgClient.user.edit_message_caption(
                chat_id=message.chat.id,
                message_id=message.id,
                caption=enhanced_caption
            )
            LOGGER.info("✅ Caption updated successfully")
            return True
            
        except MessageNotModified:
            LOGGER.info("ℹ️ Message not modified")
            return False
        
    except Exception as e:
        LOGGER.error(f"💥 Caption update error: {e}")
        return False

# Helper functions
async def has_media(msg):
    return bool(msg.video or msg.audio or msg.document)

async def already_has_mediainfo(msg):
    caption = msg.caption or ""
    return "Video:" in caption and "Audio:" in caption

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

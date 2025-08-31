"""
MediaInfo update using WZML-X WZV3 proven approach with enhanced video quality detection
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
MEDIAINFO_TIMEOUT = 30  # 30 seconds timeout for MediaInfo CLI

async def updatemediainfo_handler(client, message):
    """WZML-X WZV3 style handler with enhanced video quality detection"""
    try:
        LOGGER.info("🚀 Starting WZML-X WZV3 style MediaInfo processing with video quality")
        
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
    """Process channel using WZML-X WZV3 proven methodology"""
    try:
        chat = await TgClient.user.get_chat(channel_id)
        LOGGER.info(f"✅ Processing channel: {chat.title}")
        
        progress_msg = await send_message(message,
            f"🔄 **Processing:** {chat.title}\n"
            f"📊 **Method:** WZML-X WZV3 Enhanced\n"
            f"🎯 **Strategy:** 50MB Full | 5-Chunk Partial\n"
            f"🔧 **Tool:** MediaInfo CLI\n"
            f"📺 **Features:** Video Quality Detection\n"
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
                success, method = await process_message_wzv3_enhanced(TgClient.user, msg)
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
        LOGGER.info(f"🎉 WZML-X WZV3 enhanced processing complete: {stats['processed']} updated")
        
    except Exception as e:
        LOGGER.error(f"💥 Channel processing error: {e}")

async def process_message_wzv3_enhanced(client, message):
    """Process message using WZML-X WZV3 approach with enhancements"""
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
        safe_filename = filename.replace('/', '_').replace(' ', '_').replace('(', '').replace(')', '')
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
        
        # Extract MediaInfo using enhanced wzv3 approach
        success = await extract_mediainfo_enhanced(temp_file_path, message)
        return success, method
        
    except Exception as e:
        LOGGER.error(f"💥 WZV3 enhanced processing error: {e}")
        return False, "error"
    finally:
        # Cleanup like wzv3
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                await aioremove(temp_file_path)
                LOGGER.debug(f"🗑️ Cleaned up: {temp_file_path}")
            except:
                pass

async def extract_mediainfo_enhanced(file_path, message):
    """Extract MediaInfo with enhanced video quality detection"""
    try:
        LOGGER.debug(f"🔍 Running enhanced MediaInfo CLI on: {file_path}")
        
        # Run MediaInfo CLI with timeout
        proc = await asyncio.create_subprocess_shell(
            f'mediainfo "{file_path}"',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=MEDIAINFO_TIMEOUT)
        except asyncio.TimeoutError:
            LOGGER.warning("⚠️ MediaInfo CLI timed out")
            proc.kill()
            return False
        
        if proc.returncode != 0:
            LOGGER.warning(f"⚠️ MediaInfo returned code: {proc.returncode}")
            if stderr:
                LOGGER.warning(f"MediaInfo stderr: {stderr.decode()}")
        
        if not stdout:
            LOGGER.warning("⚠️ MediaInfo produced no output")
            return False
        
        mediainfo_output = stdout.decode()
        LOGGER.debug(f"📊 MediaInfo output length: {len(mediainfo_output)}")
        
        # Debug: Show first few lines of MediaInfo output
        lines_preview = mediainfo_output.split('\n')[:10]
        LOGGER.debug("📊 MediaInfo preview:")
        for i, line in enumerate(lines_preview):
            LOGGER.debug(f"  {i+1}: {line}")
        
        # Parse MediaInfo output with enhanced parsing
        video_info, audio_info = parse_mediainfo_enhanced(mediainfo_output)
        
        if not video_info and not audio_info:
            LOGGER.warning("⚠️ No video or audio streams found")
            return False
        
        LOGGER.info(f"✅ MediaInfo extracted: Video={bool(video_info)}, Audio={bool(audio_info)}")
        
        # Update caption with enhanced generation
        return await update_caption_enhanced(message, video_info, audio_info)
        
    except Exception as e:
        LOGGER.error(f"💥 Enhanced MediaInfo extraction error: {e}")
        return False

def parse_mediainfo_enhanced(mediainfo_output):
    """Enhanced MediaInfo parsing with robust video quality extraction"""
    try:
        LOGGER.debug("🔍 Enhanced parsing MediaInfo output")
        
        video_info = {}
        audio_info = {}
        
        current_section = None
        lines = mediainfo_output.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Detect sections - more robust detection
            if line.startswith('Video') or (line.startswith('Video #') and '#' in line):
                current_section = 'video'
                LOGGER.debug("📹 Found Video section")
                continue
            elif line.startswith('Audio') or (line.startswith('Audio #') and '#' in line):
                current_section = 'audio'  
                LOGGER.debug("🎵 Found Audio section")
                continue
            elif any(line.startswith(x) for x in ['General', 'Text', 'Menu', 'Other', 'Image']):
                current_section = 'other'
                continue
            
            # Enhanced video parsing
            if current_section == 'video' and ':' in line:
                key_value = line.split(':', 1)
                if len(key_value) == 2:
                    key = key_value[0].strip()
                    value = key_value[1].strip()
                    
                    # Extract video codec - multiple possible fields
                    if key in ['Format', 'Codec ID', 'Codec', 'Format/Info']:
                        if not video_info.get('codec'):
                            # Clean codec name
                            codec = value.split('/')[0].split('(')[0].strip()
                            video_info['codec'] = codec
                            LOGGER.debug(f"📹 Video codec: {codec}")
                    
                    # Extract width - handle various formats
                    elif key in ['Width']:
                        try:
                            # Handle "1 920 pixels", "1920 px", "1920", "1920 (1920)"
                            width_str = value.replace(' ', '').replace('pixels', '').replace('px', '')
                            width_str = width_str.split('(')[0]  # Remove parenthetical info
                            video_info['width'] = int(''.join(filter(str.isdigit, width_str)))
                            LOGGER.debug(f"📹 Video width: {video_info['width']}")
                        except Exception as e:
                            LOGGER.debug(f"Width parse error: {e}")
                    
                    # Extract height - handle various formats
                    elif key in ['Height']:
                        try:
                            # Handle "1 080 pixels", "1080 px", "1080", "1080 (1080)"
                            height_str = value.replace(' ', '').replace('pixels', '').replace('px', '')
                            height_str = height_str.split('(')[0]  # Remove parenthetical info
                            video_info['height'] = int(''.join(filter(str.isdigit, height_str)))
                            LOGGER.debug(f"📹 Video height: {video_info['height']}")
                        except Exception as e:
                            LOGGER.debug(f"Height parse error: {e}")
                    
                    # Alternative resolution detection from display aspect ratio
                    elif key in ['Display aspect ratio'] and 'x' in value:
                        try:
                            if '(' in value and 'x' in value:
                                # Extract resolution from "(1920x1080)" format
                                res_part = value.split('(')[1].split(')')[0]
                                if 'x' in res_part:
                                    width, height = res_part.split('x')
                                    if not video_info.get('width'):
                                        video_info['width'] = int(width.strip())
                                    if not video_info.get('height'):
                                        video_info['height'] = int(height.strip())
                        except:
                            pass
                    
                    # Extract frame rate
                    elif key in ['Frame rate']:
                        try:
                            fps = float(value.split()[0])
                            video_info['fps'] = fps
                        except:
                            pass
            
            # Enhanced audio parsing
            elif current_section == 'audio' and ':' in line:
                key_value = line.split(':', 1)
                if len(key_value) == 2:
                    key = key_value[0].strip()
                    value = key_value[1].strip()
                    
                    if key in ['Format', 'Codec ID', 'Codec']:
                        if not audio_info.get('codec'):
                            # Clean audio codec name
                            codec = value.split('/')[0].split('(')[0].strip()
                            audio_info['codec'] = codec
                            LOGGER.debug(f"🎵 Audio codec: {codec}")
                    
                    elif key in ['Language']:
                        audio_info['language'] = value
                        LOGGER.debug(f"🎵 Audio language: {value}")
                    
                    elif key in ['Channel(s)', 'Channels']:
                        try:
                            # Handle "6 channels", "2", "5.1", etc.
                            channels_str = value.split()[0]
                            audio_info['channels'] = int(channels_str)
                            LOGGER.debug(f"🎵 Audio channels: {channels_str}")
                        except:
                            pass
                    
                    elif key in ['Sampling rate', 'Sample rate']:
                        try:
                            # Handle "48.0 kHz", "44100 Hz", etc.
                            rate_str = value.replace('kHz', '').replace('Hz', '').strip()
                            audio_info['sample_rate'] = rate_str
                        except:
                            pass
        
        # Log final extracted info
        LOGGER.info(f"✅ Enhanced video info: {video_info}")
        LOGGER.info(f"✅ Enhanced audio info: {audio_info}")
        
        return video_info if video_info else None, audio_info if audio_info else None
        
    except Exception as e:
        LOGGER.error(f"💥 Enhanced MediaInfo parsing error: {e}")
        return None, None

async def update_caption_enhanced(message, video_info, audio_info):
    """Enhanced caption generation with comprehensive video quality detection"""
    try:
        current_caption = message.caption or ""
        mediainfo_lines = []
        
        # Enhanced Video line with comprehensive quality detection
        if video_info and video_info.get('codec'):
            codec = video_info['codec']
            width = video_info.get('width')
            height = video_info.get('height')
            fps = video_info.get('fps')
            
            LOGGER.debug(f"📹 Processing video: codec={codec}, width={width}, height={height}, fps={fps}")
            
            # Determine resolution/quality with comprehensive detection
            quality = None
            if height:
                try:
                    h = int(height)
                    if h >= 2160:
                        quality = "4K"
                    elif h >= 1440:
                        quality = "1440p"
                    elif h >= 1080:
                        quality = "1080p"
                    elif h >= 720:
                        quality = "720p"
                    elif h >= 576:
                        quality = "576p"
                    elif h >= 480:
                        quality = "480p"
                    elif h >= 360:
                        quality = "360p"
                    elif h >= 240:
                        quality = "240p"
                    else:
                        quality = f"{h}p"
                    LOGGER.info(f"📹 Detected video quality: {quality}")
                except Exception as e:
                    LOGGER.warning(f"⚠️ Quality detection error: {e}")
            
            # Build comprehensive video line
            video_line = f"Video: {codec.upper()}"
            
            # Add quality/resolution
            if quality:
                video_line += f" {quality}"
            elif width and height:
                video_line += f" {width}x{height}"
            
            # Add frame rate if available
            if fps and fps > 0:
                if fps == int(fps):
                    video_line += f" {int(fps)}fps"
                else:
                    video_line += f" {fps:.1f}fps"
            
            mediainfo_lines.append(video_line)
            LOGGER.info(f"📹 Generated enhanced video line: {video_line}")
        
        # Enhanced Audio line with comprehensive info
        if audio_info and audio_info.get('codec'):
            codec = audio_info['codec']
            language = audio_info.get('language', '').upper()
            channels = audio_info.get('channels')
            sample_rate = audio_info.get('sample_rate')
            
            # Build comprehensive audio line
            audio_line = f"Audio: {codec.upper()}"
            
            # Add channel configuration
            if channels:
                if channels == 1:
                    audio_line += " Mono"
                elif channels == 2:
                    audio_line += " Stereo"
                elif channels == 6:
                    audio_line += " 5.1"
                elif channels == 8:
                    audio_line += " 7.1"
                else:
                    audio_line += f" {channels}ch"
            
            # Add language if available and meaningful
            if language and language not in ['UNKNOWN', 'UND', 'UNDEFINED', 'N/A', 'NULL', '']:
                # Standardize language codes
                lang_map = {
                    'EN': 'ENG', 'ENGLISH': 'ENG',
                    'HI': 'HIN', 'HINDI': 'HIN', 
                    'ES': 'SPA', 'SPANISH': 'SPA',
                    'FR': 'FRA', 'FRENCH': 'FRA',
                    'DE': 'GER', 'GERMAN': 'GER',
                    'IT': 'ITA', 'ITALIAN': 'ITA',
                    'JA': 'JPN', 'JAPANESE': 'JPN',
                    'KO': 'KOR', 'KOREAN': 'KOR',
                    'ZH': 'CHI', 'CHINESE': 'CHI',
                    'AR': 'ARA', 'ARABIC': 'ARA',
                    'RU': 'RUS', 'RUSSIAN': 'RUS',
                    'PT': 'POR', 'PORTUGUESE': 'POR'
                }
                display_lang = lang_map.get(language, language)
                audio_line += f" ({display_lang})"
            
            mediainfo_lines.append(audio_line)
            LOGGER.info(f"🎵 Generated enhanced audio line: {audio_line}")
        
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
        
        LOGGER.debug(f"📝 Final enhanced caption: {enhanced_caption}")
        
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
            LOGGER.info("✅ Enhanced caption updated successfully with video quality")
            return True
            
        except MessageNotModified:
            LOGGER.info("ℹ️ Message not modified by Telegram")
            return False
        
    except Exception as e:
        LOGGER.error(f"💥 Enhanced caption update error: {e}")
        return False

# Helper functions
async def has_media(msg):
    """Check if message has media"""
    return bool(msg.video or msg.audio or msg.document)

async def already_has_mediainfo(msg):
    """Check if message already has MediaInfo in caption"""
    caption = msg.caption or ""
    return "Video:" in caption and "Audio:" in caption

async def get_target_channels(message):
    """Extract channel IDs from command"""
    try:
        if len(message.command) > 1:
            channel_id = message.command[1]
            if channel_id.startswith('-100'):
                return [int(channel_id)]
            elif channel_id.isdigit():
                return [int(f"-100{channel_id}")]
            else:
                return [channel_id]  # Username
        return []
    except Exception as e:
        LOGGER.error(f"Channel parsing error: {e}")
        return []

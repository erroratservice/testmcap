"""
Clean configuration management for Media Indexing Bot
"""

import os
from dotenv import load_dotenv

class Config:
    """Essential configuration for media indexing operations"""
    
    # Required settings
    BOT_TOKEN = None
    TELEGRAM_API = None
    TELEGRAM_HASH = None
    USER_SESSION_STRING = None
    OWNER_ID = None
    
    # Optional settings
    DATABASE_URL = None
    AUTHORIZED_CHATS = None
    INDEX_CHANNEL_ID = None
    
    # Bot settings
    TIMEZONE = None
    MEDIAINFO_ENABLED = None
    MAX_CONCURRENT_TASKS = None
    DOWNLOAD_DIR = None
    CMD_SUFFIX = None
    AUTHOR_NAME = None
    AUTHOR_URL = None
    USE_TVMAZE_TITLES = None # New setting
    
    @classmethod
    def load(cls):
        """Load environment variables from config.env"""
        load_dotenv('config.env')
        cls._set_attributes()
        
    @classmethod
    def _set_attributes(cls):
        """Set class attributes from environment variables"""
        cls.BOT_TOKEN = os.getenv('BOT_TOKEN', '')
        cls.TELEGRAM_API = int(os.getenv('TELEGRAM_API', '0'))
        cls.TELEGRAM_HASH = os.getenv('TELEGRAM_HASH', '')
        cls.USER_SESSION_STRING = os.getenv('USER_SESSION_STRING', '')
        cls.OWNER_ID = int(os.getenv('OWNER_ID', '0'))
        cls.DATABASE_URL = os.getenv('DATABASE_URL', '')
        cls.AUTHORIZED_CHATS = os.getenv('AUTHORIZED_CHATS', '')
        cls.INDEX_CHANNEL_ID = int(os.getenv('INDEX_CHANNEL_ID', '0'))
        cls.TIMEZONE = os.getenv('TIMEZONE', 'Asia/Kolkata')
        cls.MEDIAINFO_ENABLED = os.getenv('MEDIAINFO_ENABLED', 'True').lower() == 'true'
        cls.MAX_CONCURRENT_TASKS = int(os.getenv('MAX_CONCURRENT_TASKS', '5'))
        cls.DOWNLOAD_DIR = os.getenv('DOWNLOAD_DIR', '/tmp/mediainfo/')
        cls.CMD_SUFFIX = os.getenv('CMD_SUFFIX', '')
        cls.AUTHOR_NAME = os.getenv('AUTHOR_NAME', 'Media Manager Bot')
        cls.AUTHOR_URL = os.getenv('AUTHOR_URL', 'https://t.me/MediaManagerBot')
        # Add the new setting
        cls.USE_TVMAZE_TITLES = os.getenv('USE_TVMAZE_TITLES', 'True').lower() == 'true'

    @classmethod
    def set(cls, key, value):
        """Dynamically sets a configuration attribute."""
        if hasattr(cls, key):
            setattr(cls, key, value)
            return True
        return False
        
    @classmethod
    def validate(cls):
        """Validate essential configuration"""
        required_vars = {
            'BOT_TOKEN': cls.BOT_TOKEN,
            'TELEGRAM_API': cls.TELEGRAM_API,
            'TELEGRAM_HASH': cls.TELEGRAM_HASH,
            'USER_SESSION_STRING': cls.USER_SESSION_STRING,
            'OWNER_ID': cls.OWNER_ID
        }
        
        missing = [key for key, value in required_vars.items() 
                  if not value or (isinstance(value, int) and value == 0)]
        
        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")

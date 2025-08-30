"""
Clean configuration management for Media Indexing Bot
"""

import os
from dotenv import load_dotenv

class Config:
    """Essential configuration for media indexing operations"""
    
    # ================ REQUIRED SETTINGS ================
    BOT_TOKEN = os.getenv('BOT_TOKEN', '')
    TELEGRAM_API = int(os.getenv('TELEGRAM_API', '0'))
    TELEGRAM_HASH = os.getenv('TELEGRAM_HASH', '')
    USER_SESSION_STRING = os.getenv('USER_SESSION_STRING', '')
    OWNER_ID = int(os.getenv('OWNER_ID', '0'))
    
    # ================ OPTIONAL SETTINGS ================
    DATABASE_URL = os.getenv('DATABASE_URL', '')
    AUTHORIZED_CHATS = os.getenv('AUTHORIZED_CHATS', '')
    INDEX_CHANNEL_ID = int(os.getenv('INDEX_CHANNEL_ID', '0'))
    
    # ================ BOT SETTINGS ================
    TIMEZONE = os.getenv('TIMEZONE', 'Asia/Kolkata')
    MEDIAINFO_ENABLED = os.getenv('MEDIAINFO_ENABLED', 'True').lower() == 'true'
    MAX_CONCURRENT_TASKS = int(os.getenv('MAX_CONCURRENT_TASKS', '5'))
    
    # ================ PATHS ================
    DOWNLOAD_DIR = os.getenv('DOWNLOAD_DIR', '/tmp/mediainfo/')
    
    @classmethod
    def load(cls):
        """Load environment variables from .env file"""
        load_dotenv('config.env')
        
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
        
        missing = [key for key, value in required_vars.items() if not value]
        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")
          

"""
Enhanced configuration management with better file detection
"""

import os
from pathlib import Path
from dotenv import load_dotenv, find_dotenv

class Config:
    """Essential configuration for media indexing operations"""
    
    @classmethod
    def load(cls):
        """Load environment variables with multiple fallback methods"""
        # Method 1: Try to find config.env in current directory and parents
        config_paths = [
            'config.env',
            '.env', 
            Path(__file__).parent.parent.parent / 'config.env',  # Project root
            Path(__file__).parent.parent.parent / '.env'        # Project root
        ]
        
        loaded = False
        for config_path in config_paths:
            if Path(config_path).exists():
                result = load_dotenv(config_path, verbose=True)
                if result:
                    print(f"✅ Loaded configuration from: {config_path}")
                    loaded = True
                    break
        
        # Method 2: Try find_dotenv() as fallback
        if not loaded:
            dotenv_path = find_dotenv()
            if dotenv_path:
                load_dotenv(dotenv_path, verbose=True)
                print(f"✅ Loaded configuration from: {dotenv_path}")
                loaded = True
        
        # Method 3: Manual environment check
        if not loaded:
            print("⚠️ No .env file found, checking system environment variables")
        
        # Debug: Print what was loaded
        cls._debug_config()
    
    @classmethod
    def _debug_config(cls):
        """Debug method to show loaded configuration"""
        debug_vars = ['BOT_TOKEN', 'TELEGRAM_API', 'TELEGRAM_HASH', 'USER_SESSION_STRING', 'OWNER_ID']
        print("\n🔍 Configuration Debug:")
        for var in debug_vars:
            value = os.getenv(var, 'NOT_FOUND')
            # Hide sensitive values
            if value != 'NOT_FOUND' and var in ['BOT_TOKEN', 'TELEGRAM_HASH', 'USER_SESSION_STRING']:
                display_value = f"{value[:10]}..." if len(value) > 10 else "***"
            else:
                display_value = value
            print(f"  {var}: {display_value}")
        print()
    
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
    def validate(cls):
        """Validate essential configuration with detailed error messages"""
        required_vars = {
            'BOT_TOKEN': cls.BOT_TOKEN,
            'TELEGRAM_API': cls.TELEGRAM_API,
            'TELEGRAM_HASH': cls.TELEGRAM_HASH,
            'USER_SESSION_STRING': cls.USER_SESSION_STRING,
            'OWNER_ID': cls.OWNER_ID
        }
        
        missing = []
        empty = []
        
        for key, value in required_vars.items():
            if not value:
                missing.append(key)
            elif key == 'TELEGRAM_API' and value == 0:
                empty.append(key)
            elif isinstance(value, str) and value.strip() == '':
                empty.append(key)
        
        if missing or empty:
            error_msg = "Configuration validation failed:\n"
            if missing:
                error_msg += f"Missing required variables: {', '.join(missing)}\n"
            if empty:
                error_msg += f"Empty required variables: {', '.join(empty)}\n"
            error_msg += "\nPlease check your config.env file and ensure all required variables are set."
            raise ValueError(error_msg)

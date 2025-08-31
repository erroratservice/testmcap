"""
Fixed configuration management that loads attributes AFTER environment variables
"""

import os
from pathlib import Path
from dotenv import load_dotenv, find_dotenv

class Config:
    """Essential configuration for media indexing operations"""
    
    # Initialize as None - will be set after loading
    BOT_TOKEN = None
    TELEGRAM_API = None
    TELEGRAM_HASH = None
    USER_SESSION_STRING = None
    OWNER_ID = None
    DATABASE_URL = None
    AUTHORIZED_CHATS = None
    INDEX_CHANNEL_ID = None
    TIMEZONE = None
    MEDIAINFO_ENABLED = None
    MAX_CONCURRENT_TASKS = None
    DOWNLOAD_DIR = None
    
    @classmethod
    def load(cls):
        """Load environment variables and set class attributes"""
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
        
        # NOW SET CLASS ATTRIBUTES AFTER LOADING ENV VARS
        cls._set_attributes()
        
        # Debug: Print what was loaded
        cls._debug_config()
    
    @classmethod
    def _set_attributes(cls):
        """Set class attributes from environment variables AFTER loading"""
        # Required settings
        cls.BOT_TOKEN = os.getenv('BOT_TOKEN', '')
        cls.TELEGRAM_API = int(os.getenv('TELEGRAM_API', '0'))
        cls.TELEGRAM_HASH = os.getenv('TELEGRAM_HASH', '')
        cls.USER_SESSION_STRING = os.getenv('USER_SESSION_STRING', '')
        cls.OWNER_ID = int(os.getenv('OWNER_ID', '0'))
        
        # Optional settings
        cls.DATABASE_URL = os.getenv('DATABASE_URL', '')
        cls.AUTHORIZED_CHATS = os.getenv('AUTHORIZED_CHATS', '')
        cls.INDEX_CHANNEL_ID = int(os.getenv('INDEX_CHANNEL_ID', '0'))
        
        # Bot settings
        cls.TIMEZONE = os.getenv('TIMEZONE', 'Asia/Kolkata')
        cls.MEDIAINFO_ENABLED = os.getenv('MEDIAINFO_ENABLED', 'True').lower() == 'true'
        cls.MAX_CONCURRENT_TASKS = int(os.getenv('MAX_CONCURRENT_TASKS', '5'))
        
        # Paths
        cls.DOWNLOAD_DIR = os.getenv('DOWNLOAD_DIR', '/tmp/mediainfo/')
    
    @classmethod
    def _debug_config(cls):
        """Debug method to show loaded configuration"""
        print("\n🔍 Configuration Debug (Environment Variables):")
        debug_vars = ['BOT_TOKEN', 'TELEGRAM_API', 'TELEGRAM_HASH', 'USER_SESSION_STRING', 'OWNER_ID']
        for var in debug_vars:
            value = os.getenv(var, 'NOT_FOUND')
            # Hide sensitive values
            if value != 'NOT_FOUND' and var in ['BOT_TOKEN', 'TELEGRAM_HASH', 'USER_SESSION_STRING']:
                display_value = f"{value[:10]}..." if len(value) > 10 else "***"
            else:
                display_value = value
            print(f"  ENV {var}: {display_value}")
        
        print("\n🔍 Configuration Debug (Class Attributes):")
        for var in debug_vars:
            value = getattr(cls, var, 'NOT_SET')
            # Hide sensitive values
            if value and var in ['BOT_TOKEN', 'TELEGRAM_HASH', 'USER_SESSION_STRING']:
                display_value = f"{str(value)[:10]}..." if len(str(value)) > 10 else "***"
            else:
                display_value = value
            print(f"  ATTR {var}: {display_value}")
        print()
        
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
            if value is None:
                missing.append(key)
            elif not value:  # Empty string or 0
                empty.append(key)
            elif key in ['TELEGRAM_API', 'OWNER_ID'] and value == 0:
                empty.append(key)
            elif isinstance(value, str) and value.strip() == '':
                empty.append(key)
        
        if missing or empty:
            error_msg = "Configuration validation failed:\n"
            if missing:
                error_msg += f"Missing required variables: {', '.join(missing)}\n"
            if empty:
                error_msg += f"Empty required variables: {', '.join(empty)}\n"
            error_msg += "\n💡 Make sure your config.env file has all required values set correctly."
            error_msg += "\n💡 Check that values don't contain quotes or extra spaces."
            raise ValueError(error_msg)
        
        print("✅ All required configuration variables validated successfully!")

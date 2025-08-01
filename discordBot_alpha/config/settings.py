import os
import platform
import psutil
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings:
    """
    Configuration settings for the Discord bot.
    Loads values from environment variables.
    """
    
    # Discord Bot Settings
    DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
    GUILD_ID = os.getenv('GUILD_ID')
    COMMAND_PREFIX = os.getenv('COMMAND_PREFIX', '/')
    
    # Database Settings
    DB_TYPE = os.getenv('DB_TYPE', 'mysql').lower()  # 'mysql' or 'sqlite'
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = int(os.getenv('DB_PORT', 3306))
    DB_USER = os.getenv('DB_USER')
    DB_PASSWORD = os.getenv('DB_PASSWORD')
    DB_NAME = os.getenv('DB_NAME')
    DB_SQLITE_PATH = os.getenv('DB_SQLITE_PATH', 'database/discord_bot.db')
    
    # Role IDs for permission system
    ADMIN_ROLE_ID = int(os.getenv('ADMIN_ROLE_ID', 0))
    MODERATOR_ROLE_ID = int(os.getenv('MODERATOR_ROLE_ID', 0))
    TRUSTED_ROLE_ID = int(os.getenv('TRUSTED_ROLE_ID', 0))
    
    # Bot Owner ID
    BOT_OWNER_ID = int(os.getenv('BOT_OWNER_ID', 0))
    
    # Logging Settings
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_CHANNEL_ID = int(os.getenv('LOG_CHANNEL_ID', 0))
    LOG_TO_FILE = os.getenv('LOG_TO_FILE', 'true').lower() == 'true'
    
    # Point System Settings
    POINT_MESSAGE_COOLDOWN = int(os.getenv('POINT_MESSAGE_COOLDOWN', 60))  # seconds
    POINT_MESSAGE_REWARD = int(os.getenv('POINT_MESSAGE_REWARD', 1))
    POINT_DAILY_BONUS = int(os.getenv('POINT_DAILY_BONUS', 50))
    
    # Raspberry Pi / Performance Settings
    LIGHTWEIGHT_MODE = os.getenv('LIGHTWEIGHT_MODE', 'false').lower() == 'true'
    ENABLED_COGS = os.getenv('ENABLED_COGS', 'permissions,points,message_manager,logging_system,shop,gambling,betting,base').split(',')
    BACKGROUND_TASK_INTERVAL = int(os.getenv('BACKGROUND_TASK_INTERVAL', 60))  # seconds
    DB_POOL_SIZE = int(os.getenv('DB_POOL_SIZE', 5))
    MEMORY_LIMIT_MB = int(os.getenv('MEMORY_LIMIT_MB', 0))  # 0 = no limit
    
    # Auto-detect Raspberry Pi
    IS_RASPBERRY_PI = 'arm' in platform.machine().lower() and os.path.exists('/sys/firmware/devicetree/base/model')
    
    # Auto-configure for Raspberry Pi if detected
    @classmethod
    def auto_configure_for_raspberry_pi(cls):
        """Auto-configure settings for Raspberry Pi if detected"""
        if not cls.IS_RASPBERRY_PI:
            return
            
        # Get Raspberry Pi model
        try:
            with open('/sys/firmware/devicetree/base/model', 'r') as f:
                pi_model = f.read().strip()
        except:
            pi_model = "Unknown Raspberry Pi"
            
        print(f"Detected {pi_model}, applying optimized settings")
        
        # Get available memory
        mem = psutil.virtual_memory()
        total_mem_mb = mem.total / (1024 * 1024)
        
        # Apply optimized settings based on available memory
        if total_mem_mb < 1024:  # Less than 1GB RAM
            if cls.DB_TYPE == 'mysql':
                print("Low memory detected. Consider using SQLite instead of MySQL")
            cls.DB_POOL_SIZE = min(cls.DB_POOL_SIZE, 3)
            cls.LIGHTWEIGHT_MODE = True
            if 'gambling' in cls.ENABLED_COGS:
                cls.ENABLED_COGS.remove('gambling')
            if 'betting' in cls.ENABLED_COGS:
                cls.ENABLED_COGS.remove('betting')
            cls.BACKGROUND_TASK_INTERVAL = max(cls.BACKGROUND_TASK_INTERVAL, 120)
        elif total_mem_mb < 2048:  # Less than 2GB RAM
            cls.DB_POOL_SIZE = min(cls.DB_POOL_SIZE, 4)
            cls.BACKGROUND_TASK_INTERVAL = max(cls.BACKGROUND_TASK_INTERVAL, 90)
    
    @classmethod
    def validate_settings(cls):
        """
        Validate that all required settings are properly set.
        Raises ValueError if any required setting is missing.
        """
        if not cls.DISCORD_TOKEN:
            raise ValueError("DISCORD_TOKEN is not set in environment variables")
            
        # Validate database settings
        if not cls.DB_HOST:
            raise ValueError("DB_HOST is not set in environment variables")
        if not cls.DB_USER:
            raise ValueError("DB_USER is not set in environment variables")
        if not cls.DB_PASSWORD:
            raise ValueError("DB_PASSWORD is not set in environment variables")
        if not cls.DB_NAME:
            raise ValueError("DB_NAME is not set in environment variables")
            
        # Convert string IDs to integers with error handling
        for attr_name in ['ADMIN_ROLE_ID', 'MODERATOR_ROLE_ID', 'LOG_CHANNEL_ID']:
            attr_value = getattr(cls, attr_name)
            if attr_value == 0:
                print(f"Warning: {attr_name} is not set or is invalid")
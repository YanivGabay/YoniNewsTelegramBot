import os
from dotenv import dotenv_values

# Load .env file contents into a dictionary without setting them as environment variables.
# This bypasses the Windows character limit for environment variables.
config = dotenv_values()

def get_config_value(key: str) -> str | None:
    """
    Gets a configuration value by checking os.environ first, 
    then falling back to the parsed .env file from dotenv_values().
    This allows system environment variables to override .env files.
    """
    return os.environ.get(key) or config.get(key)

# Get all required configuration values using the helper
OPENROUTER_API_KEY = get_config_value("OPENROUTER_API_KEY")
YOUR_SITE_URL = get_config_value("YOUR_SITE_URL")
YOUR_SITE_NAME = get_config_value("YOUR_SITE_NAME")
TELEGRAM_BOT_TOKEN = get_config_value("TELEGRAM_BOT_TOKEN")

# Legacy: General chat IDs (for backward compatibility)
TELEGRAM_CHAT_IDS_STR = get_config_value("TELEGRAM_CHAT_IDS") or ""
TELEGRAM_CHAT_IDS = [chat_id.strip() for chat_id in TELEGRAM_CHAT_IDS_STR.split(',') if chat_id.strip()]

# Language-specific chat IDs
TELEGRAM_CHAT_ID_HEBREW = get_config_value("TELEGRAM_CHAT_ID_HEBREW")
TELEGRAM_CHAT_ID_ENGLISH = get_config_value("TELEGRAM_CHAT_ID_ENGLISH")
TELEGRAM_CHAT_ID_SPANISH = get_config_value("TELEGRAM_CHAT_ID_SPANISH")

# Language code to chat ID mapping
LANGUAGE_CHAT_IDS = {}
if TELEGRAM_CHAT_ID_HEBREW:
    LANGUAGE_CHAT_IDS['he'] = TELEGRAM_CHAT_ID_HEBREW
if TELEGRAM_CHAT_ID_ENGLISH:
    LANGUAGE_CHAT_IDS['en'] = TELEGRAM_CHAT_ID_ENGLISH
if TELEGRAM_CHAT_ID_SPANISH:
    LANGUAGE_CHAT_IDS['es'] = TELEGRAM_CHAT_ID_SPANISH

# RSS Feeds
#RSS_FEEDS_STR = get_config_value("RSS_FEEDS") or ""
# The new feed list will be:
# - Ynet (Hebrew)
# - Fox News Politics (English)
# - New York Times Politics (English)
RSS_FEEDS_STR = "http://www.ynet.co.il/Integration/StoryRss2.xml:he,https://moxie.foxnews.com/google-publisher/politics.xml:en,http://rss.nytimes.com/services/xml/rss/nyt/Politics.xml:en"
RSS_FEEDS = []
if RSS_FEEDS_STR:
    try:
        RSS_FEEDS = [
            (pair.rsplit(':', 1)[0].strip(), pair.rsplit(':', 1)[1].strip())
            for pair in RSS_FEEDS_STR.split(',') if ':' in pair
        ]
    except IndexError:
        print("Warning: Could not parse RSS_FEEDS. Ensure it's in the format 'url1:lang1,url2:lang2'")

# Telegram User Credentials for Telethon
TELEGRAM_API_ID = get_config_value("TELEGRAM_API_ID")
TELEGRAM_API_HASH = get_config_value("TELEGRAM_API_HASH")
TELEGRAM_SESSION_DATA = get_config_value("TELEGRAM_SESSION_DATA")

def get_channel_entity(key: str, default: str = "") -> str | int:
    """
    Gets a channel entity from config.
    If it's a numeric string, it's converted to an integer.
    Otherwise, it's returned as a string (for usernames).
    """
    value = get_config_value(key)
    if not value:
        return default
    
    try:
        # Try to convert to integer (for channel IDs like -100...)
        return int(value)
    except (ValueError, TypeError):
        # Return as string (for usernames like @channel_name)
        return value

# Alert Channel Configuration
SOURCE_ALERT_CHANNEL = get_channel_entity("SOURCE_ALERT_CHANNEL", "PikudHaOref_all")

# News Channel Configuration (for real-time summarization)
SOURCE_NEWS_CHANNEL = get_channel_entity("SOURCE_NEWS_CHANNEL")

# Global runtime configuration (set by main.py command line args)
DEV_MODE = False  # When True, show translations in console instead of sending to Telegram
DEBUG_MODE = False  # When True, enable verbose logging

def set_runtime_config(dev_mode=False, debug_mode=False):
    """Set runtime configuration from command line arguments"""
    global DEV_MODE, DEBUG_MODE
    DEV_MODE = dev_mode
    DEBUG_MODE = debug_mode

 
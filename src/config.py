import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
YOUR_SITE_URL = os.getenv("YOUR_SITE_URL")
YOUR_SITE_NAME = os.getenv("YOUR_SITE_NAME")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Legacy: General chat IDs (for backward compatibility)
TELEGRAM_CHAT_IDS_STR = os.getenv("TELEGRAM_CHAT_IDS", "")
TELEGRAM_CHAT_IDS = [chat_id.strip() for chat_id in TELEGRAM_CHAT_IDS_STR.split(',') if chat_id.strip()]

# Language-specific chat IDs
TELEGRAM_CHAT_ID_HEBREW = os.getenv("TELEGRAM_CHAT_ID_HEBREW")
TELEGRAM_CHAT_ID_ENGLISH = os.getenv("TELEGRAM_CHAT_ID_ENGLISH")
TELEGRAM_CHAT_ID_SPANISH = os.getenv("TELEGRAM_CHAT_ID_SPANISH")

# Language code to chat ID mapping
LANGUAGE_CHAT_IDS = {}
if TELEGRAM_CHAT_ID_HEBREW:
    LANGUAGE_CHAT_IDS['he'] = TELEGRAM_CHAT_ID_HEBREW
if TELEGRAM_CHAT_ID_ENGLISH:
    LANGUAGE_CHAT_IDS['en'] = TELEGRAM_CHAT_ID_ENGLISH
if TELEGRAM_CHAT_ID_SPANISH:
    LANGUAGE_CHAT_IDS['es'] = TELEGRAM_CHAT_ID_SPANISH

# RSS Feeds
RSS_FEEDS_STR = os.getenv("RSS_FEEDS", "")
RSS_FEEDS = []
if RSS_FEEDS_STR:
    try:
        # Safely splits "url:lang" by finding the last colon
        # Example: "https://rss.cnn.com/rss/edition.rss:en,http://www.ynet.co.il/Integration/StoryRss2.xml:he"
        RSS_FEEDS = [
            (pair.rsplit(':', 1)[0].strip(), pair.rsplit(':', 1)[1].strip())
            for pair in RSS_FEEDS_STR.split(',') if ':' in pair
        ]
    except IndexError:
        print("Warning: Could not parse RSS_FEEDS. Ensure it's in the format 'url1:lang1,url2:lang2'")

# Telegram User Credentials
TELEGRAM_API_ID = os.getenv("TELEGRAM_API_ID")
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH")

# Alert Channel Configuration
SOURCE_ALERT_CHANNEL = os.getenv("SOURCE_ALERT_CHANNEL", "PikudHaOref_all")

# News Channel Configuration (for real-time summarization)
SOURCE_NEWS_CHANNEL = os.getenv("SOURCE_NEWS_CHANNEL", "")

SOURCE_CHANNELS_STR = os.getenv("SOURCE_TELEGRAM_CHANNELS", "")
SOURCE_TELEGRAM_CHANNELS = []
if SOURCE_CHANNELS_STR:
    # Parses "channel1:lang1,channel2:lang2" into [('channel1', 'lang1'), ('channel2', 'lang2')]
    try:
        SOURCE_TELEGRAM_CHANNELS = [
            (pair.split(':')[0].strip(), pair.split(':')[1].strip())
            for pair in SOURCE_CHANNELS_STR.split(',') if ':' in pair
        ]
    except IndexError:
        print("Warning: Could not parse SOURCE_TELEGRAM_CHANNELS. Ensure it's in the format 'channel1:lang1,channel2:lang2'") 
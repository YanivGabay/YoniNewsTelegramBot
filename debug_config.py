#!/usr/bin/env python3
"""
Debug script to check what configuration values are being loaded
"""
import os
from dotenv import load_dotenv

print("🔍 Debugging YoniNews Configuration")
print("=" * 50)

# Load environment variables
load_dotenv()

# Check TELEGRAM_CHAT_IDS
telegram_chat_ids_str = os.getenv("TELEGRAM_CHAT_IDS", "")
print(f"📱 Raw TELEGRAM_CHAT_IDS from .env: '{telegram_chat_ids_str}'")

if telegram_chat_ids_str:
    # Parse the same way the app does
    chat_ids = [chat_id.strip() for chat_id in telegram_chat_ids_str.split(',') if chat_id.strip()]
    print(f"📋 Parsed Chat IDs: {chat_ids}")
    print(f"📊 Number of Chat IDs: {len(chat_ids)}")
    
    for i, chat_id in enumerate(chat_ids, 1):
        print(f"   {i}. '{chat_id}' (type: {type(chat_id).__name__})")
else:
    print("❌ TELEGRAM_CHAT_IDS is empty or not set!")

# Check other relevant config
print("\n🔧 Other Configuration:")
telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
if telegram_bot_token:
    print(f"🤖 Bot Token: {telegram_bot_token[:10]}...{telegram_bot_token[-5:]} (length: {len(telegram_bot_token)})")
else:
    print("❌ TELEGRAM_BOT_TOKEN not set!")

print(f"📁 Current working directory: {os.getcwd()}")
print(f"🐍 Python version: {os.sys.version}")

# Check if .env file exists
env_file_path = ".env"
if os.path.exists(env_file_path):
    print(f"📄 .env file found at: {os.path.abspath(env_file_path)}")
    # Get file modification time
    import time
    mod_time = os.path.getmtime(env_file_path)
    print(f"📅 .env last modified: {time.ctime(mod_time)}")
else:
    print("❌ .env file not found in current directory")

# Test importing the config module
print("\n🧪 Testing Config Module Import:")
try:
    from src.config import TELEGRAM_CHAT_IDS, TELEGRAM_BOT_TOKEN
    print(f"✅ Config imported successfully")
    print(f"📱 TELEGRAM_CHAT_IDS from config.py: {TELEGRAM_CHAT_IDS}")
    print(f"📊 Number of Chat IDs in config: {len(TELEGRAM_CHAT_IDS)}")
    
    if TELEGRAM_BOT_TOKEN:
        print(f"🤖 Bot Token from config: {TELEGRAM_BOT_TOKEN[:10]}...{TELEGRAM_BOT_TOKEN[-5:]}")
    else:
        print("❌ Bot Token not loaded in config")
        
except Exception as e:
    print(f"❌ Error importing config: {e}")

print("\n" + "=" * 50)
print("💡 Troubleshooting Tips:")
print("1. Make sure you restarted the bot after changing .env")
print("2. Check that the chat ID format is correct (numbers only)")
print("3. Ensure your father sent a message to the bot first")
print("4. Try running the bot manually to see debug output") 
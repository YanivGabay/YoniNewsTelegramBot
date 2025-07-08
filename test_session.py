import asyncio
import os
import base64
from telethon import TelegramClient
from dotenv import dotenv_values

async def test_session():
    """
    Tests the TELEGRAM_SESSION_DATA from the .env file to ensure it's valid.
    """
    # Load environment variables from .env file into a dictionary
    config = dotenv_values()
    
    print("🧪 Testing Telegram Session Data...")
    print("="*40)

    # 1. Get credentials from config dictionary
    api_id = config.get("TELEGRAM_API_ID")
    api_hash = config.get("TELEGRAM_API_HASH")
    session_data = config.get("TELEGRAM_SESSION_DATA")

    # Check if all required variables are present
    if not all([api_id, api_hash, session_data]):
        print("❌ Error: Missing required environment variables.")
        print("   Please ensure TELEGRAM_API_ID, TELEGRAM_API_HASH, and TELEGRAM_SESSION_DATA are in your .env file.")
        return

    # 2. Decode and create a temporary session file
    session_filename = 'test_login.session'
    try:
        print("🔑 Decoding session data from environment variable...")
        session_bytes = base64.b64decode(session_data)
        with open(session_filename, 'wb') as f:
            f.write(session_bytes)
        print("   ✅ Temporary session file created.")
    except Exception as e:
        print(f"❌ Error decoding or writing session file: {e}")
        print("   Your TELEGRAM_SESSION_DATA might be corrupted. Please generate it again.")
        return

    # 3. Attempt to connect and authorize using the session
    client = None
    try:
        print(f"👤 Initializing client with API ID: {api_id}...")
        client = TelegramClient(session_filename, int(api_id), api_hash)

        print("🔌 Attempting to connect to Telegram...")
        await client.connect()

        if await client.is_user_authorized():
            me = await client.get_me()
            username = f"@{me.username}" if me.username else ""
            print("\n" + "="*40)
            print(f"🎉 SUCCESS! Your session data is valid.")
            print(f"✅ Successfully logged in as: {me.first_name} {me.last_name or ''} {username}")
            print("="*40)
        else:
            print("\n" + "="*40)
            print("❌ FAILURE! Session data is invalid or expired.")
            print("   The client connected but could not authorize you with the provided session.")
            print("   Please run the `setup_telethon_session.py` script again to generate a new session string.")
            print("="*40)

    except Exception as e:
        print(f"\n❌ An error occurred during the connection test: {e}")
        print("   This could be due to a network issue or invalid API credentials (ID/Hash).")
    
    finally:
        # 4. Clean up
        if client and client.is_connected():
            await client.disconnect()
            print("🔌 Disconnected.")
        if os.path.exists(session_filename):
            os.remove(session_filename)
            print(f"🗑️ Cleaned up temporary session file.")

if __name__ == "__main__":
    asyncio.run(test_session()) 
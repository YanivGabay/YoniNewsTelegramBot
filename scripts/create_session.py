#!/usr/bin/env python3
"""Create a new Telethon session and output base64 for DO deployment."""
import asyncio
import base64
import os
from telethon import TelegramClient

API_ID = 27728634
API_HASH = "9801669edc41e1df08488eae0a8aaff6"
SESSION_FILE = "yoni_news_session"

async def main():
    print("=" * 60)
    print("Telethon Session Creator for YoniNews Bot")
    print("=" * 60)
    print()
    print("This will log you into Telegram and create a session file.")
    print("You'll receive a verification code on your Telegram app.")
    print()

    client = TelegramClient(SESSION_FILE, API_ID, API_HASH)
    await client.start()

    me = await client.get_me()
    print()
    print(f"✅ Logged in as: {me.first_name} (ID: {me.id})")

    # Verify we can access PikudHaOref
    print()
    print("Checking access to PikudHaOref_all channel...")
    try:
        entity = await client.get_entity("PikudHaOref_all")
        print(f"✅ Found: {entity.title} (ID: {entity.id})")
    except Exception as e:
        print(f"⚠️  Could not access PikudHaOref_all: {e}")
        print("   Make sure you're a member of this channel!")

    await client.disconnect()

    # Read the session file and encode to base64
    session_path = f"{SESSION_FILE}.session"
    if os.path.exists(session_path):
        with open(session_path, "rb") as f:
            session_bytes = f.read()

        session_b64 = base64.b64encode(session_bytes).decode("ascii")

        print()
        print("=" * 60)
        print("SESSION CREATED SUCCESSFULLY!")
        print("=" * 60)
        print()
        print(f"Session file: {session_path}")
        print(f"Session size: {len(session_bytes)} bytes")
        print()
        print("Base64 encoded session (copy this to DO):")
        print("-" * 60)
        print(session_b64)
        print("-" * 60)
        print()
        print(f"Base64 length: {len(session_b64)} characters")
        print()

        # Also save to a file for convenience
        b64_file = "session_b64.txt"
        with open(b64_file, "w") as f:
            f.write(session_b64)
        print(f"Also saved to: {b64_file}")
        print()
        print("Next steps:")
        print("1. Copy the base64 string above")
        print("2. Update TELEGRAM_SESSION_DATA in DigitalOcean App Platform")
        print("3. Redeploy the app")
    else:
        print(f"❌ Session file not found: {session_path}")

if __name__ == "__main__":
    asyncio.run(main())

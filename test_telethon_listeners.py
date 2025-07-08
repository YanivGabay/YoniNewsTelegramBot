#!/usr/bin/env python3
"""
Test script to check if Telethon listeners are working and can connect to channels.
No message processing, just connection and channel access testing.
"""

import asyncio
from telethon import TelegramClient
from src.config import TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_SESSION_DATA, SOURCE_ALERT_CHANNEL, SOURCE_NEWS_CHANNEL
import base64
import os

def clean_channel_id(channel_id):
    """Clean channel ID by removing comments and extra quotes"""
    if isinstance(channel_id, str):
        # Remove comments (anything after #)
        if '#' in channel_id:
            channel_id = channel_id.split('#')[0].strip()
        # Remove extra quotes
        channel_id = channel_id.strip('"\'')
        # Try to convert to int if it's a numeric ID
        if channel_id.startswith('-') and channel_id[1:].isdigit():
            return int(channel_id)
    return channel_id

async def test_telethon_setup():
    print("🧪 Telethon Connection Test")
    print("=" * 60)
    
    # Check if credentials are configured
    if not TELEGRAM_API_ID or not TELEGRAM_API_HASH:
        print("❌ Telethon credentials not configured!")
        print("   Missing TELEGRAM_API_ID or TELEGRAM_API_HASH")
        print("   Check your .env file")
        return
    
    print("✅ Telethon credentials found")
    print(f"   API ID: {TELEGRAM_API_ID}")
    print(f"   API Hash: {TELEGRAM_API_HASH[:8]}...")
    
    # Check session data
    if not TELEGRAM_SESSION_DATA:
        print("❌ No session data found!")
        print("   Missing TELEGRAM_SESSION_DATA")
        print("   You need to run the session setup script first")
        return
    
    print("✅ Session data found")
    
    # Clean and show configured channels
    clean_alert_channel = clean_channel_id(SOURCE_ALERT_CHANNEL)
    clean_news_channel = clean_channel_id(SOURCE_NEWS_CHANNEL) if SOURCE_NEWS_CHANNEL else None
    
    print(f"\n📡 Configured channels:")
    print(f"   Alert Channel: {SOURCE_ALERT_CHANNEL} → {clean_alert_channel}")
    print(f"   News Channel: {SOURCE_NEWS_CHANNEL if SOURCE_NEWS_CHANNEL else 'Not configured'} → {clean_news_channel if clean_news_channel else 'Not configured'}")
    
    print("\n" + "-" * 60)
    print("🔌 Testing Telethon connection...")
    
    client = None
    try:
        # Restore session file
        print("🔑 Restoring session from environment variable...")
        session_bytes = base64.b64decode(TELEGRAM_SESSION_DATA)
        session_file = 'test_session.session'
        with open(session_file, 'wb') as f:
            f.write(session_bytes)
        print("✅ Session file restored")
        
        # Create client
        client = TelegramClient(session_file, TELEGRAM_API_ID, TELEGRAM_API_HASH)
        
        # Connect
        print("🔗 Connecting to Telegram...")
        await client.connect()
        
        if not await client.is_user_authorized():
            print("❌ Client not authorized!")
            print("   Your session may have expired")
            print("   Re-run the session setup script")
            return
        
        print("✅ Successfully connected and authorized!")
        
        # Get user info
        me = await client.get_me()
        print(f"   Logged in as: {me.first_name} {me.last_name or ''} (@{me.username or 'no username'})")
        
        # Clear entity cache to force fresh lookups
        print("🧹 Clearing entity cache to fetch fresh channel data...")
        if hasattr(client.session, 'entities'):
            client.session.entities.clear()
        
        # Test channels
        print(f"\n📺 Testing channel access...")
        
        channels_to_test = []
        if clean_alert_channel:
            channels_to_test.append(("Alert", clean_alert_channel))
        if clean_news_channel:
            channels_to_test.append(("News", clean_news_channel))
        
        if not channels_to_test:
            print("⚠️  No channels configured to test")
        
        for channel_type, channel_id in channels_to_test:
            try:
                print(f"\n   🔍 Testing {channel_type} channel: {channel_id}")
                
                # Try to get the entity with force_refresh
                print(f"      Fetching channel info...")
                entity = await client.get_entity(channel_id)
                print(f"   ✅ Successfully found channel: {entity.title}")
                print(f"      Type: {'Channel' if hasattr(entity, 'broadcast') and entity.broadcast else 'Group'}")
                print(f"      ID: {entity.id}")
                print(f"      Members: {getattr(entity, 'participants_count', 'Unknown')}")
                
                # Try to get recent messages (just to test access)
                print(f"      Testing message access...")
                messages = await client.get_messages(entity, limit=1)
                if messages:
                    latest_msg = messages[0]
                    print(f"      ✅ Can read messages! Latest: {latest_msg.date}")
                    if latest_msg.text:
                        preview = latest_msg.text[:50] + "..." if len(latest_msg.text) > 50 else latest_msg.text
                        print(f"      Preview: {preview}")
                else:
                    print(f"      ⚠️  No recent messages found (but access works)")
                
            except Exception as e:
                print(f"   ❌ Error accessing {channel_type} channel: {e}")
                print(f"      Channel ID: {channel_id}")
                print(f"      This could mean:")
                print(f"      - You're not a member of this channel")
                print(f"      - Channel ID is incorrect") 
                print(f"      - Channel is private and restricts access")
                print(f"      - Session was created before joining this channel")
                print(f"      💡 Try regenerating your session if you recently joined")
        
        print(f"\n🎯 Telethon test complete!")
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        
    finally:
        if client and client.is_connected():
            print("🔌 Disconnecting...")
            await client.disconnect()
        
        # Clean up test session file
        if os.path.exists('test_session.session'):
            os.remove('test_session.session')
            print("🧹 Cleaned up test session file")
    
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_telethon_setup()) 
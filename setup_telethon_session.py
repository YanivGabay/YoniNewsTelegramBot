#!/usr/bin/env python3
"""
Telethon Session Setup Script
Run this script LOCALLY on your computer to create the session file.
"""

import asyncio
import base64
import os
from telethon import TelegramClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def setup_session():
    """Set up Telethon session and generate base64 data for production"""
   
   
    
    # Get credentials from environment
    api_id = os.getenv("TELEGRAM_API_ID")
    api_hash = os.getenv("TELEGRAM_API_HASH")
    
    # Debug info (remove after testing)
    print(f"🔍 Debug - API_ID: {api_id}")
    print(f"🔍 Debug - API_HASH: {api_hash[:8]}..." if api_hash else "None")
    
    if not api_id or not api_hash:
        print("❌ Error: TELEGRAM_API_ID and TELEGRAM_API_HASH not found in .env file")
        print("💡 Let's enter them manually:")
        
        api_id = input("Enter your TELEGRAM_API_ID: ").strip()
        api_hash = input("Enter your TELEGRAM_API_HASH: ").strip()
        
        if not api_id or not api_hash:
            print("❌ Both values are required")
            return
    
    # Convert API_ID to integer
    try:
        api_id = int(api_id)
    except ValueError:
        print("❌ Error: TELEGRAM_API_ID must be a number")
        return
    
    print("🔑 Setting up Telethon session...")
    print("📱 You will need to enter your phone number and verification code")
    print("💡 For Israeli numbers, use format: +972527827822")
    print("=" * 50)
    
    # Create client
    client = TelegramClient('alert_session', api_id, api_hash)
    
    try:
        # First, just connect to test credentials
        print("🔌 Testing connection...")
        await client.connect()
        
        if not await client.is_user_authorized():
            print("✅ Credentials are valid, proceeding with authentication...")
            await client.disconnect()
            
            # Now start the full authentication process
            print("📞 Choose your authentication method:")
            print("   1. Phone number: +972527827822")
            print("   2. Bot token: bot1234567890:ABCdefGHIjklMNOpqrsTUVwxyz")
            print("   💡 Bot tokens are easier but can't read from channels where they're not admin")
            await client.start()
        else:
            print("✅ Already authorized!")
        
        print("✅ Session created successfully!")
        
        # Check if session file exists
        if os.path.exists('alert_session.session'):
            # Convert session to base64
            with open('alert_session.session', 'rb') as f:
                session_bytes = f.read()
                session_b64 = base64.b64encode(session_bytes).decode()
            
            print("\n" + "=" * 50)
            print("🎉 SUCCESS! Copy this to your environment variables:")
            print("=" * 50)
            print(f"TELEGRAM_SESSION_DATA={session_b64}")
            print("=" * 50)
            print("\n📋 Instructions:")
            print("1. Copy the TELEGRAM_SESSION_DATA line above")
            print("2. Add it to your .env file (locally) or environment variables (production)")
            print("3. Deploy your app - it will use this session automatically")
            print("4. You can delete the alert_session.session file from this directory")
            
        else:
            print("❌ Session file not found")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        
    finally:
        await client.disconnect()

if __name__ == "__main__":
    print("🚀 Telethon Session Setup for YoniNews Bot")
    print("=" * 50)
    asyncio.run(setup_session()) 
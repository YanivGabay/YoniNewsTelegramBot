#!/usr/bin/env python3
"""
Setup guide for language-specific Telegram groups
"""
import os
from dotenv import load_dotenv

# Load current configuration
load_dotenv()

print("🏗️  Setting up Language-Specific Groups")
print("=" * 50)

print("🎯 GOAL: Send each language to its own Telegram group/chat")
print("   • Hebrew messages → Hebrew group")
print("   • English messages → English group") 
print("   • Spanish messages → Spanish group")
print()

# Check current configuration
from src.config import LANGUAGE_CHAT_IDS, TELEGRAM_BOT_TOKEN

print("📋 Current Configuration:")
print("-" * 30)

if TELEGRAM_BOT_TOKEN:
    print(f"✅ Bot Token: {TELEGRAM_BOT_TOKEN[:10]}...{TELEGRAM_BOT_TOKEN[-5:]}")
else:
    print("❌ Bot Token: Not set")

print(f"📱 Language Groups configured: {len(LANGUAGE_CHAT_IDS)}/3")

for lang_code, lang_name in [('he', 'Hebrew'), ('en', 'English'), ('es', 'Spanish')]:
    if lang_code in LANGUAGE_CHAT_IDS:
        print(f"   ✅ {lang_name}: {LANGUAGE_CHAT_IDS[lang_code]}")
    else:
        print(f"   ❌ {lang_name}: Not configured")

print()
print("🛠️  SETUP STEPS:")
print("=" * 50)

# Step 1: Create groups
print("1️⃣  CREATE TELEGRAM GROUPS")
print("   • Create 3 separate Telegram groups:")
print("     - Hebrew News Group")
print("     - English News Group") 
print("     - Spanish News Group")
print()

# Step 2: Add bot
print("2️⃣  ADD YOUR BOT TO EACH GROUP")
print("   • Add your bot to all 3 groups")
print("   • Make sure the bot has permission to send messages")
print()

# Step 3: Get chat IDs
print("3️⃣  GET CHAT IDs FOR EACH GROUP")
print("   • Send a message in each group")
print("   • Use this URL to get updates:")
print(f"     https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates")
print("   • Look for 'chat':{'id': -XXXXXXXXX} in the response")
print("   • Group chat IDs are usually negative numbers")
print()

# Step 4: Update .env
print("4️⃣  ADD TO YOUR .ENV FILE")
print("   Add these lines to your .env file:")
print("   " + "-" * 40)

missing_vars = []
for lang_code, lang_name in [('he', 'Hebrew'), ('en', 'English'), ('es', 'Spanish')]:
    env_var = f"TELEGRAM_CHAT_ID_{lang_name.upper()}"
    if lang_code not in LANGUAGE_CHAT_IDS:
        print(f"   {env_var}=your_{lang_name.lower()}_group_chat_id")
        missing_vars.append(env_var)

if not missing_vars:
    print("   ✅ All language groups are already configured!")
else:
    print("   " + "-" * 40)
    print()

# Step 5: Test
print("5️⃣  TEST THE SETUP")
print("   • Restart your bot after updating .env")
print("   • Run: python test_language_groups.py")
print()

if missing_vars:
    print("⚠️  MISSING CONFIGURATION:")
    print(f"   You need to add {len(missing_vars)} environment variables:")
    for var in missing_vars:
        print(f"   • {var}")
else:
    print("🎉 All language groups are configured!")
    print("   You're ready to use language-specific messaging!")

print()
print("💡 EXAMPLE .env lines:")
print("   TELEGRAM_CHAT_ID_HEBREW=-1001234567890")
print("   TELEGRAM_CHAT_ID_ENGLISH=-1001234567891") 
print("   TELEGRAM_CHAT_ID_SPANISH=-1001234567892") 
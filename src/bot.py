import telegram
from src.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_IDS, LANGUAGE_CHAT_IDS, SOURCE_ALERT_CHANNEL, SOURCE_NEWS_CHANNEL, TELEGRAM_API_ID, TELEGRAM_API_HASH
import asyncio
from telethon import TelegramClient, events
from src.llm_handler import translate_alert_to_all_languages, get_language_emoji, summarize_and_translate_news
import telegram.helpers

# Create Telethon client for real-time listening
telethon_client = None
if TELEGRAM_API_ID and TELEGRAM_API_HASH:
    telethon_client = TelegramClient('alert_session', TELEGRAM_API_ID, TELEGRAM_API_HASH)

async def send_message(text, parse_mode=None):
    """
    Sends a message to the configured Telegram chats.
    Returns True if successful, False if failed.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_IDS:
        print("❌ Error: Telegram Bot Token or Chat IDs are not configured.")
        return False

    try:
        bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
        for chat_id in TELEGRAM_CHAT_IDS:
            await bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode)
            print(f"Message sent to chat ID: {chat_id}")
        return True
    except Exception as e:
        print(f"❌ Failed to send message: {e}")
        return False

async def send_message_to_language_group(text, language_code, parse_mode=None):
    """
    Sends a message to a specific language group.
    
    Args:
        text (str): Message to send
        language_code (str): Language code ('he', 'en', 'es')
        parse_mode (str): Telegram parse mode (optional)
    
    Returns:
        bool: True if successful, False if failed
    """
    if not TELEGRAM_BOT_TOKEN:
        print("❌ Error: Telegram Bot Token is not configured.")
        return False
    
    # Get chat ID for this language
    chat_id = LANGUAGE_CHAT_IDS.get(language_code)
    if not chat_id:
        print(f"❌ Error: No chat ID configured for language '{language_code}'")
        print(f"💡 Add TELEGRAM_CHAT_ID_{language_code.upper()} to your .env file")
        return False
    
    try:
        bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
        await bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode)
        print(f"📤 Message sent to {language_code.upper()} group (chat ID: {chat_id})")
        return True
    except Exception as e:
        print(f"❌ Failed to send {language_code.upper()} message: {e}")
        return False

async def send_message_to_all_languages(messages_by_language, parse_mode=None):
    """
    Sends language-specific messages to their respective groups.
    
    Args:
        messages_by_language (dict): {'he': text, 'en': text, 'es': text}
        parse_mode (str): Telegram parse mode (optional)
    
    Returns:
        dict: Results for each language {'he': True/False, 'en': True/False, 'es': True/False}
    """
    results = {}
    
    for lang_code, message_text in messages_by_language.items():
        if message_text:  # Only send if there's content
            success = await send_message_to_language_group(message_text, lang_code, parse_mode)
            results[lang_code] = success
            
            # Small delay between messages to avoid rate limits
            await asyncio.sleep(1)
        else:
            print(f"⚠️  No content for {lang_code.upper()}, skipping")
            results[lang_code] = False
    
    return results

async def handle_emergency_alert(event):
    """
    Handles real-time emergency alerts from PikudHaOref_all channel.
    Immediately translates and sends to all language groups.
    """
    alert_text = event.message.text
    if not alert_text:
        return
    
    print(f"\n🚨 EMERGENCY ALERT DETECTED")
    print(f"📍 Source: @{SOURCE_ALERT_CHANNEL}")
    print(f"📝 Text: {alert_text[:100]}...")
    
    try:
        # Translate to all languages immediately
        print("🔄 Translating alert to all languages...")
        translations = await translate_alert_to_all_languages(alert_text)
        
        if not translations:
            print("❌ Alert translation failed")
            return
        
        # Send to each language group immediately
        for lang_code, translated_text in translations.items():
            if lang_code not in LANGUAGE_CHAT_IDS:
                print(f"⚠️  No chat ID configured for {lang_code.upper()}, skipping")
                continue
            
            emoji = get_language_emoji(lang_code)
            
            # Format as emergency alert
            formatted_message = f"🚨 {emoji} **EMERGENCY ALERT**\n\n{telegram.helpers.escape_markdown(translated_text, version=2)}"
            
            success = await send_message_to_language_group(
                formatted_message, 
                lang_code, 
                parse_mode='MarkdownV2'
            )
            
            if success:
                print(f"✅ Alert sent to {lang_code.upper()} group")
            else:
                print(f"❌ Failed to send alert to {lang_code.upper()} group")
        
        print("🚨 Emergency alert processing complete")
        
    except Exception as e:
        print(f"❌ Error processing emergency alert: {e}")

async def handle_news_channel_message(event, source_lang_code='es'):
    """
    Handles real-time news messages from the configured news channel.
    Summarizes and translates to all language groups.
    
    Args:
        event: Telethon event object
        source_lang_code (str): Language code of the source channel ('es', 'he', 'en')
    """
    news_text = event.message.text
    if not news_text:
        return
    
    print(f"\n📰 NEWS MESSAGE DETECTED")
    print(f"📍 Source: @{SOURCE_NEWS_CHANNEL} ({source_lang_code.upper()})")
    print(f"📝 Text: {news_text[:100]}...")
    
    try:
        # Summarize and translate to all languages
        print("📝 Processing news content...")
        translations = await summarize_and_translate_news(news_text, source_lang_code)
        
        if not translations:
            print("❌ News processing failed")
            return
        
        # Send to each language group
        for lang_code, translated_text in translations.items():
            if lang_code not in LANGUAGE_CHAT_IDS:
                print(f"⚠️  No chat ID configured for {lang_code.upper()}, skipping")
                continue
            
            emoji = get_language_emoji(lang_code)
            
            # Format as news update
            formatted_message = f"📰 {emoji} **NEWS UPDATE**\n\n{telegram.helpers.escape_markdown(translated_text, version=2)}\n\n\\-\\-\\-"
            
            success = await send_message_to_language_group(
                formatted_message, 
                lang_code, 
                parse_mode='MarkdownV2'
            )
            
            if success:
                print(f"✅ News sent to {lang_code.upper()} group")
            else:
                print(f"❌ Failed to send news to {lang_code.upper()} group")
        
        print("📰 News processing complete")
        
    except Exception as e:
        print(f"❌ Error processing news message: {e}")

async def start_alert_listener():
    """
    Starts the real-time alert listener for emergency notifications.
    """
    if not telethon_client:
        print("⚠️  Telethon client not configured. Real-time alerts disabled.")
        print("💡 Add TELEGRAM_API_ID and TELEGRAM_API_HASH to enable real-time alerts")
        return
    
    try:
        await telethon_client.connect()
        
        if not await telethon_client.is_user_authorized():
            print("❌ Telethon client not authorized for real-time alerts")
            print("💡 Run the bot interactively once to authorize Telethon")
            await telethon_client.disconnect()
            return
        
        # Set up event handler for the alert channel
        @telethon_client.on(events.NewMessage(chats=SOURCE_ALERT_CHANNEL))
        async def alert_handler(event):
            await handle_emergency_alert(event)
        
        # Set up event handler for the news channel (if configured)
        if SOURCE_NEWS_CHANNEL:
            @telethon_client.on(events.NewMessage(chats=SOURCE_NEWS_CHANNEL))
            async def news_handler(event):
                # Default to Spanish since that's your current channel
                await handle_news_channel_message(event, source_lang_code='es')
            
            print(f"📰 Real-time news listener started for @{SOURCE_NEWS_CHANNEL} (Spanish)")
        else:
            print("⚠️  No news channel configured. Add SOURCE_NEWS_CHANNEL to .env to enable")
        
        print(f"🚨 Real-time alert listener started for @{SOURCE_ALERT_CHANNEL}")
        print("🔴 Listening for emergency alerts and news updates...")
        
        # Keep the client running
        await telethon_client.run_until_disconnected()
        
    except Exception as e:
        print(f"❌ Error starting alert listener: {e}")
        if telethon_client.is_connected():
            await telethon_client.disconnect()

async def main():
    """Test the bot functionality"""

if __name__ == '__main__':
    asyncio.run(main()) 
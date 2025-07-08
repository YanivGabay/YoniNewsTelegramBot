import telegram
from src.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_IDS, LANGUAGE_CHAT_IDS, SOURCE_ALERT_CHANNEL, SOURCE_NEWS_CHANNEL, TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_SESSION_DATA
import asyncio
from telethon import TelegramClient, events
from src.llm_handler import translate_alert_to_all_languages, get_language_emoji, summarize_and_translate_news
import telegram.helpers
import json
from datetime import datetime
import base64
import os

# Memory for webhook deduplication (message_id -> timestamp)
processed_webhook_messages = {}

# Create Telethon client with session management
telethon_client = None

def setup_telethon_client():
    """Set up Telethon client with session from environment variable"""
    global telethon_client
    
    if not TELEGRAM_API_ID or not TELEGRAM_API_HASH:
        print("⚠️  TELEGRAM_API_ID or TELEGRAM_API_HASH not configured")
        return False
    
    try:
        # Create session file from environment variable if it exists
        if TELEGRAM_SESSION_DATA:
            print("🔑 Restoring Telethon session from environment variable...")
            session_bytes = base64.b64decode(TELEGRAM_SESSION_DATA)
            with open('alert_session.session', 'wb') as f:
                f.write(session_bytes)
            print("✅ Session file restored successfully")
        
        # Create Telethon client
        telethon_client = TelegramClient('alert_session', TELEGRAM_API_ID, TELEGRAM_API_HASH)
        
        # Clear entity cache to ensure fresh channel lookups
        # This fixes issues when session was created before joining channels
        print("🧹 Clearing Telethon entity cache for fresh channel lookups...")
        if hasattr(telethon_client.session, 'entities'):
            telethon_client.session.entities.clear()
        
        return True
        
    except Exception as e:
        print(f"❌ Error setting up Telethon client: {e}")
        return False

def cleanup_webhook_memory():
    """Remove old webhook messages from memory to prevent memory leaks"""
    global processed_webhook_messages
    import time
    cutoff_time = time.time() - (24 * 60 * 60)  # 24 hours ago
    
    old_count = len(processed_webhook_messages)
    processed_webhook_messages = {
        msg_id: timestamp 
        for msg_id, timestamp in processed_webhook_messages.items()
        if timestamp > cutoff_time
    }
    
    cleaned_count = old_count - len(processed_webhook_messages)
    if cleaned_count > 0:
        print(f"🧹 Cleaned {cleaned_count} old webhook messages from memory")

def is_webhook_message_processed(message_id):
    """Check if we've already processed this webhook message"""
    return message_id in processed_webhook_messages

def mark_webhook_message_processed(message_id):
    """Mark webhook message as processed"""
    import time
    processed_webhook_messages[message_id] = time.time()

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

async def handle_webhook_alert(alert_text, message_id=None, source="Webhook"):
    """
    Handles emergency alerts received via webhook.
    This is the production-ready version that doesn't require Telethon.
    """
    if not alert_text:
        return {"success": False, "error": "No alert text provided"}
    
    # Prevent duplicate processing
    if message_id and is_webhook_message_processed(message_id):
        print(f"⚠️  [{source}] Alert {message_id} already processed, skipping")
        return {"success": True, "message": "Already processed"}
    
    print(f"\n🚨 [{source}] EMERGENCY ALERT")
    print(f"📍 Source: {source}")
    print(f"📝 Text: {alert_text[:100]}...")
    
    try:
        # Translate to all languages immediately
        print("🔄 Translating alert to all languages...")
        translations = await translate_alert_to_all_languages(alert_text)
        
        if not translations:
            print("❌ Alert translation failed")
            return {"success": False, "error": "Translation failed"}
        
        results = {}
        # Send to each language group immediately
        for lang_code, translated_text in translations.items():
            if lang_code not in LANGUAGE_CHAT_IDS:
                print(f"⚠️  No chat ID configured for {lang_code.upper()}, skipping")
                results[lang_code] = False
                continue
            
            emoji = get_language_emoji(lang_code)
            
            # Format as emergency alert
            formatted_message = f"🚨 {emoji} **EMERGENCY ALERT**\n\n{telegram.helpers.escape_markdown(translated_text, version=2)}"
            
            success = await send_message_to_language_group(
                formatted_message, 
                lang_code, 
                parse_mode='MarkdownV2'
            )
            
            results[lang_code] = success
            if success:
                print(f"✅ Alert sent to {lang_code.upper()} group")
            else:
                print(f"❌ Failed to send alert to {lang_code.upper()} group")
        
        # Mark as processed
        if message_id:
            mark_webhook_message_processed(message_id)
        
        print(f"🚨 [{source}] Emergency alert processing complete")
        return {"success": True, "results": results}
        
    except Exception as e:
        print(f"❌ Error processing [{source}] emergency alert: {e}")
        return {"success": False, "error": str(e)}

async def handle_webhook_news(news_text, source_lang_code='es', message_id=None, source="Webhook"):
    """
    Handles news messages received via webhook.
    This is the production-ready version that doesn't require Telethon.
    """
    if not news_text:
        return {"success": False, "error": "No news text provided"}
    
    # Prevent duplicate processing
    if message_id and is_webhook_message_processed(message_id):
        print(f"⚠️  [{source}] News {message_id} already processed, skipping")
        return {"success": True, "message": "Already processed"}
    
    print(f"\n📰 [{source}] NEWS MESSAGE")
    print(f"📍 Source: {source} ({source_lang_code.upper()})")
    print(f"📝 Text: {news_text[:100]}...")
    
    try:
        # Summarize and translate to all languages
        print("📝 Processing news content...")
        translations = await summarize_and_translate_news(news_text, source_lang_code)
        
        if not translations:
            print("❌ News processing failed")
            return {"success": False, "error": "Processing failed"}
        
        results = {}
        # Send to each language group
        for lang_code, translated_text in translations.items():
            if lang_code not in LANGUAGE_CHAT_IDS:
                print(f"⚠️  No chat ID configured for {lang_code.upper()}, skipping")
                results[lang_code] = False
                continue
            
            emoji = get_language_emoji(lang_code)
            
            # Format as news update
            formatted_message = f"📰 {emoji} **NEWS UPDATE**\n\n{telegram.helpers.escape_markdown(translated_text, version=2)}\n\n\\-\\-\\-"
            
            success = await send_message_to_language_group(
                formatted_message, 
                lang_code, 
                parse_mode='MarkdownV2'
            )
            
            results[lang_code] = success
            if success:
                print(f"✅ News sent to {lang_code.upper()} group")
            else:
                print(f"❌ Failed to send news to {lang_code.upper()} group")
        
        # Mark as processed
        if message_id:
            mark_webhook_message_processed(message_id)
        
        print(f"📰 [{source}] News processing complete")
        return {"success": True, "results": results}
        
    except Exception as e:
        print(f"❌ Error processing [{source}] news message: {e}")
        return {"success": False, "error": str(e)}

async def handle_emergency_alert(event):
    """
    Handles real-time emergency alerts from PikudHaOref_all channel.
    """
    alert_text = event.message.text
    if not alert_text:
        return
    
    source_tag = f"Telethon @{SOURCE_ALERT_CHANNEL}"
    await handle_webhook_alert(alert_text, message_id=f"telethon_{event.message.id}", source=source_tag)

async def handle_news_channel_message(event, source_lang_code='es'):
    """
    Handles real-time news messages from the configured news channel.
    """
    news_text = event.message.text
    if not news_text:
        return
    
    source_tag = f"Telethon @{SOURCE_NEWS_CHANNEL}"
    await handle_webhook_news(news_text, source_lang_code, message_id=f"telethon_{event.message.id}", source=source_tag)

async def start_alert_listener():
    """
    Starts the real-time alert listener for emergency notifications using Telethon.
    """
    if not setup_telethon_client():
        print("❌ Failed to set up Telethon client")
        return
    
    if not telethon_client:
        print("❌ Telethon client not available")
        return
    
    try:
        print("🔌 Connecting to Telegram...")
        await telethon_client.connect()
        
        if not await telethon_client.is_user_authorized():
            print("❌ Telethon client not authorized")
            print("💡 You need to run the session setup script first")
            await telethon_client.disconnect()
            return
        
        print("✅ Telethon client authorized successfully")
        
        # Set up event handler for the alert channel
        try:
            @telethon_client.on(events.NewMessage(chats=SOURCE_ALERT_CHANNEL))
            async def alert_handler(event):
                await handle_emergency_alert(event)
            
            print(f"🚨 Real-time alert listener started for @{SOURCE_ALERT_CHANNEL}")
        except Exception as e:
            print(f"⚠️  Warning: Could not set up alert listener for @{SOURCE_ALERT_CHANNEL}: {e}")
            print("💡 The bot will continue running but won't receive real-time alerts from this channel")
        
        # Set up event handler for the news channel (if configured)
        if SOURCE_NEWS_CHANNEL:
            try:
                @telethon_client.on(events.NewMessage(chats=SOURCE_NEWS_CHANNEL))
                async def news_handler(event):
                    # Default to Spanish since that's your current channel
                    await handle_news_channel_message(event, source_lang_code='es')
                
                print(f"📰 Real-time news listener started for @{SOURCE_NEWS_CHANNEL} (Spanish)")
            except Exception as e:
                print(f"⚠️  Warning: Could not set up news listener for @{SOURCE_NEWS_CHANNEL}: {e}")
                print("💡 The bot will continue running but won't receive real-time news from this channel")
        else:
            print("⚠️  No news channel configured. Add SOURCE_NEWS_CHANNEL to .env to enable")
        
        print("🔴 Listening for emergency alerts and news updates...")
        
        # Keep the client running
        await telethon_client.run_until_disconnected()
        
    except Exception as e:
        print(f"❌ Error starting alert listener: {e}")
        if telethon_client and telethon_client.is_connected():
            await telethon_client.disconnect()



async def start_webhook_server():
    """
    Starts a simple webhook server for receiving alerts and news.
    This is the production-ready approach for Digital Ocean App Platform.
    """
    from aiohttp import web, ClientSession
    import os
    
    async def webhook_alert_handler(request):
        """Handle incoming alert webhooks"""
        try:
            # Clean old messages from memory
            cleanup_webhook_memory()
            
            data = await request.json()
            alert_text = data.get('text', '')
            message_id = data.get('message_id')
            
            if not alert_text:
                return web.json_response({"error": "No alert text provided"}, status=400)
            
            result = await handle_webhook_alert(alert_text, message_id, source="Webhook")
            return web.json_response(result)
            
        except Exception as e:
            print(f"❌ Webhook alert error: {e}")
            return web.json_response({"error": str(e)}, status=500)
    
    async def webhook_news_handler(request):
        """Handle incoming news webhooks"""
        try:
            # Clean old messages from memory
            cleanup_webhook_memory()
            
            data = await request.json()
            news_text = data.get('text', '')
            source_lang = data.get('source_lang', 'es')
            message_id = data.get('message_id')
            
            if not news_text:
                return web.json_response({"error": "No news text provided"}, status=400)
            
            result = await handle_webhook_news(news_text, source_lang, message_id, source="Webhook")
            return web.json_response(result)
            
        except Exception as e:
            print(f"❌ Webhook news error: {e}")
            return web.json_response({"error": str(e)}, status=500)
    
    async def health_check(request):
        """Health check endpoint"""
        return web.json_response({"status": "healthy", "timestamp": datetime.now().isoformat()})
    
    # Create web application
    app = web.Application()
    app.router.add_post('/webhook/alert', webhook_alert_handler)
    app.router.add_post('/webhook/news', webhook_news_handler)
    app.router.add_get('/health', health_check)
    app.router.add_get('/', health_check)  # Root endpoint
    
    # Get port from environment (Digital Ocean App Platform uses PORT)
    port = int(os.environ.get('PORT', 8080))
    
    print(f"🌐 Starting webhook server on port {port}")
    print(f"📡 Alert webhook: POST /webhook/alert")
    print(f"📰 News webhook: POST /webhook/news")
    print(f"❤️  Health check: GET /health")
    
    # Start the server
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    print(f"✅ Webhook server started on http://0.0.0.0:{port}")
    return runner

async def main():
    """Test the bot functionality"""

if __name__ == '__main__':
    asyncio.run(main()) 
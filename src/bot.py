import telegram
from src.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_IDS, LANGUAGE_CHAT_IDS, SOURCE_ALERT_CHANNEL, SOURCE_NEWS_CHANNEL, TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_SESSION_DATA
import asyncio
from telethon import TelegramClient, events
from src.llm_handler import translate_alert_to_all_languages, get_language_emoji
from src.telethon_llm_handler import summarize_and_translate_news_telethon
import telegram.helpers
import json
from datetime import datetime
import base64
import os
import hashlib
import time

# Telethon/Webhook memory (completely separate from RSS)
processed_webhook_messages = {}  # webhook message_id -> timestamp
sent_messages = {}  # chat_id:text hash -> timestamp

def is_duplicate_message(text, chat_id):
    key = hashlib.md5(f"{chat_id}:{text}".encode()).hexdigest()
    cutoff = time.time() - 1800  # 30 minutes
    
    # Clean old entries
    global sent_messages
    sent_messages = {k: v for k, v in sent_messages.items() if v > cutoff}
    
    return key in sent_messages

def mark_message_sent(text, chat_id):
    key = hashlib.md5(f"{chat_id}:{text}".encode()).hexdigest()
    sent_messages[key] = time.time()

# Create Telethon client with session management
telethon_client = None

def setup_telethon_client():
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

def cleanup_telethon_memory():
    cutoff_time = time.time() - (24 * 60 * 60)  # 24 hours ago
    
    global processed_webhook_messages
    old_count = len(processed_webhook_messages)
    processed_webhook_messages = {
        msg_id: timestamp 
        for msg_id, timestamp in processed_webhook_messages.items()
        if timestamp > cutoff_time
    }
    
    cleaned_count = old_count - len(processed_webhook_messages)
    if cleaned_count > 0:
        print(f"🧹 [Telethon] Cleaned {cleaned_count} old messages from memory")

def is_telethon_message_processed(message_id):
    if not message_id:
        return False
    return message_id in processed_webhook_messages

def mark_telethon_message_processed(message_id):
    if message_id:
        processed_webhook_messages[message_id] = time.time()

async def send_message(text, parse_mode=None):
    # In dev mode, print to console instead of sending to Telegram
    from src.config import DEV_MODE  # Import dynamically to get current value
    if DEV_MODE:
        print(f"\n{'='*60}")
        print(f"🔧 DEV MODE - GENERAL MESSAGE (would send to Telegram)")
        print(f"{'='*60}")
        print(f"Parse Mode: {parse_mode or 'None'}")
        print(f"Content:")
        print(f"{'-'*40}")
        # Remove markdown formatting for cleaner console output
        clean_text = text
        if parse_mode == 'MarkdownV2':
            clean_text = text.replace('\\-', '-').replace('\\.', '.').replace('\\(', '(').replace('\\)', ')')
            clean_text = clean_text.replace('**', '').replace('*', '')
        print(clean_text)
        print(f"{'-'*40}")
        print(f"✅ DEV MODE: General message displayed in console")
        print(f"{'='*60}\n")
        return True

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
    # In dev mode, print to console instead of sending to Telegram
    from src.config import DEV_MODE  # Import dynamically to get current value
    if DEV_MODE:
        print(f"\n{'='*60}")
        print(f"🔧 DEV MODE - {language_code.upper()} MESSAGE (would send to Telegram)")
        print(f"{'='*60}")
        print(f"Language: {language_code.upper()}")
        print(f"Parse Mode: {parse_mode or 'None'}")
        print(f"Content:")
        print(f"{'-'*40}")
        # Remove markdown formatting for cleaner console output
        clean_text = text
        if parse_mode == 'MarkdownV2':
            clean_text = text.replace('\\-', '-').replace('\\.', '.').replace('\\(', '(').replace('\\)', ')')
            clean_text = clean_text.replace('**', '').replace('*', '')
        print(clean_text)
        print(f"{'-'*40}")
        print(f"✅ DEV MODE: {language_code.upper()} message displayed in console")
        print(f"{'='*60}\n")
        
        return True
    
    if not TELEGRAM_BOT_TOKEN:
        print("❌ Error: Telegram Bot Token is not configured.")
        return False
    
    # Get chat ID for this language
    chat_id = LANGUAGE_CHAT_IDS.get(language_code)
    if not chat_id:
        print(f"❌ Error: No chat ID configured for language '{language_code}'")
        print(f"💡 Add TELEGRAM_CHAT_ID_{language_code.upper()} to your .env file")
        return False
    
    # Check for duplicates
    if is_duplicate_message(text, chat_id):
        print(f"🔄 Duplicate message to {language_code.upper()}, skipping")
        return True
    
    try:
        bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
        await asyncio.wait_for(
            bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode),
            timeout=30
        )
        mark_message_sent(text, chat_id)
        print(f"📤 Message sent to {language_code.upper()} group (chat ID: {chat_id})")
        return True
    except asyncio.TimeoutError:
        print(f"⏰ Timeout sending to {language_code.upper()}, but may have been delivered")
        mark_message_sent(text, chat_id)  # Mark sent to prevent retries
        return False
    except Exception as e:
        print(f"❌ Failed to send {language_code.upper()} message: {e}")
        return False

async def send_message_to_all_languages(messages_by_language, parse_mode=None):
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
    if not alert_text:
        return {"success": False, "error": "No alert text provided"}
    
    # Prevent duplicate processing within Telethon/Webhook system
    if message_id and is_telethon_message_processed(message_id):
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
            mark_telethon_message_processed(message_id)
        
        print(f"🚨 [{source}] Emergency alert processing complete")
        return {"success": True, "results": results}
        
    except Exception as e:
        print(f"❌ Error processing [{source}] emergency alert: {e}")
        return {"success": False, "error": str(e)}

async def handle_webhook_news(news_text, source_lang_code='es', message_id=None, source="Webhook"):
    if not news_text:
        return {"success": False, "error": "No news text provided"}
    
    # Prevent duplicate processing within Telethon/Webhook system
    if message_id and is_telethon_message_processed(message_id):
        print(f"⚠️  [{source}] News {message_id} already processed, skipping")
        return {"success": True, "message": "Already processed"}
    
    print(f"\n📰 [{source}] NEWS MESSAGE")
    print(f"📍 Source: {source} ({source_lang_code.upper()})")
    print(f"📝 Text: {news_text[:100]}...")
    
    try:
        # Summarize and translate to all languages
        print("📝 Processing news content...")
        translations = await summarize_and_translate_news_telethon(news_text, source_lang_code)
        
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
            mark_telethon_message_processed(message_id)
        
        print(f"📰 [{source}] News processing complete")
        return {"success": True, "results": results}
        
    except Exception as e:
        print(f"❌ Error processing [{source}] news message: {e}")
        return {"success": False, "error": str(e)}

async def handle_emergency_alert(event):
    alert_text = event.message.text
    if not alert_text:
        return

    source_tag = f"Telethon @{SOURCE_ALERT_CHANNEL}"
    # No need for message_id - each alert is unique
    await handle_webhook_alert(alert_text, message_id=None, source=source_tag)


async def handle_news_channel_message(event, source_lang_code='es'):
    news_text = event.message.text
    if not news_text:
        return
    
    source_tag = f"Telethon @{SOURCE_NEWS_CHANNEL}"
    await handle_webhook_news(news_text, source_lang_code, message_id=f"telethon_{event.message.id}", source=source_tag)

async def start_alert_listener():
    max_retries = 5
    retry_delay = 30  # seconds
    
    for attempt in range(max_retries):
        try:
            if not setup_telethon_client():
                print("❌ Failed to set up Telethon client")
                if attempt < max_retries - 1:
                    print(f"🔄 Retrying in {retry_delay} seconds... (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(retry_delay)
                    continue
                return
            
            if not telethon_client:
                print("❌ Telethon client not available")
                return
            
            print(f"🔌 Connecting to Telegram... (attempt {attempt + 1}/{max_retries})")
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
                    try:
                        await handle_emergency_alert(event)
                    except Exception as e:
                        print(f"❌ Error handling alert: {e}")
                
                print(f"🚨 Real-time alert listener started for @{SOURCE_ALERT_CHANNEL}")
            except Exception as e:
                print(f"⚠️  Warning: Could not set up alert listener for @{SOURCE_ALERT_CHANNEL}: {e}")
                print("💡 The bot will continue running but won't receive real-time alerts from this channel")
            
            # Set up event handler for the news channel (if configured)
            if SOURCE_NEWS_CHANNEL:
                try:
                    @telethon_client.on(events.NewMessage(chats=SOURCE_NEWS_CHANNEL))
                    async def news_handler(event):
                        try:
                            await handle_news_channel_message(event, source_lang_code='es')
                        except Exception as e:
                            print(f"❌ Error handling news: {e}")
                    
                    print(f"📰 Real-time news listener started for @{SOURCE_NEWS_CHANNEL} (Spanish)")
                except Exception as e:
                    print(f"⚠️  Warning: Could not set up news listener for @{SOURCE_NEWS_CHANNEL}: {e}")
                    print("💡 The bot will continue running but won't receive real-time news from this channel")
            else:
                print("⚠️  No news channel configured. Add SOURCE_NEWS_CHANNEL to .env to enable")
            
            print("🔴 Listening for emergency alerts and news updates...")
            
            # Keep the client running with error recovery
            try:
                await telethon_client.run_until_disconnected()
            except Exception as e:
                print(f"❌ Telethon connection lost: {e}")
                raise  # Re-raise to trigger retry
            
            # If we get here, connection ended normally
            break
            
        except Exception as e:
            print(f"❌ Error in alert listener (attempt {attempt + 1}/{max_retries}): {e}")
            
            # Clean up connection
            try:
                if telethon_client and telethon_client.is_connected():
                    await telethon_client.disconnect()
            except:
                pass
            
            # Retry unless it's the last attempt
            if attempt < max_retries - 1:
                print(f"🔄 Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 300)  # Exponential backoff, max 5 minutes
            else:
                print("❌ Max retries reached. Telethon listener stopped.")
                break



async def start_webhook_server():
    from aiohttp import web, ClientSession
    import os
    
    async def webhook_alert_handler(request):
        try:
            # Clean old messages from memory
            cleanup_telethon_memory()
            
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
        try:
            # Clean old messages from memory
            cleanup_telethon_memory()
            
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
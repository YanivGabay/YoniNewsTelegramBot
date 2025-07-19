import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from src.news_fetcher import fetch_news
from src.llm_handler import get_language_name, get_language_emoji, ai_batch_filter_content, translate_alert_to_all_languages
from src.bot import send_message, send_message_to_language_group, start_alert_listener, start_webhook_server
from src.config import RSS_FEEDS, set_runtime_config
import re
import telegram.helpers
import time
import hashlib

# RSS memory (completely separate from Telethon/Webhook)
processed_rss_articles = {}  # article_hash -> timestamp

def get_identifier_from_article(article):
    """
    Creates a unique and consistent identifier for an article to prevent duplicates.
    It prioritizes the article's link, then its ID, and falls back to a hash of the title and summary.
    """
    if not isinstance(article, dict):
        return None

    # Prioritize 'link' as the most reliable identifier
    identifier = article.get('link') or article.get('id')
    
    # As a fallback, create a hash from the title and summary
    if not identifier:
        title = article.get('title', '')
        summary = article.get('summary', '')
        # Use only the first 200 chars of summary to keep it consistent
        identifier = f"{title}|{summary[:200]}"

    if not identifier.strip():
        print(f"⚠️ Could not generate a unique identifier for an article. Title: '{article.get('title', 'N/A')[:50]}...'")
        return None
        
    # Always return a hash for a consistent key format
    return hashlib.sha256(identifier.encode('utf-8')).hexdigest()

def cleanup_rss_memory():
    cutoff_time = time.time() - (3 * 60 * 60)  # 3 hours ago
    
    global processed_rss_articles
    old_count = len(processed_rss_articles)
    processed_rss_articles = {
        article_id: timestamp 
        for article_id, timestamp in processed_rss_articles.items()
        if timestamp > cutoff_time
    }
    
    cleaned_count = old_count - len(processed_rss_articles)
    if cleaned_count > 0:
        print(f"🧹 Cleaned {cleaned_count} old articles from memory (keeping {len(processed_rss_articles)} recent)")
    else:
        print(f"🧹 Memory check: {len(processed_rss_articles)} articles in 3-hour window")

def mark_as_processed(article_id):
    """Mark article as processed with current timestamp"""
    if article_id:
        processed_rss_articles[article_id] = time.time()

def is_already_processed(article_id):
    """Check if we've seen this article in the last 3 hours"""
    return article_id in processed_rss_articles if article_id else False

async def fetch_process_and_send_news():
    print("🔄 Starting news processing cycle...")
    
    # Clean old articles from memory first
    cleanup_rss_memory()
    
    all_articles = []

    # 1. Fetch from RSS feeds with limits
    print("📰 Fetching RSS feeds...")
    for feed_url, lang_code in RSS_FEEDS:
        articles = fetch_news(feed_url, limit=10)  # Limit to 10 articles per feed
        for article in articles:
            article['source_lang'] = lang_code
            article['source_type'] = 'rss'
            article['source_name'] = feed_url.split('/')[2]
        all_articles.extend(articles)
        print(f"   📊 {len(articles)} articles from {feed_url.split('/')[2]}")

    print(f"📊 Total content: {len(all_articles)} items")

    if not all_articles:
        print("❌ No content found")
        return

    # 3. Filter out already processed RSS articles (RSS-specific deduplication)
    new_articles = [
        article for article in all_articles
        if not is_already_processed(get_identifier_from_article(article))
    ]

    if not new_articles:
        print("❌ [RSS] No new content (all already processed in last 3 hours)")
        return

    print(f"🆕 New content: {len(new_articles)} items")

    # 4. Group articles by language for batch processing
    articles_by_lang = {}
    for article in new_articles:
        lang = article['source_lang']
        if lang not in articles_by_lang:
            articles_by_lang[lang] = []
        articles_by_lang[lang].append(article)

    # 5. Batch filter and rate articles by language
    print("🎯 Batch filtering and rating...")
    rated_articles = []
    
    for lang_code, articles in articles_by_lang.items():
        print(f"  🔍 Processing {len(articles)} {get_language_name(lang_code)} articles...")
        
        # Batch filter all articles for this language together
        if articles:
            rated_results = ai_batch_filter_content(articles, lang_code)
            rated_articles.extend(rated_results)

    # 6. Select top articles by rating (reduced to avoid alert interference)
    MIN_RATING = 7  # Higher threshold
    MAX_ARTICLES = 1  # Only 1 article per hour (3 messages total per hour)
    
    # Filter by minimum rating and sort by rating (highest first)
    good_articles = [(article, rating) for article, rating in rated_articles if rating >= MIN_RATING]
    good_articles.sort(key=lambda x: x[1], reverse=True)
    
    # Take top articles
    selected_articles = good_articles[:MAX_ARTICLES]
    
    print(f"🎯 Selected {len(selected_articles)} articles (rating ≥{MIN_RATING}):")
    for i, (article, rating) in enumerate(selected_articles, 1):
        source_name = article['source_name']
        title = article.get('title', article.get('summary', '')[:50] + '...')
        print(f"  {i}. {rating}/10 - {source_name} - {title}")

    if not selected_articles:
        print("❌ No articles meet minimum rating threshold")
        return

    # 7. Process selected articles
    print(f"\n📝 Processing {len(selected_articles)} selected articles...")
    
    for i, (article_to_process, importance_rating) in enumerate(selected_articles, 1):
        print(f"\n{'='*50}")
        print(f"📖 [RSS] ARTICLE {i}/{len(selected_articles)} (Rating: {importance_rating}/10)")
        print(f"{'='*50}")
        
        source_lang_code = article_to_process['source_lang']
        source_name = article_to_process['source_name']
        
        title = article_to_process.get('title')
        summary_to_clean = article_to_process.get('summary', '')

        # Clean RSS summary (remove HTML tags)
        clean_summary = re.sub('<[^<]+?>', '', summary_to_clean).strip()

        print(f"📍 [RSS] {source_name} ({get_language_name(source_lang_code)})")
        if title:
            print(f"📄 [RSS] {title}")
        print(f"📝 [RSS] {clean_summary[:100]}...")

        # Translate to all languages using simple individual calls
        text_for_llm = f"{title}\n{clean_summary}" if title else clean_summary
        
        from src.config import DEV_MODE  # Import dynamically to get current value
        if DEV_MODE:
            print(f"🔧 DEV MODE: Translating content...")
            print(f"   Source language: {get_language_name(source_lang_code)}")
        else:
            print(f"🔄 Translating...")
        
        # Use the same reliable translation method as alerts
        all_languages = await translate_alert_to_all_languages(text_for_llm, source_lang_code)

        if not all_languages:
            print("❌ Translation failed")
        else:
            print(f"✅ Got all {len(all_languages)} languages")
            
            # Send all 3 languages (source + translations)
            for lang_code, translated_content in all_languages.items():
                lang_name = get_language_name(lang_code)
                lang_emoji = get_language_emoji(lang_code)
                
                # Show brief preview
                preview = str(translated_content)[:60] + "..."
                print(f"  {lang_emoji} {lang_name}: {preview}")
                
                # Format message for Telegram (simple text format like alerts)
                message_text = f"{lang_emoji} {telegram.helpers.escape_markdown(translated_content, version=2)}\n\n\\-\\-\\-"
                
                # Send to the appropriate language group (RSS-specific sending)
                print(f"  📤 [RSS] Sending {lang_name} to {lang_code.upper()} group...")
                success = await send_message_to_language_group(message_text, lang_code, parse_mode='MarkdownV2')
                if success:
                    print(f"  ✅ {lang_name} sent to {lang_code.upper()} group!")
                
                # Longer delay between RSS messages to avoid interfering with alerts
                await asyncio.sleep(5)

        # Mark as processed using RSS-specific memory
        article_identifier = get_identifier_from_article(article_to_process)
        mark_as_processed(article_identifier)

    print(f"\n✅ Processing complete! Handled {len(selected_articles)} articles")

async def safe_fetch_process_and_send_news():
    """Wrapper with error handling for scheduler"""
    try:
        await fetch_process_and_send_news()
    except Exception as e:
        print(f"❌ Error in scheduled news processing: {e}")
        # Don't re-raise - let scheduler continue

async def safe_cleanup_memory():
    """Wrapper with error handling for memory cleanup"""
    try:
        cleanup_rss_memory()
        # Import the telethon cleanup (since RSS and Telethon are separate)
        from src.bot import cleanup_telethon_memory
        cleanup_telethon_memory()
        print("🧹 Memory cleanup completed")
    except Exception as e:
        print(f"❌ Error in memory cleanup: {e}")

async def main(dev_mode=False, debug_mode=False):
    # Set runtime configuration
    set_runtime_config(dev_mode, debug_mode)
    
    # Start the scheduled news processor with error handling
    scheduler = AsyncIOScheduler()
    scheduler.add_job(safe_fetch_process_and_send_news, 'interval', hours=1, id='news_processor')
    scheduler.add_job(safe_cleanup_memory, 'interval', hours=3, id='memory_cleanup')  # Clean every 3 hours
    scheduler.start()
    
    mode_info = ""
    if dev_mode:
        mode_info += " (DEV MODE)"
    if debug_mode:
        mode_info += " (DEBUG MODE)"
    
    print(f"🚀 YoniNews Bot started!{mode_info}")
    print("📰 Scheduled news processing: Every hour")
    print("🧹 Memory cleanup: Every 3 hours")
    print("🚨 Real-time alerts: Continuous monitoring")
    print("Press Ctrl+C to exit.")

    # Run once at startup
    print("\n🔄 Running initial news processing...")
    await safe_fetch_process_and_send_news()

    # Start webhook server, scheduler, and alert listener concurrently
    try:
        tasks = []
        
        if not dev_mode:
            # Only start these services in production mode
            webhook_task = asyncio.create_task(start_webhook_server())
            alert_task = asyncio.create_task(start_alert_listener())
            tasks = [webhook_task, alert_task]
            
            print("🚀 All systems started:")
            print("  📰 Scheduled news processing: Every hour")
            print("  🌐 Webhook server: Real-time alerts & news")
            print("  📡 Telethon listener: Real-time channel monitoring")
        else:
            print("🚀 Development mode systems started:")
            print("  📰 Scheduled news processing: Every hour (console output only)")
            print("  🚨 Webhook & Telethon disabled in dev mode")
        
        # Main loop to keep all systems running
        while True:
            await asyncio.sleep(1)
            
    except (KeyboardInterrupt, SystemExit):
        print("\n🛑 Shutting down...")
        scheduler.shutdown()
        
        # Cancel all tasks if they exist
        if not dev_mode and tasks:
            for task in tasks:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        print("👋 Bot stopped")

if __name__ == "__main__":
    asyncio.run(main()) 
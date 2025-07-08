import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from src.news_fetcher import fetch_news
from src.llm_handler import get_translations, get_language_name, get_language_emoji, ai_batch_filter_content, get_translations_all_three
from src.bot import send_message, send_message_to_language_group, start_alert_listener, start_webhook_server
from src.config import RSS_FEEDS
import re
import telegram.helpers
import time
import hashlib

# RSS-specific memory for deduplication (separate from Telethon)
processed_rss_articles = {}

def cleanup_rss_memory():
    """Remove old RSS articles from memory to prevent memory leaks"""
    global processed_rss_articles
    cutoff_time = time.time() - (3 * 60 * 60)  # 3 hours ago
    
    old_count = len(processed_rss_articles)
    processed_rss_articles = {
        article_id: timestamp 
        for article_id, timestamp in processed_rss_articles.items()
        if timestamp > cutoff_time
    }
    
    cleaned_count = old_count - len(processed_rss_articles)
    if cleaned_count > 0:
        print(f"🧹 [RSS] Cleaned {cleaned_count} old articles from memory")

def get_identifier_from_article(article):
    """Generate a unique identifier for an RSS article"""
    # Use title + summary for uniqueness
    text = f"{article.get('title', '')}{article.get('summary', '')}"
    return hashlib.md5(text.encode()).hexdigest()

def is_already_processed(article_identifier):
    """Check if we've already processed this RSS article"""
    cleanup_rss_memory()  # Clean old entries first
    return article_identifier in processed_rss_articles

def mark_as_processed(article_identifier):
    """Mark RSS article as processed"""
    processed_rss_articles[article_identifier] = time.time()

async def fetch_process_and_send_news():
    print("🔄 Starting news processing cycle...")
    
    
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

    # 6. Select top articles by rating
    MIN_RATING = 6
    MAX_ARTICLES = 2  # Maximum 2 articles per hour (2 messages per language group)
    
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

        # Translate to ALL languages (including cleaning the source)
        text_for_llm = f"{title}\n{clean_summary}" if title else clean_summary
        print(f"🔄 Translating...")
        
        # Get all 3 languages including cleaned source
        all_languages = get_translations_all_three(text_for_llm, source_lang_code)

        if not all_languages:
            print("❌ Translation failed")
        else:
            print(f"✅ Got all {len(all_languages)} languages")
            
            # Send all 3 languages (source + translations)
            for lang_code, translated_content in all_languages.items():
                lang_name = get_language_name(lang_code)
                lang_emoji = get_language_emoji(lang_code)
                
                # Show brief preview
                if isinstance(translated_content, dict):
                    if translated_content.get('title'):
                        preview = translated_content['title'][:60] + "..."
                    else:
                        preview = translated_content.get('summary', '')[:60] + "..."
                else:
                    preview = str(translated_content)[:60] + "..."
                
                print(f"  {lang_emoji} {lang_name}: {preview}")
                
                # Format message for Telegram
                if isinstance(translated_content, dict):
                    if translated_content.get('title'):
                        # Article with title
                        message_text = f"{lang_emoji} *{telegram.helpers.escape_markdown(translated_content['title'], version=2)}*\n\n{telegram.helpers.escape_markdown(translated_content['summary'], version=2)}\n\n\\-\\-\\-"
                    else:
                        # Article without title (like Telegram messages)
                        message_text = f"{lang_emoji} {telegram.helpers.escape_markdown(translated_content['summary'], version=2)}\n\n\\-\\-\\-"
                else:
                    # Fallback for simple string content
                    message_text = f"{lang_emoji} {telegram.helpers.escape_markdown(str(translated_content), version=2)}\n\n\\-\\-\\-"
                
                # Send to the appropriate language group
                print(f"  📤 [RSS] Sending {lang_name} to {lang_code.upper()} group...")
                success = await send_message_to_language_group(message_text, lang_code, parse_mode='MarkdownV2')
                if success:
                    print(f"  ✅ [RSS] Sent to {lang_code.upper()} group!")
                else:
                    print(f"  ❌ [RSS] Failed to send to {lang_code.upper()} group!")
                
                # Small delay between language sends
                await asyncio.sleep(2)

        # Mark as processed using RSS-specific memory
        article_identifier = get_identifier_from_article(article_to_process)
        mark_as_processed(article_identifier)
        
        # Delay between articles
        if i < len(selected_articles):
            print(f"⏳ Waiting 5 seconds...")
            await asyncio.sleep(5)

    print(f"\n✅ [RSS] Processing complete! Handled {len(selected_articles)} articles")


async def main():
    # Start the scheduled news processor
    scheduler = AsyncIOScheduler()
    scheduler.add_job(fetch_process_and_send_news, 'interval', hours=1)
    scheduler.start()
    print("🚀 YoniNews Bot started!")
    print("📰 Scheduled news processing: Every hour")
    print("🚨 Real-time alerts: Continuous monitoring")
    print("Press Ctrl+C to exit.")

    # Run once at startup
    print("\n🔄 Running initial news processing...")
    await fetch_process_and_send_news()

    # Start webhook server, scheduler, and alert listener concurrently
    try:
        # Create tasks for all systems
        webhook_task = asyncio.create_task(start_webhook_server())
        alert_task = asyncio.create_task(start_alert_listener())
        
        print("🚀 All systems started:")
        print("  📰 Scheduled news processing: Every hour")
        print("  🌐 Webhook server: Real-time alerts & news")
        print("  📡 Telethon listener: Real-time channel monitoring")
        
        # Main loop to keep all systems running
        while True:
            await asyncio.sleep(1)
            
    except (KeyboardInterrupt, SystemExit):
        print("\n🛑 Shutting down...")
        scheduler.shutdown()
        
        # Cancel all tasks
        if 'webhook_task' in locals():
            webhook_task.cancel()
            try:
                await webhook_task
            except asyncio.CancelledError:
                pass
        
        if 'alert_task' in locals():
            alert_task.cancel()
            try:
                await alert_task
            except asyncio.CancelledError:
                pass
        
        print("👋 Bot stopped")

if __name__ == "__main__":
    asyncio.run(main()) 
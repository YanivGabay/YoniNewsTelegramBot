import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from src.news_fetcher import fetch_news
from src.telegram_fetcher import fetch_telegram_messages
from src.llm_handler import get_translations, get_language_name, get_language_emoji, ai_filter_content, ai_clean_telegram_content, ai_batch_filter_content, get_translations_all_three
from src.bot import send_message, start_alert_listener
from src.config import RSS_FEEDS, SOURCE_TELEGRAM_CHANNELS
import random
import html
import re
import telegram.helpers
import time

# Time-based memory management (article_id -> timestamp)
processed_articles = {}

def cleanup_memory():
    """Remove articles older than 3 hours to keep memory manageable"""
    cutoff_time = time.time() - (3 * 60 * 60)  # 3 hours ago
    
    old_count = len(processed_articles)
    
    # Keep only articles processed within the last 3 hours
    global processed_articles
    processed_articles = {
        article_id: timestamp 
        for article_id, timestamp in processed_articles.items()
        if timestamp > cutoff_time
    }
    
    cleaned_count = old_count - len(processed_articles)
    if cleaned_count > 0:
        print(f"🧹 Cleaned {cleaned_count} old articles from memory (keeping {len(processed_articles)} recent)")
    else:
        print(f"🧹 Memory check: {len(processed_articles)} articles in 3-hour window")

def mark_as_processed(article_id):
    """Mark article as processed with current timestamp"""
    if article_id:
        processed_articles[article_id] = time.time()

def is_already_processed(article_id):
    """Check if we've seen this article in the last 3 hours"""
    return article_id in processed_articles if article_id else False

async def fetch_process_and_send_news():
    print("🔄 Starting news processing cycle...")
    
    # Clean old articles from memory first
    cleanup_memory()
    
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

    # 2. Fetch from Telegram channels with individual filtering (keep existing logic)
    print("📱 Processing Telegram channels...")
    telegram_articles = []
    for channel_username, lang_code in SOURCE_TELEGRAM_CHANNELS:
        messages = await fetch_telegram_messages(channel_username)
        print(f"   🔍 {len(messages)} messages from @{channel_username}")
        
        for message in messages:
            # Individual filter for Telegram (existing logic)
            filter_result = ai_filter_content(message['summary'], lang_code)
            
            if filter_result == 'NEWS':
                cleaned_content = ai_clean_telegram_content(message['summary'], lang_code)
                message['summary'] = cleaned_content
                message['source_lang'] = lang_code
                message['source_type'] = 'telegram'
                message['source_name'] = f"@{channel_username}"
                telegram_articles.append(message)
                print(f"     ✅ Message accepted")
            else:
                print(f"     ❌ Message rejected (AD)")
                
    all_articles.extend(telegram_articles)
    print(f"📊 Total content: {len(all_articles)} items")

    if not all_articles:
        print("❌ No content found")
        return

    # 3. Filter out already processed articles using new time-based system
    new_articles = [
        article for article in all_articles
        if not is_already_processed(article.get('id') or article.get('link'))
    ]

    if not new_articles:
        print("❌ No new content (all already processed in last 3 hours)")
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
        
        # Only batch filter RSS articles (Telegram already filtered individually)
        rss_articles = [a for a in articles if a['source_type'] == 'rss']
        telegram_articles = [a for a in articles if a['source_type'] == 'telegram']
        
        if rss_articles:
            rss_rated = ai_batch_filter_content(rss_articles, lang_code)
            rated_articles.extend(rss_rated)
            
        # Telegram articles get default rating of 6 (already filtered)
        for tg_article in telegram_articles:
            rated_articles.append((tg_article, 6))
            print(f"  ✅ Telegram: AUTO:6")

    # 6. Select top articles by rating
    MIN_RATING = 6
    MAX_ARTICLES = 5
    
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
        print(f"📖 ARTICLE {i}/{len(selected_articles)} (Rating: {importance_rating}/10)")
        print(f"{'='*50}")
        
        source_lang_code = article_to_process['source_lang']
        source_name = article_to_process['source_name']
        
        title = article_to_process.get('title')
        summary_with_html = article_to_process.get('summary', '')
        clean_summary = re.sub('<[^<]+?>', '', summary_with_html).strip()

        print(f"📍 {source_name} ({get_language_name(source_lang_code)})")
        if title:
            print(f"📄 {title}")
        print(f"📝 {clean_summary[:100]}...")

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
                
                # Send to Telegram
                print(f"  📤 Sending {lang_name} to Telegram...")
                success = await send_message(message_text, parse_mode='MarkdownV2')
                if success:
                    print(f"  ✅ {lang_name} sent!")
                else:
                    print(f"  ❌ {lang_name} failed to send!")
                
                # Small delay between language sends
                await asyncio.sleep(2)

        # Mark as processed
        article_identifier = article_to_process.get('id') or article_to_process.get('link')
        mark_as_processed(article_identifier)
        
        # Delay between articles
        if i < len(selected_articles):
            print(f"⏳ Waiting 5 seconds...")
            await asyncio.sleep(5)

    print(f"\n✅ Processing complete! Handled {len(selected_articles)} articles")


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

    # Start both the scheduler and alert listener concurrently
    try:
        # Create tasks for both systems
        alert_task = asyncio.create_task(start_alert_listener())
        
        # Main loop to keep the scheduler running
        while True:
            await asyncio.sleep(1)
            
    except (KeyboardInterrupt, SystemExit):
        print("\n🛑 Shutting down...")
        scheduler.shutdown()
        
        # Cancel the alert listener task
        if 'alert_task' in locals():
            alert_task.cancel()
            try:
                await alert_task
            except asyncio.CancelledError:
                pass
        
        print("👋 Bot stopped")

if __name__ == "__main__":
    asyncio.run(main()) 
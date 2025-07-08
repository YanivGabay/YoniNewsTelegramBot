#!/usr/bin/env python3
"""
Simple RSS feed test - just shows what news each feed has.
No translation, no API calls, just raw feed data.
"""

from src.news_fetcher import fetch_news
from src.config import RSS_FEEDS
from src.llm_handler import get_language_name
import re

def clean_html_tags(text):
    """Remove HTML tags from text"""
    return re.sub('<[^<]+?>', '', text).strip()

def test_rss_feeds():
    print("🧪 RSS Feed Test - Raw Data Only")
    print("=" * 60)
    
    if not RSS_FEEDS:
        print("❌ No RSS feeds configured!")
        print("RSS_FEEDS is empty. Check src/config.py")
        return
    
    print(f"📰 Testing {len(RSS_FEEDS)} RSS feeds:")
    for i, (feed_url, lang_code) in enumerate(RSS_FEEDS, 1):
        print(f"  {i}. {feed_url} ({lang_code.upper()})")
    
    print("\n" + "=" * 60)
    
    for feed_index, (feed_url, lang_code) in enumerate(RSS_FEEDS, 1):
        print(f"\n📡 FEED {feed_index}/{len(RSS_FEEDS)}: {feed_url}")
        print(f"🌐 Language: {get_language_name(lang_code)} ({lang_code.upper()})")
        print("-" * 60)
        
        try:
            # Fetch articles (limit to 5 for testing)
            articles = fetch_news(feed_url, limit=5)
            
            if not articles:
                print("❌ No articles fetched from this feed")
                print("   This could mean:")
                print("   - Feed is down")
                print("   - Feed URL is incorrect") 
                print("   - Network/SSL issues")
                continue
            
            print(f"✅ Successfully fetched {len(articles)} articles")
            
            # Display each article
            for i, article in enumerate(articles, 1):
                print(f"\n  📄 Article {i}:")
                
                title = article.get('title', 'No title')
                print(f"     Title: {title}")
                
                link = article.get('link', 'No link')
                print(f"     Link: {link}")
                
                summary = article.get('summary', '')
                if summary:
                    clean_summary = clean_html_tags(summary)
                    # Show first 200 characters
                    preview = clean_summary[:200] + "..." if len(clean_summary) > 200 else clean_summary
                    print(f"     Summary: {preview}")
                else:
                    print(f"     Summary: No summary available")
                
                article_id = article.get('id', 'No ID')
                print(f"     ID: {article_id}")
        
        except Exception as e:
            print(f"❌ Error fetching from this feed: {e}")
            print(f"   Feed URL: {feed_url}")
        
        print("-" * 60)
    
    print(f"\n🎯 RSS Test Complete!")
    print("=" * 60)

if __name__ == "__main__":
    test_rss_feeds() 
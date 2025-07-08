import feedparser
from src.error_handler import handle_feed_error
import requests

@handle_feed_error
def fetch_news(feed_url, limit=10):
    """
    Fetches news from a given RSS feed URL using the requests library
    for better reliability and timeout handling.
    Returns a list of articles.
    """
    print(f"   Fetching from {feed_url}...")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    # Use requests to fetch the content with a timeout
    try:
        response = requests.get(feed_url, headers=headers, timeout=15) # 15-second timeout
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
        
        # Pass the content to feedparser
        feed = feedparser.parse(response.content)
        
    except requests.exceptions.RequestException as e:
        print(f"Error using requests for {feed_url}: {e}")
        return [] # Return empty list on request failure

    if feed.bozo:
        # Bozo feeds are malformed, but we can still try to read them.
        # The error is logged, and we proceed.
        print(f"Warning: Malformed feed from {feed_url}. Reason: {feed.bozo_exception}")

    articles = []
    for entry in feed.entries[:limit]:
        articles.append({
            'title': entry.get('title', ''),
            'summary': entry.get('summary', entry.get('description', '')), # Also check 'description'
            'link': entry.get('link', ''),
            'id': entry.get('id', entry.get('link')) # Use link as fallback for id
        })
        
    return articles

if __name__ == '__main__':
    # Example usage with a sample RSS feed
    sample_feed_url = "http://www.ynet.co.il/Integration/StoryRss2.xml" # Ynet news in Hebrew
    news_articles = fetch_news(sample_feed_url, limit=5)
    if news_articles:
        print(f"Fetched {len(news_articles)} articles from {sample_feed_url}")
        for article in news_articles[:2]: # Print details of the first 2 articles
            print("\n---")
            print(f"Title: {article.title}")
            print(f"Link: {article.link}")
            if 'summary' in article:
                print(f"Summary: {article.summary}")
            print("---")
    else:
        print("No articles fetched.") 
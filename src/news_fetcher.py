import feedparser

def fetch_news(feed_url, limit=10):
    """
    Fetches and parses an RSS feed.
    """
    try:
        feed = feedparser.parse(feed_url)
        if feed.bozo:
            print(f"Error parsing feed {feed_url}: {feed.bozo_exception}")
            return []
        
        # Limit the number of articles returned
        articles = feed.entries[:limit] if limit else feed.entries
        return articles
    except Exception as e:
        print(f"Could not fetch or parse feed from {feed_url}. Error: {e}")
        return []

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
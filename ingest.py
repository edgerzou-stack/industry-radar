import feedparser
from datetime import datetime, timedelta

def fetch_rss_feeds(feeds, hours_back=168):
    """Fetches articles from a list of RSS feeds within the last X hours."""
    articles = []
    time_limit = datetime.now() - timedelta(hours=hours_back)
    
    import requests
    for feed_url in feeds:
        print(f"Fetching from {feed_url}...")
        try:
            # Use requests with a timeout to prevent feedparser from hanging on bad connections
            res = requests.get(feed_url, timeout=10)
            feed = feedparser.parse(res.content)
            for entry in feed.entries:
                # Parse publication date
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    pub_date = datetime(*entry.published_parsed[:6])
                elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                    pub_date = datetime(*entry.updated_parsed[:6])
                else:
                    pub_date = datetime.now()
                
                if pub_date >= time_limit:
                    articles.append({
                        'title': entry.title,
                        'link': entry.link,
                        'summary': getattr(entry, 'summary', ''),
                        'source': feed.feed.title if hasattr(feed.feed, 'title') else feed_url,
                        'published_at': pub_date.isoformat()
                    })
        except Exception as e:
            print(f"Error fetching {feed_url}: {e}")
            
    return articles

if __name__ == "__main__":
    feeds = ["https://techcrunch.com/feed/"]
    print(fetch_rss_feeds(feeds, hours_back=168))

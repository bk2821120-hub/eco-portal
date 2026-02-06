import feedparser
import re
from datetime import datetime

feeds = [
    ("https://feeds.bbci.co.uk/news/science_and_environment/rss.xml", "Climate Change"),
    ("https://www.sciencedaily.com/rss/earth_climate/environmental_science.xml", "Green Tech"),
    ("https://www.downtoearth.org.in/rss/environment", "India/Wildlife"),
    ("https://news.google.com/rss/search?q=pollution+awareness+india&hl=en-IN&gl=IN&ceid=IN:en", "Pollution")
]

educational_news = []

for url, category in feeds:
    try:
        print(f"Fetching {url}...")
        feed = feedparser.parse(url)
        print(f"Found {len(feed.entries)} entries")
        for entry in feed.entries[:2]:
            raw_text = re.sub('<[^<]+?>', '', entry.summary) if 'summary' in entry else ""
            print(f"Entry: {entry.title[:50]}...")
    except Exception as e:
        print(f"Error: {e}")

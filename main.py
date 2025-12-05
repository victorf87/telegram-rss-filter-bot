import feedparser
import os
import requests
from datetime import datetime, timedelta

# Загрузка переменных
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# Загрузка ключевых слов
with open("keywords.txt", "r", encoding="utf-8") as f:
    keywords = [line.strip().lower() for line in f if line.strip()]

# Загрузка RSS-лент
with open("feeds.txt", "r", encoding="utf-8") as f:
    feed_urls = [line.strip() for line in f if line.strip()]

def post_to_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    requests.post(url, data=data)

def is_recent(published):
    try:
        published_time = datetime(*feedparser._parse_date(published)[:6])
        return datetime.utcnow() - published_time < timedelta(hours=1)
    except:
        return False

def main():
    for url in feed_urls:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            title = entry.title
            link = entry.link
            published = entry.get("published", "")

            if not is_recent(published):
                continue

            title_lower = title.lower()
            if any(keyword in title_lower for keyword in keywords):
                message = f"<b>{title}</b>\n{link}"
                post_to_telegram(message)

if __name__ == "__main__":
    post_to_telegram("🎯 Тестовое сообщение: бот работает!")
    main()

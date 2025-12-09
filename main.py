import os
import requests
import feedparser
from datetime import datetime, timedelta, timezone
import time

BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

if not BOT_TOKEN or not CHAT_ID:
    raise EnvironmentError('BOT_TOKEN и/или CHAT_ID не заданы')

# Ключевые слова и ленты не меняются
with open('keywords.txt', 'r', encoding='utf-8') as f:
    KEYWORDS = [line.strip().lower() for line in f if line.strip()]

with open('feeds.txt', 'r', encoding='utf-8') as f:
    FEED_URLS = [line.strip() for line in f if line.strip()]

# Файл, где будем хранить уже отправленные ссылки
SENT_FILE = 'sent_articles.txt'

def load_sent_links() -> set[str]:
    """Загружает множество уже отправленных ссылок из файла."""
    if not os.path.exists(SENT_FILE):
        return set()
    with open(SENT_FILE, 'r', encoding='utf-8') as f:
        return {line.strip() for line in f if line.strip()}

def save_sent_link(link: str) -> None:
    """Добавляет новую ссылку в файл отправленных."""
    with open(SENT_FILE, 'a', encoding='utf-8') as f:
        f.write(link + '\n')

def post_to_telegram(text: str) -> None:
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    data = {
        'chat_id': CHAT_ID,
        'text': text,
        'parse_mode': 'HTML',
        'disable_web_page_preview': False,
    }
    resp = requests.post(url, data=data, timeout=10)
    if resp.status_code != 200:
        print(f'[ERROR] Telegram API returned {resp.status_code}: {resp.text}')

TIME_WINDOW = timedelta(hours=12)

def is_recent(published_parsed) -> bool:
    if not published_parsed:
        return False
    try:
        published_time = datetime.fromtimestamp(
            time.mktime(published_parsed), tz=timezone.utc
        )
    except Exception:
        return False
    return datetime.now(timezone.utc) - published_time < TIME_WINDOW

def main():
    sent_links = load_sent_links()
    for url in FEED_URLS:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            title = entry.get('title', '')
            link = entry.get('link', '')
            published_parsed = entry.get('published_parsed') or entry.get('updated_parsed')
            if not is_recent(published_parsed):
                continue
            title_lower = title.lower()
            if any(keyword in title_lower for keyword in KEYWORDS):
                # Проверяем, отправляли ли мы эту ссылку ранее
                if link in sent_links:
                    print(f'[DEBUG] Уже отправлено: {title}')
                    continue
                # Формируем активную ссылку
                message = f'<a href="{link}"><b>{title}</b></a>'
                print(f'[INFO] Отправка: {title}')
                post_to_telegram(message)
                # Добавляем ссылку в список отправленных
                save_sent_link(link)
                sent_links.add(link)
            else:
                print(f'[DEBUG] Пропуск (не содержит ключевое слово): {title}')

if __name__ == '__main__':
    main()

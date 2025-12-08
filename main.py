import os
import requests
import feedparser
from datetime import datetime, timedelta, timezone
import time

# Загрузка переменных окружения
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

# Проверка обязательных переменных
if not BOT_TOKEN or not CHAT_ID:
    raise EnvironmentError('BOT_TOKEN и/или CHAT_ID не заданы')

# Загрузка ключевых слов
with open('keywords.txt', 'r', encoding='utf-8') as f:
    KEYWORDS = [line.strip().lower() for line in f if line.strip()]

# Загрузка RSS‑лент
with open('feeds.txt', 'r', encoding='utf-8') as f:
    FEED_URLS = [line.strip() for line in f if line.strip()]

def post_to_telegram(text: str) -> None:
    """Отправляет текстовое сообщение в телеграм‑канал."""
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

# Интервал, в пределах которого новости считаются свежими
TIME_WINDOW = timedelta(hours=12)

def is_recent(published_parsed) -> bool:
    """Проверяет, что новость была опубликована в течение последнего TIME_WINDOW."""
    try:
        if not published_parsed:
            return False
        # Преобразуем struct_time в datetime c учётом UTC
        published_time = datetime.fromtimestamp(
            time.mktime(published_parsed), tz=timezone.utc
        )
        return datetime.now(timezone.utc) - published_time < TIME_WINDOW
    except Exception:
        return False

def main() -> None:
    """Основная логика: парсинг лент, фильтрация по ключевым словам и отправка."""
    for url in FEED_URLS:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            title = entry.get('title', '')
            link = entry.get('link', '')
            # В некоторых лентах может отсутствовать published_parsed; используем updated_parsed
            published_parsed = entry.get('published_parsed') or entry.get('updated_parsed')
            # Проверяем свежесть
            if not is_recent(published_parsed):
                continue
            title_lower = title.lower()
            if any(keyword in title_lower for keyword in KEYWORDS):
                # формируем активную ссылку
                message = f'<a href="{link}"><b>{title}</b></a>'
                print(f'[INFO] Отправка: {title}')
                post_to_telegram(message)
            else:
                print(f'[DEBUG] Пропуск: {title}')

if __name__ == '__main__':
    main()

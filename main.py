import os
import requests
import feedparser
from datetime import datetime, timedelta, timezone
import time
import urllib.parse
import hashlib

BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

if not BOT_TOKEN or not CHAT_ID:
    raise EnvironmentError('BOT_TOKEN и/или CHAT_ID не заданы')

with open('keywords.txt', 'r', encoding='utf-8') as f:
    KEYWORDS = [line.strip().lower() for line in f if line.strip()]

with open('feeds.txt', 'r', encoding='utf-8') as f:
    FEED_URLS = [line.strip() for line in f if line.strip()]

# Файл, где будем хранить уже отправленные идентификаторы
SENT_FILE = 'sent_articles.txt'

def load_sent_ids() -> set[str]:
    """Загружает множество уже отправленных идентификаторов из файла."""
    if not os.path.exists(SENT_FILE):
        return set()
    with open(SENT_FILE, 'r', encoding='utf-8') as f:
        return {line.strip() for line in f if line.strip()}

def save_sent_id(sent_id: str) -> None:
    """Добавляет новый идентификатор в файл отправленных."""
    with open(SENT_FILE, 'a', encoding='utf-8') as f:
        f.write(sent_id + '\n')

def canonical_link(url: str) -> str:
    """Возвращает ссылку без query‑параметров и якоря."""
    parsed = urllib.parse.urlparse(url)
    # собираем URL из компонентов, обнуляя параметры и якорь
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))

def entry_id(entry) -> str:
    """Формирует уникальный идентификатор для записи."""
    link = canonical_link(entry.get('link', ''))
    eid = entry.get('id')
    # если в RSS присутствует id, используем его + канонический адрес; иначе хэшируем заголовок и ссылку
    if eid:
        return f'{eid}|{link}'
    # fallback: хэш title+canonical_link
    unique_str = f"{entry.get('title','')}_{link}"
    return hashlib.md5(unique_str.encode('utf-8')).hexdigest()

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
    sent_ids = load_sent_ids()
    for url in FEED_URLS:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            title = entry.get('title', '')
            if not title:
                continue
            pub_parsed = entry.get('published_parsed') or entry.get('updated_parsed')
            if not is_recent(pub_parsed):
                continue

            # нормализуем идентификатор записи (каноническая ссылка + id или хэш)
            uid = entry_id(entry)
            # проверка по ключевым словам
            title_lower = title.lower()
            if any(keyword in title_lower for keyword in KEYWORDS):
                # проверка на дубликат
                if uid in sent_ids:
                    print(f'[DEBUG] Уже отправлено: {title}')
                    continue
                link = canonical_link(entry.get('link', ''))
                message = f'<a href="{link}"><b>{title}</b></a>'
                print(f'[INFO] Отправка: {title}')
                post_to_telegram(message)
                save_sent_id(uid)
                sent_ids.add(uid)
            else:
                print(f'[DEBUG] Пропуск (не содержит ключевое слово): {title}')

if __name__ == '__main__':
    main()

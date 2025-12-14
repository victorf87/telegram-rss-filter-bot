import os
import time
import hashlib
import urllib.parse
from datetime import datetime, timedelta, timezone

import feedparser
import requests

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    raise EnvironmentError("BOT_TOKEN и/или CHAT_ID не заданы")

# Загружаем ключевые слова и ленты
with open("keywords.txt", "r", encoding="utf-8") as f:
    KEYWORDS = [line.strip().lower() for line in f if line.strip()]

with open("feeds.txt", "r", encoding="utf-8") as f:
    FEED_URLS = [line.strip() for line in f if line.strip()]

# Файл для сохранения отправленных идентификаторов
SENT_FILE = "sent_articles.txt"


def load_sent_ids() -> set[str]:
    """Загружаем уже отправленные ID статей из файла."""
    if not os.path.exists(SENT_FILE):
        return set()

    with open(SENT_FILE, "r", encoding="utf-8") as f:
        return {line.strip() for line in f if line.strip()}


def save_sent_id(sent_id: str) -> None:
    """Добавляем один ID в файл отправленных статей."""
    with open(SENT_FILE, "a", encoding="utf-8") as f:
        f.write(sent_id + "\n")


def canonical_link(url: str) -> str:
    """
    Приводим ссылку к каноническому виду:
    - https
    - без www.
    - без завершающего слеша
    """
    parsed = urllib.parse.urlparse(url)
    scheme = "https"
    host = parsed.netloc.lower()

    if host.startswith("www."):
        host = host[4:]

    path = parsed.path.rstrip("/")

    return urllib.parse.urlunparse((scheme, host, path, "", "", ""))


def entry_id(entry) -> str:
    """
    Формируем стабильный ID записи по title + canonical link.
    """
    title = entry.get("title", "").strip().lower()
    link_raw = entry.get("link", "")
    link = canonical_link(link_raw) if link_raw else ""

    data = f"{title}|{link}"
    return hashlib.md5(data.encode("utf-8")).hexdigest()


def post_to_telegram(text: str) -> None:
    """Отправка одного сообщения в Telegram."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }

    resp = requests.post(url, data=data, timeout=10)
    if resp.status_code != 200:
        print(f"[ERROR] Telegram API returned {resp.status_code}: {resp.text}")


# Берём статьи за последние 12 часов
TIME_WINDOW = timedelta(hours=12)


def is_recent(published_parsed) -> bool:
    """Проверяем, попадает ли дата публикации в заданное окно."""
    if not published_parsed:
        return False

    try:
        published_time = datetime.fromtimestamp(
            time.mktime(published_parsed),
            tz=timezone.utc,
        )
    except Exception:
        return False

    return datetime.now(timezone.utc) - published_time < TIME_WINDOW


def main() -> None:
    sent_ids = load_sent_ids()

    for url in FEED_URLS:
        feed = feedparser.parse(url)

        for entry in feed.entries:
            title = entry.get("title", "").strip()
            if not title:
                continue

            pub_parsed = entry.get("published_parsed") or entry.get("updated_parsed")
            if not is_recent(pub_parsed):
                continue

            title_lower = title.lower()
            if not any(keyword in title_lower for keyword in KEYWORDS):
                print(f"[DEBUG] Пропуск (не содержит ключевое слово): {title}")
                continue

            uid = entry_id(entry)
            if uid in sent_ids:
                print(f"[DEBUG] Уже отправлено: {title}")
                continue

            link_raw = entry.get("link", "").strip()
            link = canonical_link(link_raw) if link_raw else ""

            if link:
                # Нормальное HTML-сообщение: кликабельный заголовок
                message = f'<a href="{link}">{title}</a>'
            else:
                # На всякий случай, если вдруг нет ссылки
                message = title

            print(f"[INFO] Отправка: {title}")
            post_to_telegram(message)

            save_sent_id(uid)
            sent_ids.add(uid)


if __name__ == "__main__":
    main()

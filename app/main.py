import asyncio
import logging
import os
import re
from datetime import datetime, timezone, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telethon import TelegramClient
from telegram import Bot
from telegram.constants import ParseMode
from dotenv import load_dotenv

from app.database import Database

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ── Конфігурація ──────────────────────────────────────────────
TELEGRAM_API_ID   = int(os.environ["TELEGRAM_API_ID"])
TELEGRAM_API_HASH = os.environ["TELEGRAM_API_HASH"]
BOT_TOKEN         = os.environ["BOT_TOKEN"]
NOTIFY_CHAT_ID    = int(os.environ["NOTIFY_CHAT_ID"])   # ваш особистий chat_id
SCAN_INTERVAL_H   = int(os.getenv("SCAN_INTERVAL_HOURS", "2"))
SESSION_FILE      = "data/scanner.session"

# ── Канали для моніторингу (username або числовий id) ─────────
CHANNELS: list[str | int] = [
    ch.strip()
    for ch in os.getenv("CHANNELS", "").split(",")
    if ch.strip()
]

# ── Ключові слова для фільтрації ──────────────────────────────
KEYWORDS: list[str] = [
    kw.strip().lower()
    for kw in os.getenv(
        "KEYWORDS",
        "junior python,junior developer,junior dev,джуніор python,"
        "python junior,джун python,стажер python,intern python,"
        "trainee python,junior qa,junior data",
    ).split(",")
    if kw.strip()
]

ANTI_KEYWORDS: list[str] = [
    kw.strip().lower()
    for kw in os.getenv("ANTI_KEYWORDS", "senior,lead,middle,").split(",")
    if kw.strip()
]


def is_relevant(text: str) -> bool:
    """Перевіряє чи повідомлення відповідає критеріям вакансії."""
    text_l = text.lower()
    has_keyword = any(kw in text_l for kw in KEYWORDS)
    has_anti    = any(kw in text_l for kw in ANTI_KEYWORDS)
    return has_keyword and not has_anti


def format_vacancy(channel: str, message) -> str:
    """Форматує повідомлення для надсилання."""
    date_str = message.date.strftime("%d.%m.%Y %H:%M")
    link = f"https://t.me/{channel.lstrip('@')}/{message.id}"
    text = (message.text or "")[:3000]
    return (
        f"🔍 *Нова вакансія*\n"
        f"📢 Канал: `{channel}`\n"
        f"📅 {date_str}\n\n"
        f"{text}\n\n"
        f"🔗 [Відкрити повідомлення]({link})"
    )


async def scan_channels(db: Database, bot: Bot, client: TelegramClient):
    """Основна функція сканування каналів."""
    log.info("▶ Починаємо сканування %d каналів...", len(CHANNELS))
    found = 0

    for channel in CHANNELS:
        try:
            entity = await client.get_entity(channel)
            # Беремо повідомлення за останні N годин
            cutoff = datetime.now(timezone.utc) - timedelta(days=2)
            async for message in client.iter_messages(entity, limit=100):
                if message.date < cutoff:
                    break
                if not message.text:
                    continue
                # Пропускаємо старі (вже скановані раніше)
                if await db.is_seen(message.id, str(entity.id)):
                    continue
                if is_relevant(message.text):
                    text = format_vacancy(channel, message)
                    await bot.send_message(
                        chat_id=NOTIFY_CHAT_ID,
                        text=text,
                        parse_mode=ParseMode.MARKDOWN,
                        disable_web_page_preview=False,
                    )
                    found += 1
                    log.info("  ✅ Відправлено: channel=%s msg_id=%s", channel, message.id)
                    await asyncio.sleep(1)  # throttle

                await db.mark_seen(message.id, str(entity.id), message.text[:500])

        except Exception as exc:
            log.error("  ❌ Помилка каналу %s: %s", channel, exc)

    log.info("◀ Сканування завершено. Нових вакансій: %d", found)
    if found == 0:
        log.info("   (нових вакансій не знайдено)")


async def main():
    db = Database(os.environ["DATABASE_URL"])
    await db.init()

    bot = Bot(token=BOT_TOKEN)
    await bot.send_message(NOTIFY_CHAT_ID, "🤖 Vacancy Scanner запущено! Перше сканування зараз...")

    async with TelegramClient(SESSION_FILE, TELEGRAM_API_ID, TELEGRAM_API_HASH) as client:
        # Перше сканування одразу
        await scan_channels(db, bot, client)

        # Планувальник
        scheduler = AsyncIOScheduler()
        scheduler.add_job(
            scan_channels,
            "interval",
            hours=SCAN_INTERVAL_H,
            args=[db, bot, client],
        )
        scheduler.start()
        log.info("⏰ Наступне сканування через %d год.", SCAN_INTERVAL_H)

        await asyncio.Event().wait()  # Тримаємо процес живим


if __name__ == "__main__":
    asyncio.run(main())

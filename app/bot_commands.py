"""
Опційний модуль: Telegram-бот для керування сканером через команди.
Запускається окремо або разом з main.py.

Команди:
  /start   — реєстрація (отримати chat_id)
  /status  — статус сканера
  /last    — останні 5 вакансій з БД
  /scan    — запустити сканування вручну
  /help    — список команд
"""
import asyncio
import logging
import os

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from dotenv import load_dotenv

from app.database import Database

load_dotenv()
log = logging.getLogger(__name__)

BOT_TOKEN      = os.environ["BOT_TOKEN"]
ADMIN_CHAT_ID  = int(os.environ["NOTIFY_CHAT_ID"])


def admin_only(func):
    """Декоратор: тільки адмін може виконувати команду."""
    async def wrapper(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != ADMIN_CHAT_ID:
            await update.message.reply_text("⛔ Доступ заборонено.")
            return
        return await func(update, ctx)
    return wrapper


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await update.message.reply_text(
        f"👋 Привіт! Твій chat_id: `{chat_id}`\n"
        "Додай його до `.env` як `NOTIFY_CHAT_ID`.",
        parse_mode="Markdown",
    )


@admin_only
async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    db: Database = ctx.application.bot_data["db"]
    count_row = await db._pool.fetchval("SELECT COUNT(*) FROM seen_messages")
    vacancy_count = await db._pool.fetchval("SELECT COUNT(*) FROM vacancies")
    await update.message.reply_text(
        f"📊 *Статус сканера*\n"
        f"👁 Переглянуто повідомлень: `{count_row}`\n"
        f"💼 Знайдено вакансій: `{vacancy_count}`",
        parse_mode="Markdown",
    )


@admin_only
async def cmd_last(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    db: Database = ctx.application.bot_data["db"]
    vacancies = await db.get_recent_vacancies(limit=5)
    if not vacancies:
        await update.message.reply_text("🔍 Вакансій ще немає в БД.")
        return
    for v in vacancies:
        preview = (v["text"] or "")[:400]
        await update.message.reply_text(
            f"📅 {v['sent_at'].strftime('%d.%m.%Y %H:%M')}\n"
            f"📢 Канал: `{v['channel_id']}`\n\n{preview}...",
            parse_mode="Markdown",
        )


@admin_only
async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Vacancy Scanner Bot*\n\n"
        "/status — статистика\n"
        "/last   — останні 5 вакансій\n"
        "/help   — ця довідка",
        parse_mode="Markdown",
    )


async def run_bot():
    db = Database(os.environ["DATABASE_URL"])
    await db.init()

    app = Application.builder().token(BOT_TOKEN).build()
    app.bot_data["db"] = db

    app.add_handler(CommandHandler("start",  cmd_start))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("last",   cmd_last))
    app.add_handler(CommandHandler("help",   cmd_help))

    log.info("🤖 Bot запущено")
    await app.run_polling()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_bot())

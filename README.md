# 🤖 Vacancy Scanner Bot

Сканує Telegram-канали з вакансіями і надсилає знайдені позиції Junior Python Developer у ваш Telegram кожні 2 години.

## Структура проєкту

```
vacancy_bot/
├── app/
│   ├── main.py           # сканер каналів + планувальник
│   ├── database.py       # робота з PostgreSQL
│   └── bot_commands.py   # команди бота (/status, /last)
├── data/                 # telethon session
├── run.py                # точка входу
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

## Швидкий старт

### 1. Отримайте Telegram API ключі
Зайдіть на https://my.telegram.org → "API development tools" → створіть додаток.
Збережіть api_id і api_hash.

### 2. Створіть Telegram-бота
Напишіть @BotFather → /newbot → збережіть BOT_TOKEN.

### 3. Дізнайтесь свій chat_id
Запустіть бота (/start) — він відповість вашим chat_id.

### 4. Налаштуйте .env
```bash
cp .env.example .env
nano .env
```

### 5. Перша авторизація Telethon
```bash
mkdir -p data
pip install telethon python-dotenv
python - <<'PY'
from telethon.sync import TelegramClient
import os; from dotenv import load_dotenv; load_dotenv()
client = TelegramClient("data/scanner.session", int(os.environ["TELEGRAM_API_ID"]), os.environ["TELEGRAM_API_HASH"])
client.start()
print("OK — session збережено")
PY
```

### 6. Запуск через Docker
```bash
docker compose up -d
```

### 7. Запуск без Docker
```bash
pip install -r requirements.txt
python run.py
```

## Команди бота
| Команда | Дія |
|---|---|
| /start  | Показує ваш chat_id |
| /status | Статистика |
| /last   | Останні 5 вакансій з БД |
| /help   | Список команд |

## Конфігурація (.env)
| Змінна | Опис |
|---|---|
| TELEGRAM_API_ID | ID з my.telegram.org |
| TELEGRAM_API_HASH | Hash з my.telegram.org |
| BOT_TOKEN | Токен від BotFather |
| NOTIFY_CHAT_ID | Ваш особистий chat_id |
| DATABASE_URL | PostgreSQL рядок підключення |
| CHANNELS | Канали через кому: @djinni_jobs,@python_jobs_ua |
| KEYWORDS | Ключові слова (через кому, lowercase) |
| ANTI_KEYWORDS | Слова-виключення (senior,lead,middle) |
| SCAN_INTERVAL_HOURS | Інтервал (за замовч. 2) |

## Рекомендовані канали
```
@djinni_jobs           — Djinni (найбільше IT-вакансій UA)
@python_jobs_ua        — Python вакансії
@it_vacancies_ukraine  — IT вакансії загальні
@junior_jobs_ua        — вакансії для джунів
@robotaua_jobs         — robota.ua
```

## Корисні SQL-запити
```sql
-- Останні вакансії
SELECT channel_id, sent_at, LEFT(text, 100) FROM vacancies ORDER BY sent_at DESC LIMIT 10;

-- Статистика по каналах
SELECT channel_id, COUNT(*) FROM vacancies GROUP BY channel_id ORDER BY 2 DESC;
```

## Важливо
- Telethon читає канали від імені вашого акаунту — не зловживайте частотою.
- Session-файл (data/scanner.session) — НЕ публікуйте його!
- Додайте data/ та .env до .gitignore.

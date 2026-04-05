import json
import os
import subprocess
import asyncio
import signal
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv
from groq import Groq
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

load_dotenv("/Users/oleksandr_ishcheko/ai-agent/.env")
TOKEN = os.getenv("TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DEFAULT_CHAT_ID = os.getenv("DEFAULT_CHAT_ID")
BASE_DIR = "/Users/oleksandr_ishcheko/ai-agent/files"
LAST_CHAT_ID_FILE = Path("/Users/oleksandr_ishcheko/ai-agent/.last_chat_id")
MEMORY_FILE = "/Users/oleksandr_ishcheko/ai-agent/memory.json"

AGENT_PROMPT = """Ти локальний AI-агент.
Ти виконуєш дії через tools.

Доступні інструменти:
- create_file(filename)
- read_file(filename)
- delete_file(filename)
- write_file(filename, content)
- append_file(filename, content)
- create_directory(path)
- delete_directory(path)
- list_files()
- search_files(query)
- read_logs(lines=50)
- system_info()
- current_time()
- fetch_url(url)
- git_pull()
- restart()
- remember(key, value)
- recall(key)
- list_memory()
- delete_memory(key)

Ти НЕ пояснюєш.
Ти виконуєш.

Якщо дія потрібна → ALWAYS return JSON ARRAY:
[
  {"tool": "...", "args": {...}}
]

---

ПРИКЛАДИ:

Запит: "створи файл test.txt"
Відповідь:
[
  {"tool": "create_file", "args": {"filename": "test.txt"}}
]

Запит: "прочитай файл test.txt"
Відповідь:
[
  {"tool": "read_file", "args": {"filename": "test.txt"}}
]

Запит: "видали файл test.txt"
Відповідь:
[
  {"tool": "delete_file", "args": {"filename": "test.txt"}}
]

Запит: "покажи файли"
Відповідь:
[
  {"tool": "list_files", "args": {}}
]

Запит: "онови код"
Відповідь:
[
  {"tool": "git_pull", "args": {}}
]

Запит: "перезапусти"
Відповідь:
[
  {"tool": "restart", "args": {}}
]

Запит: "запамʼятай що порт 8080"
Відповідь:
[
  {"tool": "remember", "args": {"key": "порт", "value": "8080"}}
]

Запит: "який у мене порт"
Відповідь:
[
  {"tool": "recall", "args": {"key": "порт"}}
]

Запит: "покажи памʼять"
Відповідь:
[
  {"tool": "list_memory", "args": {}}
]

Запит: "додай текст у файл"
Відповідь:
[
  {"tool": "append_file", "args": {"filename": "test.txt", "content": "новий рядок"}}
]

Запит: "знайди слово"
Відповідь:
[
  {"tool": "search_files", "args": {"query": "слово"}}
]

Запит: "покажи лог"
Відповідь:
[
  {"tool": "read_logs", "args": {"lines": 50}}
]

Запит: "стан системи"
Відповідь:
[
  {"tool": "system_info", "args": {}}
]

Запит: "котра година"
Відповідь:
[
  {"tool": "current_time", "args": {}}
]

Запит: "відкрий сайт"
Відповідь:
[
  {"tool": "fetch_url", "args": {"url": "https://example.com"}}
]

Запит: "видали з памʼяті"
Відповідь:
[
  {"tool": "delete_memory", "args": {"key": "порт"}}
]

Запит: "онови код і перезапустися"
Відповідь:
[
  {"tool": "git_pull", "args": {}},
  {"tool": "restart", "args": {}}
]

---

Якщо НЕ зрозумів → відповідай:
"Я не можу виконати цю дію"
"""

AI_PROMPT = """Ти AI асистент.
Ти відповідаєш українською.
Ти НЕ маєш доступу до інструментів.
Ти НЕ вигадуєш інструменти.
"""

MEMORY_DECIDER_PROMPT = """Ти модуль smart memory.
Оціни повідомлення користувача і виріши, чи треба це зберегти в памʼять.

Зберігати ТІЛЬКИ:
- налаштування користувача
- конфігурації
- важливі довготривалі факти

НЕ зберігати:
- випадкові одноразові прохання
- загальні питання
- тимчасовий контекст розмови

Формат відповіді:
- якщо зберігати не треба: NONE
- якщо зберігати треба: JSON обʼєкт
{
  "key": "...",
  "value": "..."
}

Без пояснень. Тільки NONE або JSON.
"""

TOOLS_HELP_TEXT = (
    "🛠 Доступні інструменти:\n\n"
    "📂 Файли:\n"
    "- create_file\n"
    "- read_file\n"
    "- delete_file\n"
    "- write_file\n"
    "- list_files\n\n"
    "- append_file\n"
    "- create_directory\n"
    "- delete_directory\n"
    "- search_files\n\n"
    "📜 Логи:\n"
    "- read_logs\n\n"
    "💻 Система:\n"
    "- system_info\n"
    "- current_time\n\n"
    "🌐 Інтернет:\n"
    "- fetch_url\n\n"
    "🔄 Система:\n"
    "- git_pull\n"
    "- restart\n\n"
    "🧠 Памʼять:\n"
    "- remember\n"
    "- recall\n"
    "- list_memory\n"
    "- delete_memory"
)

DEPENDENCY_NOTE = "Dependency note: beautifulsoup4 required."


def create_file(filename):
    filename = os.path.basename(filename)
    filepath = os.path.join(BASE_DIR, filename)
    with open(filepath, "w", encoding="utf-8"):
        pass
    return f"Створено: {filename}"


def read_file(filename):
    filename = os.path.basename(filename)
    filepath = os.path.join(BASE_DIR, filename)
    if not os.path.exists(filepath):
        return f"Не знайдено: {filename}"

    with open(filepath, "r", encoding="utf-8") as file:
        return file.read() or "(порожній файл)"


def delete_file(filename):
    filename = os.path.basename(filename)
    filepath = os.path.join(BASE_DIR, filename)
    if not os.path.exists(filepath):
        return f"Не знайдено: {filename}"

    os.remove(filepath)
    return f"Видалено: {filename}"


def write_file(filename, content):
    filename = os.path.basename(filename)
    filepath = os.path.join(BASE_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as file:
        file.write(content if content is not None else "")
    return f"Записано: {filename}"


def append_file(filename, content):
    filename = os.path.basename(filename)
    path = os.path.join(BASE_DIR, filename)
    with open(path, "a", encoding="utf-8") as file:
        file.write((content if content is not None else "") + "\n")
    return f"➕ Додано в файл: {filename}"


def create_directory(path):
    path = os.path.basename(path)
    full_path = os.path.join(BASE_DIR, path)
    os.makedirs(full_path, exist_ok=True)
    return f"📁 Створено папку: {path}"


def delete_directory(path):
    import shutil

    path = os.path.basename(path)
    full_path = os.path.join(BASE_DIR, path)
    shutil.rmtree(full_path, ignore_errors=True)
    return f"🗑 Видалено папку: {path}"


def list_files():
    try:
        files = sorted(
            name for name in os.listdir(BASE_DIR)
            if os.path.isfile(os.path.join(BASE_DIR, name))
        )
    except Exception as error:
        return f"Помилка list_files: {error}"

    if not files:
        return "(файлів немає)"
    return "\n".join(files)


def search_files(query):
    results = []
    for root, _, files in os.walk(BASE_DIR):
        for file in files:
            path = os.path.join(root, file)
            try:
                with open(path, "r", encoding="utf-8") as opened_file:
                    if query in opened_file.read():
                        results.append(file)
            except Exception:
                continue
    return "\n".join(results) if results else "Нічого не знайдено"


def read_logs(lines=50):
    try:
        with open("/Users/oleksandr_ishcheko/agent.log", "r", encoding="utf-8") as file:
            return "".join(file.readlines()[-lines:])
    except Exception:
        return "❌ Лог недоступний"


def system_info():
    import psutil
    return (
        f"CPU: {psutil.cpu_percent()}%\n"
        f"RAM: {psutil.virtual_memory().percent}%\n"
        f"Disk: {psutil.disk_usage('/').percent}%"
    )


def current_time():
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def fetch_url(url):
    # Dependency note: beautifulsoup4 required
    import requests
    from bs4 import BeautifulSoup

    try:
        r = requests.get(url, timeout=5)
        soup = BeautifulSoup(r.text, "html.parser")

        text = soup.get_text(separator="\n")
        text = "\n".join(text.splitlines())

        return text[:1000]

    except Exception as e:
        return f"❌ Помилка: {str(e)}"


def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return {}
    with open(MEMORY_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def save_memory(data):
    with open(MEMORY_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def remember(key, value):
    data = load_memory()
    data[key] = value
    save_memory(data)
    return f"💾 Збережено: {key} = {value}"


def recall(key):
    data = load_memory()
    return data.get(key, "❌ Немає такого запису")


def list_memory():
    data = load_memory()
    if not data:
        return "Памʼять порожня"
    return "\n".join([f"{key}: {value}" for key, value in data.items()])


def delete_memory(key):
    data = load_memory()
    if key in data:
        del data[key]
        save_memory(data)
        return f"🗑 Видалено: {key}"
    return "❌ Ключ не знайдено"




def git_pull():
    try:
        output = subprocess.check_output(
            "cd /Users/oleksandr_ishcheko/ai-agent && git pull",
            shell=True
        ).decode()
        return output
    except Exception as e:
        return f"Помилка git pull: {e}"


def restart_agent():
    import threading
    import os
    import time

    def restart():
        time.sleep(2)
        os.system("launchctl kickstart -k gui/$(id -u)/com.bot.agent")

    threading.Thread(target=restart).start()

    return "♻️ Перезапуск агента..."


def save_last_chat_id(chat_id):
    try:
        LAST_CHAT_ID_FILE.write_text(str(chat_id), encoding="utf-8")
    except Exception:
        pass


def load_last_chat_id():
    try:
        if LAST_CHAT_ID_FILE.exists():
            return int(LAST_CHAT_ID_FILE.read_text(encoding="utf-8").strip())
    except Exception:
        return None
    return None


async def notify_status(application, text):
    chat_ids = []

    last_chat_id = load_last_chat_id()
    if last_chat_id:
        chat_ids.append(last_chat_id)

    if DEFAULT_CHAT_ID:
        try:
            default_chat_id = int(DEFAULT_CHAT_ID)
            if default_chat_id not in chat_ids:
                chat_ids.append(default_chat_id)
        except ValueError:
            pass

    if not chat_ids:
        return

    for chat_id in chat_ids:
        for attempt in range(3):
            try:
                await application.bot.send_message(chat_id=chat_id, text=text)
                return
            except Exception as error:
                print(
                    f"Не вдалося надіслати статус у chat_id={chat_id}, "
                    f"спроба {attempt + 1}/3: {error}"
                )
                await asyncio.sleep(1)


async def on_startup(application):
    await notify_status(application, "🚀 Агент запущений")


def notify_stop():
    chat_id = load_last_chat_id()
    if not chat_id and DEFAULT_CHAT_ID:
        try:
            chat_id = int(DEFAULT_CHAT_ID)
        except ValueError:
            return
    if not chat_id:
        return

    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": "🔴 Агент зупинено"
            },
            timeout=5
        )
    except Exception:
        pass


def handle_exit(signum, frame):
    notify_stop()
    sys.exit(0)

def ask_ai(prompt, mode="agent"):
    if not GROQ_API_KEY:
        return "GROQ_API_KEY не встановлено"

    if mode == "agent":
        system_prompt = AGENT_PROMPT
    elif mode == "memory":
        system_prompt = MEMORY_DECIDER_PROMPT
    else:
        system_prompt = AI_PROMPT

    client = Groq(api_key=GROQ_API_KEY)
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
    )
    return response.choices[0].message.content or ""


def plan_task(prompt):
    if not GROQ_API_KEY:
        return "GROQ_API_KEY не встановлено"

    client = Groq(api_key=GROQ_API_KEY)
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": """
Ти планувальник задач.

Твоя задача:
розбити запит користувача на кроки.

Поверни JSON список:

[
  {"step": "...", "tool": "...", "args": {...}}
]

НЕ пояснюй.
"""
            },
            {"role": "user", "content": prompt}
        ]
    )

    return response.choices[0].message.content


def fix_plan(original_prompt, error_message):
    if not GROQ_API_KEY:
        return "GROQ_API_KEY не встановлено"

    client = Groq(api_key=GROQ_API_KEY)
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": f"""
Ти виправляєш план задачі.

Помилка:
{error_message}

Ти МОЖЕШ використовувати ТІЛЬКИ ці інструменти:

- create_file
- read_file
- delete_file
- write_file
- append_file
- list_files
- git_pull
- restart
- remember
- recall
- list_memory
- delete_memory

Поверни правильний JSON список.
НЕ використовуй touch, echo або bash.
"""
            },
            {"role": "user", "content": original_prompt}
        ]
    )

    return response.choices[0].message.content


VALID_TOOLS = {
    "create_file",
    "read_file",
    "delete_file",
    "write_file",
    "append_file",
    "list_files",
    "git_pull",
    "restart",
    "remember",
    "recall",
    "list_memory",
    "delete_memory",
}


def validate_plan(plan_json):
    try:
        data = json.loads(plan_json)

        if not isinstance(data, list):
            return "❌ Невірний формат плану"

        for step in data:
            tool = step.get("tool")

            if tool not in VALID_TOOLS:
                return f"❌ Невідомий інструмент у плані: {tool}"

        return data

    except Exception as e:
        return f"❌ Помилка плану: {str(e)}"


def extract_memory_candidate(text):
    response = ask_ai(text, mode="memory").strip()

    if response == "NONE":
        return None

    try:
        data = json.loads(response)
    except json.JSONDecodeError:
        return None

    if not isinstance(data, dict):
        return None

    key = str(data.get("key", "")).strip()
    value = str(data.get("value", "")).strip()

    if not key or not value:
        return None

    return key, value


def auto_remember_from_text(text):
    memory_pair = extract_memory_candidate(text)
    if memory_pair is None:
        return None

    key, value = memory_pair
    return remember(key, value)


def try_execute_tool(response):
    try:
        response = response.strip()

        if not response.startswith("["):
            return None

        data = json.loads(response)

        if not isinstance(data, list):
            return None

        results = []
        git_result = ""

        for item in data:
            tool = item.get("tool")
            args = item.get("args", {})

            if tool == "create_file":
                results.append(create_file(args.get("filename")))

            elif tool == "read_file":
                results.append(read_file(args.get("filename")))

            elif tool == "delete_file":
                results.append(delete_file(args.get("filename")))

            elif tool == "write_file":
                results.append(write_file(
                    args.get("filename"),
                    args.get("content", "")
                ))

            elif tool == "append_file":
                results.append(append_file(
                    args.get("filename"),
                    args.get("content", "")
                ))

            elif tool == "create_directory":
                results.append(create_directory(args.get("path")))

            elif tool == "delete_directory":
                results.append(delete_directory(args.get("path")))

            elif tool == "list_files":
                results.append(list_files())

            elif tool == "search_files":
                results.append(search_files(args.get("query", "")))

            elif tool == "read_logs":
                results.append(read_logs(args.get("lines", 50)))

            elif tool == "system_info":
                results.append(system_info())

            elif tool == "current_time":
                results.append(current_time())

            elif tool == "fetch_url":
                results.append(fetch_url(args.get("url", "")))

            elif tool == "git_pull":
                git_result = git_pull()
                results.append(git_result)

            elif tool == "restart":
                if "Already up to date" not in git_result:
                    results.append(restart_agent())

            elif tool == "remember":
                results.append(remember(args.get("key"), args.get("value")))

            elif tool == "recall":
                results.append(recall(args.get("key")))

            elif tool == "list_memory":
                results.append(list_memory())

            elif tool == "delete_memory":
                results.append(delete_memory(args.get("key")))

        return "\n".join(results)

    except Exception as e:
        return f"❌ Executor error: {str(e)}"


async def handle(update, context):
    text = update.message.text or ""
    save_last_chat_id(update.effective_chat.id)
    auto_remember_from_text(text)

    if text.lower() in ["інструменти", "tools", "що ти вмієш"]:
        await update.message.reply_text(TOOLS_HELP_TEXT)
        return

    ai_response = ask_ai(text, mode="agent")
    print("MODE: AGENT")
    print("AI RESPONSE:", ai_response)
    result = try_execute_tool(ai_response)
    print("RESULT:", result)

    if result is not None:
        await update.message.reply_text(result)
        return

    await update.message.reply_text("Я не можу виконати цю дію")


async def ai_handler(update, context):
    prompt = " ".join(context.args)

    if not prompt:
        await update.message.reply_text("Введи запит після /ai")
        return

    auto_remember_from_text(prompt)
    response = ask_ai(prompt, mode="chat")
    await update.message.reply_text(response)


async def tools_handler(update, context):
    await update.message.reply_text(TOOLS_HELP_TEXT)


async def status_handler(update, context):
    await update.message.reply_text("Агент активний")


async def plan_handler(update, context):
    text = " ".join(context.args)

    if not text:
        await update.message.reply_text("Введи задачу")
        return

    raw_plan = plan_task(text)
    validated = validate_plan(raw_plan)

    if isinstance(validated, str):
        fixed_plan = fix_plan(text, validated)
        validated = validate_plan(fixed_plan)

        if isinstance(validated, str):
            await update.message.reply_text("❌ Не вдалося побудувати план")
            return

    await update.message.reply_text(
        json.dumps(validated, indent=2, ensure_ascii=False)
    )


def main():
    if not TOKEN:
        raise RuntimeError("TOKEN не встановлено у файлі .env")

    app = (
        ApplicationBuilder()
        .token(TOKEN)
        .post_init(on_startup)
        .build()
    )
    app.add_handler(CommandHandler("ai", ai_handler))
    app.add_handler(CommandHandler("plan", plan_handler))
    app.add_handler(CommandHandler("plans", plan_handler))
    app.add_handler(CommandHandler("tools", tools_handler))
    app.add_handler(CommandHandler("status", status_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    signal.signal(signal.SIGTERM, handle_exit)
    signal.signal(signal.SIGINT, handle_exit)

    print("🚀 BOT STARTED")
    app.run_polling()


if __name__ == "__main__":
    main()

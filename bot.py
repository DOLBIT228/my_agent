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
TASKS_FILE = "/Users/oleksandr_ishcheko/ai-agent/tasks.json"
tasks = {}

TOOL_SIGNATURES = [
    "create_file(filename)",
    "read_file(filename)",
    "delete_file(filename)",
    "write_file(filename, content)",
    "append_file(filename, content)",
    "create_directory(path)",
    "delete_directory(path)",
    "list_files()",
    "search_files(query)",
    "read_logs(lines=50)",
    "system_info()",
    "current_time()",
    "fetch_url(url)",
    "git_pull()",
    "restart()",
    "remember(key, value)",
    "recall(key)",
    "list_memory()",
    "delete_memory(key)",
]

AGENT_PROMPT = f"""Ти універсальний AI агент.

Ти можеш:
1. Відповідати на питання
2. Виконувати дії через інструменти
3. Робити кілька кроків

---

ДОСТУПНІ ІНСТРУМЕНТИ:
{chr(10).join(f"- {tool}" for tool in TOOL_SIGNATURES)}

---

ПРАВИЛА:

1. Якщо потрібно просто відповісти → текст

2. Якщо потрібно діяти → поверни JSON:
[
  {{"tool": "...", "args": {{...}}}}
]

3. Якщо кілька кроків → список

4. НЕ вигадуй інструменти

5. Якщо не знаєш → відповідай текстом
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


def load_tasks():
    if not os.path.exists(TASKS_FILE):
        return {}

    try:
        with open(TASKS_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        return {}

    return data if isinstance(data, dict) else {}


def save_tasks():
    with open(TASKS_FILE, "w", encoding="utf-8") as file:
        json.dump(tasks, file, ensure_ascii=False, indent=2)


def create_task(task_text):
    from uuid import uuid4

    task_id = str(uuid4())
    tasks[task_id] = {
        "id": task_id,
        "status": "pending",
        "steps": [],
        "result": "",
    }
    save_tasks()
    return task_id


def run_task(task_id, task_text):
    task = tasks.get(task_id)
    if task is None:
        return None

    task["status"] = "running"
    save_tasks()

    try:
        ai_response = ask_ai(task_text, mode="agent")
        result = try_execute_tool(ai_response)

        if result is not None:
            task["steps"] = [line for line in result.splitlines() if line.strip()]
            task["result"] = result
        else:
            task["result"] = ai_response

        task["status"] = "done"
    except Exception as error:
        task["status"] = "error"
        task["result"] = f"❌ Помилка виконання задачі: {error}"

    save_tasks()
    return task["result"]


def get_task_status(task_id):
    task = tasks.get(task_id)
    if task is None:
        return "❌ Task not found"

    result = task.get("result", "")
    if not result:
        result = "(поки без результату)"

    return f"status: {task.get('status', 'unknown')}\nresult: {result}"



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


def execute_tool(tool, args):
    try:
        if tool == "create_file":
            return create_file(args.get("filename"))

        if tool == "read_file":
            return read_file(args.get("filename"))

        if tool == "delete_file":
            return delete_file(args.get("filename"))

        if tool == "write_file":
            return write_file(args.get("filename"), args.get("content", ""))

        if tool == "append_file":
            return append_file(args.get("filename"), args.get("content", ""))

        if tool == "create_directory":
            return create_directory(args.get("path"))

        if tool == "delete_directory":
            return delete_directory(args.get("path"))

        if tool == "list_files":
            return list_files()

        if tool == "search_files":
            return search_files(args.get("query", ""))

        if tool == "read_logs":
            return read_logs(args.get("lines", 50))

        if tool == "system_info":
            return system_info()

        if tool == "current_time":
            return current_time()

        if tool == "fetch_url":
            return fetch_url(args.get("url", ""))

        if tool == "git_pull":
            return git_pull()

        if tool == "restart":
            return restart_agent()

        if tool == "remember":
            return remember(args.get("key"), args.get("value"))

        if tool == "recall":
            return recall(args.get("key"))

        if tool == "list_memory":
            return list_memory()

        if tool == "delete_memory":
            return delete_memory(args.get("key"))

        return f"❌ Невідомий інструмент: {tool}"
    except Exception as error:
        return f"❌ Помилка інструмента {tool}: {error}"


def try_execute_tool(response):
    response = response.strip()
    if not response.startswith("["):
        return None

    try:
        data = json.loads(response)
    except json.JSONDecodeError as error:
        return f"❌ Некоректний JSON від AI: {error}"

    if not isinstance(data, list):
        return "❌ Очікувався список кроків у форматі JSON-масиву."

    results = []
    for index, step in enumerate(data, start=1):
        if not isinstance(step, dict):
            results.append(f"Крок {index}: ❌ Некоректний крок (очікувався об'єкт).")
            continue

        tool = step.get("tool")
        args = step.get("args", {})
        if not isinstance(args, dict):
            results.append(f"Крок {index}: ❌ Некоректні args (очікувався об'єкт).")
            continue

        result = execute_tool(tool, args)
        results.append(f"Крок {index} ({tool}): {result}")

    return "\n".join(results) if results else "✅ Немає кроків для виконання."


async def handle(update, context):
    text = update.message.text or ""
    save_last_chat_id(update.effective_chat.id)
    auto_remember_from_text(text)

    ai_response = ask_ai(text, mode="agent")
    result = try_execute_tool(ai_response)

    if result is not None:
        await update.message.reply_text(result)
        return

    await update.message.reply_text(ai_response)


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


async def task_handler(update, context):
    task_text = " ".join(context.args).strip()
    if not task_text:
        await update.message.reply_text("Введи опис задачі після /task")
        return

    task_id = create_task(task_text)
    run_task(task_id, task_text)
    await update.message.reply_text(f"✅ Задача виконана\nID: {task_id}")


async def task_status_handler(update, context):
    task_id = " ".join(context.args).strip()
    if not task_id:
        await update.message.reply_text("Введи ID після /task_status")
        return

    await update.message.reply_text(get_task_status(task_id))


def main():
    if not TOKEN:
        raise RuntimeError("TOKEN не встановлено у файлі .env")

    global tasks
    tasks = load_tasks()

    app = (
        ApplicationBuilder()
        .token(TOKEN)
        .post_init(on_startup)
        .build()
    )
    app.add_handler(CommandHandler("ai", ai_handler))
    app.add_handler(CommandHandler("tools", tools_handler))
    app.add_handler(CommandHandler("status", status_handler))
    app.add_handler(CommandHandler("task", task_handler))
    app.add_handler(CommandHandler("task_status", task_status_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    signal.signal(signal.SIGTERM, handle_exit)
    signal.signal(signal.SIGINT, handle_exit)

    print("🚀 BOT STARTED")
    app.run_polling()


if __name__ == "__main__":
    main()

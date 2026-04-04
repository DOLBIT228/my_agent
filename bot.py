import json
import os
import subprocess
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq
from telegram.ext import ApplicationBuilder, MessageHandler, filters

load_dotenv("/Users/oleksandr_ishcheko/ai-agent/.env")
TOKEN = os.getenv("TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
BASE_DIR = "/Users/oleksandr_ishcheko/ai-agent/files"
LAST_CHAT_ID_FILE = Path("/Users/oleksandr_ishcheko/ai-agent/.last_chat_id")

SYSTEM_PROMPT = """Ти локальний AI-агент.
Відповідай українською мовою.
Будь коротким, чітким і практичним.
Якщо потрібно виконати дію — використовуй tools."""


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




def git_pull():
    try:
        output = subprocess.check_output(
            "cd /Users/oleksandr_ishcheko/ai-agent && git pull",
            shell=True
        ).decode()
        if "Already up to date" in output:
            return "Оновлень немає"
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
    chat_id = load_last_chat_id()
    if not chat_id:
        return
    try:
        await application.bot.send_message(chat_id=chat_id, text=text)
    except Exception:
        pass


async def on_startup(application):
    await notify_status(application, "✅ Бот запущено. Я готовий до роботи.")


async def on_shutdown(application):
    await notify_status(application, "🛑 Бот зупиняється.")

def ask_ai(prompt):
    if not GROQ_API_KEY:
        return "GROQ_API_KEY не встановлено"

    client = Groq(api_key=GROQ_API_KEY)
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
    )
    return response.choices[0].message.content or ""


def try_execute_tool(response):
    try:
        def extract_json_blocks(text):
            blocks = []
            depth = 0
            start = None

            for index, char in enumerate(text):
                if char == "{":
                    if depth == 0:
                        start = index
                    depth += 1
                elif char == "}":
                    if depth > 0:
                        depth -= 1
                        if depth == 0 and start is not None:
                            blocks.append(text[start:index + 1])
                            start = None

            return blocks

        blocks = extract_json_blocks(response)
        results = []
        git_result = None

        for block in blocks:
            try:
                data = json.loads(block)
            except Exception:
                continue

            tool = data.get("tool")
            args = data.get("args", {})

            if tool == "create_file":
                results.append(create_file(args.get("filename")))
            elif tool == "read_file":
                results.append(read_file(args.get("filename")))
            elif tool == "delete_file":
                results.append(delete_file(args.get("filename")))
            elif tool == "git_pull":
                git_result = git_pull()
                results.append(git_result)
            elif tool == "restart":
                if git_result and "Оновлень немає" in git_result:
                    continue
                results.append("ℹ️ Отримано команду на перезапуск. Перезапускаюся...")
                results.append(restart_agent())

        if results:
            return "\n".join(results)
        return None

    except:
        return None


async def handle(update, context):
    text = update.message.text or ""
    save_last_chat_id(update.effective_chat.id)
    parts = text.split()

    if len(parts) >= 2:
        command, filename = parts[0], parts[1]

        if command == "create_file":
            result = create_file(filename)
            await update.message.reply_text(result)
            return
        if command == "read_file":
            result = read_file(filename)
            await update.message.reply_text(result)
            return
        if command == "delete_file":
            result = delete_file(filename)
            await update.message.reply_text(result)
            return

    ai_response = ask_ai(text)
    print("AI:", ai_response)
    result = try_execute_tool(ai_response)
    print("RESULT:", result)

    if result is not None:
        await update.message.reply_text(result)
    else:
        await update.message.reply_text(ai_response)


def main():
    if not TOKEN:
        raise RuntimeError("TOKEN не встановлено у файлі .env")

    app = (
        ApplicationBuilder()
        .token(TOKEN)
        .post_init(on_startup)
        .post_shutdown(on_shutdown)
        .build()
    )
    app.add_handler(MessageHandler(filters.TEXT, handle))

    print("🚀 BOT STARTED")
    app.run_polling()


if __name__ == "__main__":
    main()

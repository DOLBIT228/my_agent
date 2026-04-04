import json
import os
import subprocess

from dotenv import load_dotenv
from groq import Groq
from telegram.ext import ApplicationBuilder, MessageHandler, filters

load_dotenv("/Users/oleksandr_ishcheko/ai-agent/.env")
TOKEN = os.getenv("TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
BASE_DIR = "/Users/oleksandr_ishcheko/ai-agent/files"

SYSTEM_PROMPT = """You are an AI agent.
You can use tools:

create_file(filename)
read_file(filename)
delete_file(filename)
git_pull()
restart()

If action needed -> return JSON:

{\"tool\": \"...\", \"args\": {...}}

Otherwise return text.

If user asks to update code (for example: "онови код", "update project", "pull latest changes"), call tool git_pull.
If user asks to restart (for example: "перезапусти", "restart agent", "reload system"), call tool restart.

DO NOT explain tools."""


def create_file(filename):
    filename = os.path.basename(filename)
    filepath = os.path.join(BASE_DIR, filename)
    with open(filepath, "w", encoding="utf-8"):
        pass
    return f"Created: {filename}"


def read_file(filename):
    filename = os.path.basename(filename)
    filepath = os.path.join(BASE_DIR, filename)
    if not os.path.exists(filepath):
        return f"Not found: {filename}"

    with open(filepath, "r", encoding="utf-8") as file:
        return file.read() or "(empty file)"


def delete_file(filename):
    filename = os.path.basename(filename)
    filepath = os.path.join(BASE_DIR, filename)
    if not os.path.exists(filepath):
        return f"Not found: {filename}"

    os.remove(filepath)
    return f"Deleted: {filename}"




def git_pull():
    try:
        return subprocess.check_output(
            "cd /Users/oleksandr_ishcheko/ai-agent && git pull",
            shell=True
        ).decode()
    except Exception as e:
        return str(e)


def restart_agent():
    import threading
    import os
    import time

    def restart():
        time.sleep(2)
        os.system("launchctl kickstart -k gui/$(id -u)/com.bot.agent")

    threading.Thread(target=restart).start()

    return "♻️ Restarting agent..."

def ask_ai(prompt):
    if not GROQ_API_KEY:
        return "GROQ_API_KEY is not set"

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
        data = json.loads(response)

        tool = data.get("tool")
        args = data.get("args", {})

        if tool == "create_file":
            return create_file(args.get("filename"))

        if tool == "read_file":
            return read_file(args.get("filename"))

        if tool == "delete_file":
            return delete_file(args.get("filename"))

        if tool == "git_pull":
            return git_pull()

        if tool == "restart":
            return restart_agent()

    except:
        return None

    return None


async def handle(update, context):
    text = update.message.text or ""
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
    result = try_execute_tool(ai_response)

    if result is not None:
        await update.message.reply_text(result)
    else:
        await update.message.reply_text(ai_response)


def main():
    if not TOKEN:
        raise RuntimeError("TOKEN is not set in the .env file")

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT, handle))

    print("🚀 BOT STARTED")
    app.run_polling()


if __name__ == "__main__":
    main()

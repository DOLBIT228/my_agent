import json
import os

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

If action needed -> return JSON:

{\"tool\": \"...\", \"args\": {...}}

Otherwise return text.

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

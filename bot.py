import os

from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, MessageHandler, filters

load_dotenv("/Users/oleksandr_ishcheko/ai-agent/.env")
TOKEN = os.getenv("TOKEN")
BASE_DIR = "/Users/oleksandr_ishcheko/ai-agent/files"


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

    await update.message.reply_text("OK")


def main():
    if not TOKEN:
        raise RuntimeError("TOKEN is not set in the .env file")

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT, handle))

    print("🚀 BOT STARTED")
    app.run_polling()


if __name__ == "__main__":
    main()

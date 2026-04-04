import os

from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, MessageHandler, filters

load_dotenv("/Users/oleksandr_ishcheko/ai-agent/.env")
TOKEN = os.getenv("TOKEN")


async def handle(update, context):
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

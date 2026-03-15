"""Telegram bot entrypoint."""
from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from agent.assistant import Assistant
from agent.config import settings
from agent.executor import Executor
from agent.memory import Memory
from agent.planner import Planner
from database.db import Database
from integrations.google_calendar import GoogleCalendarService
from llm.ollama_client import OllamaClient
from scheduler.reminders import ReminderScheduler
from tools.calendar_tool import CalendarTool
from tools.notes_tool import NotesTool
from tools.python_exec_tool import PythonExecTool
from tools.reminder_tool import ReminderTool
from tools.search_tool import SearchTool
from tools.task_tool import TaskTool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def build_assistant() -> Assistant:
    db = Database(settings.DATABASE_PATH)
    scheduler = ReminderScheduler()
    scheduler.start()

    task_tool = TaskTool(db)
    notes_tool = NotesTool(db)
    reminder_tool = ReminderTool(db, scheduler)
    search_tool = SearchTool()
    python_tool = PythonExecTool()

    calendar_tool = None
    if settings.GOOGLE_CALENDAR_ENABLED:
        calendar_tool = CalendarTool(GoogleCalendarService())

    planner = Planner()
    executor = Executor(task_tool, notes_tool, reminder_tool, calendar_tool, search_tool, python_tool)
    memory = Memory(db, max_messages=settings.MAX_CONTEXT_MESSAGES)

    ollama = OllamaClient(settings.OLLAMA_BASE_URL, settings.MODEL_NAME)
    return Assistant(planner, executor, memory, ollama)


ASSISTANT = build_assistant()


async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "👋 Вітаю! Персональний AI-помічник вже онлайн.\n"
        "Спробуйте: 'додай задачу: підготувати презентацію для інвестора' або "
        "'нагадай через 30 хвилин зателефонувати Олексію'."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return

    chat_id = str(update.effective_chat.id)

    async def send_callback(target_chat_id: str, text: str) -> None:
        await context.bot.send_message(chat_id=int(target_chat_id), text=text)

    status_message = await update.message.reply_text("⏳ Працюю над вашою відповіддю...")
    response = await ASSISTANT.handle_message(chat_id, update.message.text, send_callback)
    await status_message.edit_text(response)


def main() -> None:
    if not settings.TELEGRAM_TOKEN:
        raise RuntimeError("Відсутній TELEGRAM_TOKEN. Додайте його у змінні середовища.")

    app = Application.builder().token(settings.TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Запускаю Telegram-бота...")
    app.run_polling()


if __name__ == "__main__":
    main()

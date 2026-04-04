import requests
import subprocess
import os
import json
import sys
import time
import socket
import asyncio

from groq import Groq
from telegram import Update, BotCommand
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    filters,
    ContextTypes
)

# ---------- CONFIG ----------

from dotenv import load_dotenv
load_dotenv("/Users/oleksandr_ishcheko/ai-agent/.env")

TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

BASE_DIR = "/Users/oleksandr_ishcheko/ai-agent/files"
PROJECT_DIR = "/Users/oleksandr_ishcheko/ai-agent"
LOCK_FILE = "/tmp/ai_agent.lock"

os.makedirs(BASE_DIR, exist_ok=True)

client = Groq(api_key=GROQ_API_KEY)

# ---------- STATE ----------

git_setup_step = {}

# ---------- INTERNET ----------

def wait_for_internet():
    while True:
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            return
        except:
            time.sleep(2)

# ---------- LOCK ----------

def acquire_lock():
    if os.path.exists(LOCK_FILE):
        sys.exit(1)
    with open(LOCK_FILE, "w") as f:
        f.write(str(os.getpid()))

def release_lock():
    if os.path.exists(LOCK_FILE):
        os.remove(LOCK_FILE)

# ---------- NOTIFY ----------

def notify_start():
    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": "🚀 Агент запущений"},
            timeout=5
        )
    except:
        pass

# ---------- TOOLS ----------

def safe_path(filename):
    return os.path.join(BASE_DIR, os.path.basename(filename))

def create_file(filename):
    path = safe_path(filename)
    open(path, "w").close()
    return f"📄 Created: {path}"

def read_file(filename):
    path = safe_path(filename)
    if not os.path.exists(path):
        return "❌ Файл не існує"
    with open(path, "r") as f:
        content = f.read()
        return content if content else "📭 Файл порожній"

def delete_file(filename):
    path = safe_path(filename)
    if not os.path.exists(path):
        return "❌ Файл не знайдено"
    os.remove(path)
    return f"🗑 Deleted: {path}"

def run_command(cmd):
    try:
        return subprocess.check_output(cmd, shell=True).decode()
    except Exception as e:
        return str(e)

TOOLS = {
    "create_file": create_file,
    "read_file": read_file,
    "delete_file": delete_file,
    "run_command": run_command,
}

# ---------- NORMALIZE ----------

def normalize(tool, args):
    if not isinstance(args, dict):
        args = {}

    tool_map = {
        "rm": "delete_file",
        "ls": "run_command"
    }

    tool = tool_map.get(tool, tool)

    filename = args.get("filename") or args.get("file") or args.get("path")
    cmd = args.get("cmd") or args.get("command")

    if tool in ["create_file", "read_file", "delete_file"]:
        return tool, {"filename": filename}

    if tool == "run_command":
        return tool, {"cmd": cmd or "ls"}

    return tool, args

# ---------- AI ----------

SYSTEM_PROMPT = """
Використовуй tools:
create_file, read_file, delete_file, run_command

Відповідай JSON:
{"tool": "...", "args": {...}}
"""

def ask_ai(prompt):
    chat = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
    )
    return chat.choices[0].message.content

# ---------- EXEC ----------

def execute_ai(text):
    try:
        data = json.loads(text)

        tool, args = normalize(
            data.get("tool"),
            data.get("args", {})
        )

        if tool not in TOOLS:
            return f"❌ Інструмент '{tool}' не існує"

        return TOOLS[tool](**args)

    except:
        return None

# ---------- GIT ----------

def git_pull():
    try:
        return subprocess.check_output(
            f"cd {PROJECT_DIR} && git pull",
            shell=True
        ).decode()
    except Exception as e:
        return str(e)

def git_clone(repo):
    try:
        return subprocess.check_output(
            f"cd {PROJECT_DIR} && git clone {repo} .",
            shell=True
        ).decode()
    except Exception as e:
        return str(e)


def has_updates():
    try:
        local_head = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=PROJECT_DIR,
            stderr=subprocess.DEVNULL,
        ).decode().strip()
        remote_head = subprocess.check_output(
            ["git", "rev-parse", "origin/main"],
            cwd=PROJECT_DIR,
            stderr=subprocess.DEVNULL,
        ).decode().strip()
        return local_head != remote_head
    except Exception:
        return False


async def auto_update_loop(app):
    while True:
        try:
            subprocess.run(
                ["git", "fetch"],
                cwd=PROJECT_DIR,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )

            if has_updates():
                subprocess.run(
                    ["git", "pull"],
                    cwd=PROJECT_DIR,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=True,
                )
                print("🔄 Update applied. Restarting bot...")
                subprocess.run(
                    [
                        "launchctl",
                        "kickstart",
                        "-k",
                        f"gui/{os.getuid()}/com.bot.agent",
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
        except Exception:
            pass

        await asyncio.sleep(30)

# ---------- COMMANDS ----------

async def git_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    git_setup_step[update.effective_user.id] = "repo"
    await update.message.reply_text("🔗 Встав URL репозиторію")

async def update_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⬇️ Оновлюю...")

    result = git_pull()
    await update.message.reply_text(result[:4000])

    await update.message.reply_text("♻️ Перезапуск...")

    os.system("launchctl kickstart -k gui/$(id -u)/com.bot.agent")

async def tools_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🧰 create_file\nread_file\ndelete_file\nrun_command"
    )

# ---------- HANDLER ----------

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    # ---- GIT SETUP FLOW ----
    if user_id in git_setup_step:
        if git_setup_step[user_id] == "repo":
            result = git_clone(text)
            git_setup_step.pop(user_id)

            await update.message.reply_text("✅ Репозиторій підключено")
            await update.message.reply_text(result[:4000])
            return

    # ---- NORMAL ----

    await update.message.reply_text("⚡ Думаю...")

    ai = ask_ai(text)
    result = execute_ai(ai)

    if result is not None:
        await update.message.reply_text(result)
    else:
        await update.message.reply_text(ai)

# ---------- MAIN ----------

async def set_commands(app):
    await app.bot.set_my_commands([
        BotCommand("tools", "Інструменти"),
        BotCommand("git", "Підключити GitHub"),
        BotCommand("update", "Оновити код"),
    ])


async def on_startup(app):
    await set_commands(app)
    app.create_task(auto_update_loop(app))

def main():
    acquire_lock()

    try:
        wait_for_internet()
        notify_start()

        app = ApplicationBuilder().token(TOKEN).post_init(on_startup).build()

        app.add_handler(CommandHandler("tools", tools_cmd))
        app.add_handler(CommandHandler("git", git_cmd))
        app.add_handler(CommandHandler("update", update_cmd))

        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

        print("🚀 Agent started")

        app.run_polling()

    finally:
        release_lock()

if __name__ == "__main__":
    main()

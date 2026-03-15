# Personal AI Business Assistant

A production-style, local-first **Python** assistant that runs as a Telegram bot and helps with:

- meeting scheduling
- reminders
- Google Calendar operations
- task and notes management
- internet search
- local LLM reasoning via **Ollama**
- optional cloud fallback via **OpenAI API**

## Architecture

```text
Telegram message
  -> Planner
  -> Tool Router / Executor
  -> Tool execution (calendar, reminders, tasks, notes, search, python)
  -> LLM reasoning (Ollama primary, OpenAI fallback optional)
  -> Telegram response
```

Core modules:

- `agent/assistant.py`: orchestration logic
- `agent/planner.py`: intent planning
- `agent/executor.py`: tool execution
- `agent/memory.py`: conversation memory
- `bot/telegram_bot.py`: Telegram runtime
- `integrations/google_calendar.py`: Google Calendar API
- `llm/ollama_client.py`: local LLM client
- `integrations/openai_fallback.py`: optional cloud fallback
- `scheduler/reminders.py`: APScheduler integration
- `database/db.py`: SQLite persistence

## Repository Structure

```text
ai-business-assistant/
├ bot/
│   └ telegram_bot.py
├ agent/
│   ├ assistant.py
│   ├ planner.py
│   ├ memory.py
│   ├ executor.py
│   └ config.py
├ tools/
│   ├ calendar_tool.py
│   ├ reminder_tool.py
│   ├ task_tool.py
│   ├ notes_tool.py
│   ├ search_tool.py
│   └ python_exec_tool.py
├ integrations/
│   ├ google_calendar.py
│   └ openai_fallback.py
├ database/
│   └ db.py
├ llm/
│   └ ollama_client.py
├ scheduler/
│   └ reminders.py
├ prompts/
│   └ system_prompt.txt
├ admin/
│   └ streamlit_app.py
├ requirements.txt
├ start.sh
└ README.md
```

## Setup

### 1) Install Ollama

- macOS/Linux: follow https://ollama.com/download
- verify:

```bash
ollama --version
```

### 2) Pull a local model

Supported examples:

```bash
ollama pull phi3:mini
ollama pull gemma:2b
ollama pull mistral:7b
ollama pull qwen2.5:7b
```

### 3) Create Telegram bot token

1. Open Telegram and message `@BotFather`
2. Run `/newbot`
3. Copy the bot token

### 4) Google Calendar credentials (optional)

1. Create a Google Cloud project
2. Enable **Google Calendar API**
3. Create OAuth desktop credentials
4. Download as `credentials.json` into project root (`ai-business-assistant/`)
5. On first run, browser auth flow creates `token.json`

### 5) Install Python dependencies

```bash
cd ai-business-assistant
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 6) Configure environment variables

```bash
export TELEGRAM_TOKEN="your-token"
export MODEL_NAME="phi3:mini"
export MAX_CONTEXT_MESSAGES="10"
export GOOGLE_CALENDAR_ENABLED="true"
export ENABLE_OPENAI_FALLBACK="false"

# Optional OpenAI fallback
export OPENAI_API_KEY="sk-..."
export OPENAI_MODEL="gpt-4o-mini"
```

### 7) Start assistant

```bash
./start.sh
```

## Telegram Examples

- `Schedule meeting tomorrow at 14:00 with Alex`
- `Remind me in 2 hours to call the client`
- `What meetings do I have today?`
- `Add task: prepare investor presentation`
- `Remember: investor meeting idea about AI SaaS`
- `Search latest AI startup benchmarks`

## Optional Streamlit Admin Panel

```bash
source .venv/bin/activate
streamlit run admin/streamlit_app.py
```

## Notes on Production Readiness

- Modular architecture and tool separation
- SQLite-backed persistence
- Async reminder scheduling via APScheduler
- Environment-driven config for deployment portability
- Local-first inference with optional cloud fallback

## License

MIT

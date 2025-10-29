import os
import asyncio
from fastapi import FastAPI
from aiogram import Bot, Dispatcher, F, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, Message
from aiogram.filters import Command
from pydantic import BaseModel
import requests
import random

# -------------------------------
# 🔹 Токендерді оқу
# -------------------------------
BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")

# 🔍 Логқа шығару (жасырын түрде)
print("🔍 DEBUG: TG_BOT_TOKEN =", BOT_TOKEN[:5] if BOT_TOKEN else "❌ None")
print("🔍 DEBUG: OPENROUTER_API_KEY =", OPENROUTER_KEY[:5] if OPENROUTER_KEY else "❌ None")

if not BOT_TOKEN:
    raise ValueError("❌ ERROR: TG_BOT_TOKEN табылмады! Render → Environment → TG_BOT_TOKEN орнатыңыз.")

# -------------------------------
# 🔹 Инициализация
# -------------------------------
bot = Bot(token=str(BOT_TOKEN))
dp = Dispatcher()
app = FastAPI()

# -------------------------------
# 🔹 Ойын логикасы
# -------------------------------
GAMES = {}

class Game:
    def __init__(self, chat_id):
        self.chat_id = chat_id
        self.players = []
        self.started = False
        self.winner = None

    def add_player(self, user_id):
        if user_id not in self.players:
            self.players.append(user_id)

    def start(self):
        self.started = True
        self.winner = random.choice(self.players) if self.players else None

def get_game(chat_id):
    if chat_id not in GAMES:
        GAMES[chat_id] = Game(chat_id)
    return GAMES[chat_id]

# -------------------------------
# 🔹 AI комментатор
# -------------------------------
def get_ai_comment(winner_name, losers):
    if not OPENROUTER_KEY:
        return "😂 Комментатордың микрофоны өшіп қалған сияқты!"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "mistralai/mixtral-8x7b",
        "messages": [
            {"role": "system", "content": "Сен қазақша сөйлейтін комментаторсың. Әзіл мен эмоция қос, бірақ мәдениетті бол."},
            {"role": "user", "content": f"Жеңімпаз: {winner_name}. Жеңілгендер: {', '.join(losers)}. Қысқа әзіл жаз."}
        ]
    }
    try:
        r = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print("AI comment error:", e)
        return "😂 Комментатор картасын жоғалтып алды!"

# -------------------------------
# 🔹 /start командасы
# -------------------------------
@dp.message(Command("start"))
async def start_cmd(msg: Message):
    web_app_url = f"https://erzhan279.github.io/Durakkkkkkk/?chat={msg.chat.id}"
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("🃏 Durak Mini App ашу", web_app=WebAppInfo(url=web_app_url))]
    ])
    await msg.answer(
        "🎮 Durak ойынына қош келдің!\nБатырманы басып ойынды баста:",
        reply_markup=markup
    )

# -------------------------------
# 🔹 /endgame командасы
# -------------------------------
@dp.message(Command("endgame"))
async def end_game(msg: Message):
    game = get_game(msg.chat.id)
    if not game.players:
        await msg.answer("Ойыншылар жоқ 😅")
        return
    winner = random.choice(game.players)
    losers = [p for p in game.players if p != winner]
    comment = get_ai_comment(f"Ойыншы {winner}", [str(l) for l in losers])
    await msg.answer(f"🏆 Ойыншы {winner} жеңді!\n\n🎤 {comment}")

# -------------------------------
# 🔹 Сервер мен ботты бірге іске қосу
# -------------------------------
async def start_bot():
    await dp.start_polling(bot)

@app.on_event("startup")
async def on_startup():
    asyncio.create_task(start_bot())

@app.get("/")
def root():
    return {"status": "Bot is running!"}

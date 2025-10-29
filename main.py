import os
import asyncio
from fastapi import FastAPI
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from pydantic import BaseModel
import requests
import random

# 🔹 Бот және серверді орнату
BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)
app = FastAPI()

# ----- Ойын мәліметтері -----
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

# ----- AI комментатор -----
def get_ai_comment(winner_name, losers):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "mistralai/mixtral-8x7b",
        "messages": [
            {"role": "system", "content": "Сен қазақша сөйлейтін комментаторсың. Әзіл қос, бірақ мәдениетті түрде."},
            {"role": "user", "content": f"Жеңімпаз: {winner_name}. Жеңілгендер: {', '.join(losers)}. Қысқа әзіл жаз."}
        ]
    }
    try:
        r = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print("AI comment error:", e)
        return "😂 Комментатор картасын жоғалтып алды!"

# ----- /start -----
@dp.message_handler(commands=["start"])
async def start_cmd(msg: types.Message):
    web_app_url = f"https://erzhan279.github.io/Durakkkkkkk/?chat={msg.chat.id}"
    markup = InlineKeyboardMarkup().add(
        InlineKeyboardButton("🃏 Durak Mini App ашу", web_app=WebAppInfo(url=web_app_url))
    )
    await msg.answer("🎮 Durak ойынына қош келдің!\nБатырманы басып ойынды баста:",
                     reply_markup=markup)

# ----- /join -----
class JoinReq(BaseModel):
    user_id: int
    chat_id: int

@app.post("/join")
async def join(req: JoinReq):
    game = get_game(req.chat_id)
    game.add_player(req.user_id)
    await bot.send_message(req.chat_id, f"🧑‍💻 Ойыншы қосылды: {req.user_id}")
    return {"ok": True}

# ----- /endgame -----
@dp.message_handler(commands=["endgame"])
async def end_game(msg: types.Message):
    game = get_game(msg.chat.id)
    if not game.players:
        await msg.answer("Ойыншылар жоқ 😅")
        return
    winner = random.choice(game.players)
    losers = [p for p in game.players if p != winner]
    comment = get_ai_comment("Ойыншы " + str(winner), [str(l) for l in losers])
    await msg.answer(f"🏆 Ойыншы {winner} жеңді!\n\n🎤 {comment}")

# ----- Сервер мен ботты іске қосу -----
async def start_bot():
    await dp.start_polling()

@app.on_event("startup")
async def on_startup():
    asyncio.create_task(start_bot())

@app.get("/")
def root():
    return {"status": "Bot is running!"}

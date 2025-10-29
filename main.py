import os
import traceback
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from openai import OpenAI

# === Config ===
BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
HOST = os.getenv("RENDER_EXTERNAL_HOSTNAME") or "durakbott.onrender.com"
WEBHOOK_PATH = f"/webhook"
WEBHOOK_URL = f"https://{HOST}{WEBHOOK_PATH}"

app = FastAPI()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_API_KEY)

# === Handlers ===
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    web_app_url = "https://erzhan279.github.io/Durakkkkkkk/"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🃏 Durak Mini App ашу", web_app=WebAppInfo(url=web_app_url))]
    ])
    await message.answer("Сәлем! Durak ойынын бастау үшін батырманы басыңыз:", reply_markup=kb)

@dp.message(Command("ping"))
async def ping(message: types.Message):
    await message.answer("pong")

# === Webhook setup ===
@app.on_event("startup")
async def on_startup():
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await bot.set_webhook(WEBHOOK_URL)
        print(f"🚀 Webhook орнатылды: {WEBHOOK_URL}")
    except Exception as e:
        print("❌ Webhook орнату қатесі:", e)

@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        update = types.Update(**data)
        await dp.feed_update(bot, update)
        return {"ok": True}
    except Exception as e:
        print("❌ Webhook өңдеу қатесі:", e)
        traceback.print_exc()
        return {"ok": False, "error": str(e)}

@app.get("/")
async def root():
    return {"status": "Durak bot is running via webhook"}

import os
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, Update
import asyncio

# -------------------------------
# 🔑 Токен мен URL параметрлері
# -------------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN", "8005464032:AAGZJW7DjwUI_CxRYm-5J4bPUEqGw1QbBwg")
WEBHOOK_URL = "https://durakbott.onrender.com/webhook"
WEB_APP_URL = "https://erzhan279.github.io/Durakkkkkkk/"

# -------------------------------
# ⚙️ Aiogram және FastAPI орнату
# -------------------------------
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
app = FastAPI()

# -------------------------------
# 📲 Бастапқы /start командасы
# -------------------------------
@dp.message()
async def start_handler(message: types.Message):
    if message.text == "/start":
        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🃏 Durak Mini App ашу",
                        web_app=WebAppInfo(url=WEB_APP_URL)
                    )
                ]
            ]
        )
        await message.answer(
            "Сәлем 👋 Бұл — Durak Mini App ойыны!\n\n"
            "Төмендегі батырманы басып, ойынды аш:",
            reply_markup=markup
        )

# -------------------------------
# 🌐 Webhook маршруты (POST)
# -------------------------------
@app.post("/webhook")
async def webhook_handler(request: Request):
    # Telegram-нан келген JSON-ды оқу
    data = await request.json()

    # dict -> Update түрлендіру
    update = Update(**data)

    # Dispatcher-ге жіберу
    await dp.feed_update(bot, update)

    return {"ok": True}

# -------------------------------
# ✅ Render тексерісі үшін GET
# -------------------------------
@app.get("/webhook")
async def webhook_check():
    return {"status": "Webhook is active 🚀"}

# -------------------------------
# 🚀 Стартап (webhook орнату)
# -------------------------------
@app.on_event("startup")
async def on_startup():
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)
    print(f"🚀 Webhook орнатылды: {WEBHOOK_URL}")

# -------------------------------
# 💤 Асинхронды цикл іске қосу
# -------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
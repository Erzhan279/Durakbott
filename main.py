import os
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from openai import OpenAI

# === Токендер мен баптаулар ===
BOT_TOKEN = os.getenv("TG_BOT_TOKEN") or "8005464032:AAGZJW7DjwUI_CxRYm-5J4bPUEqGw1QbBwg"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY") or "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"
WEBHOOK_HOST = "https://durakbott.onrender.com"
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

# === FastAPI, Telegram және OpenRouter клиенттері ===
app = FastAPI()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_API_KEY)

# === Start командасы ===
@dp.message(commands=["start"])
async def start_cmd(message: types.Message):
    web_app_url = "https://erzhan279.github.io/Durakkkkkkk/"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🃏 Durak Mini App ашу", web_app=WebAppInfo(url=web_app_url))]
    ])
    await message.answer("Сәлем 👋\nDurak Mini App ойынын бастау үшін төмендегі батырманы бас:", reply_markup=keyboard)

# === /winner және /loser командалары ===
@dp.message(commands=["winner"])
async def winner(message: types.Message):
    username = message.from_user.first_name
    ai_response = get_ai_reaction(f"Ойыншы {username} Durak ойынында жеңді. Қазақша мақтау сөздермен, әзіл қосып жауап бер.")
    await message.answer(ai_response)

@dp.message(commands=["loser"])
async def loser(message: types.Message):
    username = message.from_user.first_name
    ai_response = get_ai_reaction(f"Ойыншы {username} Durak ойынында жеңілді. Қазақша жеңілді деп, әзілмен мазақта.")
    await message.answer(ai_response)

# === OpenRouter AI жауап функциясы ===
def get_ai_reaction(prompt: str) -> str:
    try:
        response = client.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Сен Durak ойынының көңілді комментаторысың."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"AI жауап бере алмады 😅 ({e})"

# === Webhook орнату және сервер ===
@app.on_event("startup")
async def on_startup():
    await bot.set_webhook(WEBHOOK_URL)
    print(f"🚀 Webhook орнатылды: {WEBHOOK_URL}")

@app.on_event("shutdown")
async def on_shutdown():
    await bot.delete_webhook()

@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    data = await request.json()
    update = types.Update(**data)
    await dp.feed_update(bot, update)
    return {"ok": True}

@app.get("/")
async def root():
    return {"status": "Durak bot with AI is running 🚀"}

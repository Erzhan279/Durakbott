import os
import traceback
from fastapi import FastAPI, Request, Response
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, Message
from aiogram.filters import Command
import requests
from pydantic import BaseModel
from game_engine import get_game
import time

# ---------------------------
# Конфигурация (ортадан алынады)
# ---------------------------
BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")
# HOST: Render автоматты түрде орнатады; локалда тест үшін override қоюға болады
HOST = os.getenv("RENDER_EXTERNAL_HOSTNAME") or os.getenv("HOSTNAME") or "durakbott.onrender.com"
WEBHOOK_PATH = "/webhook"         # қауіпсіз болу үшін token path-қа қоймадық
WEBHOOK_URL = f"https://{HOST}{WEBHOOK_PATH}"

if not BOT_TOKEN:
    raise RuntimeError("TG_BOT_TOKEN орнатылмаған. Render Environment Variables-қа қосыңыз.")

# ---------------------------
# Инициализация
# ---------------------------
app = FastAPI()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ---------------------------
# Utility: OpenRouter call via requests (no extra lib)
# ---------------------------
def openrouter_chat_completion(system_prompt: str, user_prompt: str, model="openai/gpt-4o-mini"):
    if not OPENROUTER_KEY:
        return None
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "max_tokens": 200
    }
    r = requests.post(url, json=payload, headers=headers, timeout=15)
    r.raise_for_status()
    data = r.json()
    # safe extraction
    try:
        return data["choices"][0]["message"]["content"]
    except Exception:
        return None

# ---------------------------
# Handlers (aiogram 3.x style)
# ---------------------------
@dp.message(Command("start"))
async def handle_start(message: Message):
    # WebApp link points to our /game route
    web_app_url = f"https://{HOST}/game?chat={message.chat.id}"
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🃏 Durak Mini App ашу", web_app=WebAppInfo(url=web_app_url))]
    ])
    await message.answer("Сәлем! Durak ойынына қош келдің. Батырманы басып Mini App ашыңыз:", reply_markup=markup)

# quick ping
@dp.message(Command("ping"))
async def handle_ping(message: Message):
    await message.reply("pong")

# admin /endgame to force finish and ask AI to comment
@dp.message(Command("endgame"))
async def handle_endgame(message: Message):
    game = get_game(message.chat.id)
    if not game.players or not game.started:
        await message.reply("Ойын жүріп жатқан жоқ.")
        return
    # pick winner randomly (placeholder) and ask AI comment
    winner = None
    if game.players:
        winner = game.players[0]  # simple: first player considered winner for now
    losers = [p for p in game.players if p != winner]
    winner_name = f"Ойыншы {winner}"
    loser_names = [f"Ойыншы {x}" for x in losers]
    prompt_user = f"Жеңімпаз: {winner_name}. Жеңілгендер: {', '.join(loser_names)}. Қысқа, қазақша әзіл-қалжыңдармен мақтау және мазақ жаз."
    system = "Сен қазақша көңілді комментаторсың. Мәдени, әзілмен, қысқа және көңілді бол."
    ai_text = openrouter_chat_completion(system, prompt_user) or "AI жауап бере алмады 😅"
    await message.reply(f"🏆 {winner_name} жеңді!\n\n🎤 {ai_text}")

# ---------------------------
# API models for frontend POSTs
# ---------------------------
class JoinReq(BaseModel):
    user_id: int
    chat_id: int

class StartReq(BaseModel):
    chat_id: int

class AdviceReq(BaseModel):
    user_id: int
    chat_id: int
    hand: list
    table: list
    move: str

# Frontend calls this to join game
@app.post("/join")
async def api_join(req: JoinReq):
    g = get_game(req.chat_id)
    added = g.add_player(req.user_id)
    # notify group chat via bot
    try:
        await bot.send_message(req.chat_id, f"🧑‍💻 Ойыншы қосылды: {req.user_id}")
    except Exception as e:
        print("notify join error:", e)
    return {"ok": True, "added": added}

# Frontend calls to start game (deal)
@app.post("/startgame")
async def api_startgame(req: StartReq):
    g = get_game(req.chat_id)
    if len(g.players) < 2:
        return {"ok": False, "error": "Кемінде 2 ойыншы қажет"}
    g.deal()
    # notify chat
    try:
        await bot.send_message(req.chat_id, f"🎮 Ойын басталды! Козыр: {g.trump}")
    except Exception as e:
        print("notify start error:", e)
    return {"ok": True, "state": g.serialize_for_frontend()}

# Frontend requests advice (AI) — bot posts the advice to chat
@app.post("/advice")
async def api_advice(req: AdviceReq):
    # build prompt
    user_hand = ", ".join(req.hand)
    table = ", ".join(req.table)
    prompt = f"Қолымдағы карталар: {user_hand}. Үстелде: {table}. Мен {req.move} салсам қайсысы дұрыс? Қысқа қазақша кеңес бер."
    system = "Сен Durak ойынының кеңесшісісың. Қысқа нақты ұсыныс бер."
    ai = openrouter_chat_completion(system, prompt)
    text = ai or "AI кеңес бере алмады."
    try:
        await bot.send_message(req.chat_id, f"🤖 Кеңес: {text}")
    except Exception as e:
        print("notify advice error:", e)
    return {"ok": True, "advice": text}

# ---------------------------
# Webhook setup + handler
# ---------------------------
@app.on_event("startup")
async def on_startup():
    try:
        # remove existing webhook to avoid conflicts
        await bot.delete_webhook(drop_pending_updates=True)
    except Exception as e:
        print("delete_webhook error (ignored):", e)
    try:
        # set webhook to our /webhook path
        await bot.set_webhook(WEBHOOK_URL)
        print("🚀 Webhook орнатылды:", WEBHOOK_URL)
    except Exception as e:
        print("set_webhook error:", e)

@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        update = types.Update(**data)
        # process update, but protect against crashes
        try:
            await dp.feed_update(bot, update)
        except Exception as e:
            print("dp.feed_update error:", e)
            traceback.print_exc()
        return {"ok": True}
    except Exception as e:
        print("webhook top-level error:", e)
        traceback.print_exc()
        return Response(status_code=200, content='{"ok":false}')

# ---------------------------
# Mini App page (simple self-contained HTML)
# ---------------------------
@app.get("/game")
async def serve_game(request: Request):
    # Note: do not include secret keys here. This page uses Telegram WebApp JS.
    html = f"""
    <!doctype html>
    <html lang="kk">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width,initial-scale=1">
      <title>DURAK Mini App</title>
      <script src="https://telegram.org/js/telegram-web-app.js"></script>
      <style>
        body{{margin:0;background:radial-gradient(circle at center,#5b3c1e,#2e1b0b);font-family:Segoe UI,Arial;color:#fff;}}
        .table{{width:95%;height:90vh;margin:2vh auto;background:#4b2a15;border-radius:20px;padding:20px;box-sizing:border-box;border:10px solid #c9a87c;position:relative;overflow:hidden;}}
        .pattern{{position:absolute;inset:0;background-image:url('https://upload.wikimedia.org/wikipedia/commons/9/90/Kazakh_pattern.svg');opacity:0.06;background-size:180px;z-index:1;}}
        h1{{text-align:center;margin:0 0 10px 0;z-index:2;position:relative;}}
        #cards{{display:flex;justify-content:center;gap:10px;flex-wrap:wrap;position:relative;z-index:2;}}
        .card{{width:80px;height:120px;border-radius:10px;background:#fff;box-shadow:0 6px 12px rgba(0,0,0,0.4);display:flex;align-items:center;justify-content:center;font-weight:bold;color:#111;}}
        .controls{{position:absolute;bottom:20px;left:50%;transform:translateX(-50%);z-index:3;}}
        button{{padding:12px 20px;border-radius:10px;border:none;background:#c9a87c;color:#2e1b0b;font-weight:600;margin:0 8px;cursor:pointer;}}
      </style>
    </head>
    <body>
      <div class="table">
        <div class="pattern"></div>
        <h1>🃏 DURAK (Mini App)</h1>
        <div id="status" style="text-align:center;margin-bottom:10px;z-index:2;">Ойынға қосылып, бастауға дайын болыңыз</div>
        <div id="cards"></div>
        <div class="controls">
          <button id="joinBtn">👥 Топқа қосылу</button>
          <button id="startBtn">🎮 Ойынды бастау</button>
          <button id="adviceBtn">🤖 Кеңес сұрау</button>
        </div>
      </div>

      <script>
        const tg = window.Telegram?.WebApp;
        if (tg) tg.expand();
        const params = new URLSearchParams(window.location.search);
        const chatId = params.get('chat') || '';
        const user = tg?.initDataUnsafe?.user;
        const backend = window.location.origin; // same host

        document.getElementById('joinBtn').onclick = async () => {
          if (!user) return alert('Telegram ішінде Mini App ашып көріңіз.');
          await fetch(backend + '/join', {
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body: JSON.stringify({user_id:user.id, chat_id: parseInt(chatId)})
          });
          document.getElementById('status').innerText = '👥 Сен топқа қосылдың';
        };

        document.getElementById('startBtn').onclick = async () => {
          if (!chatId) return alert('Chat id жоқ.');
          const res = await fetch(backend + '/startgame', {
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body: JSON.stringify({chat_id: parseInt(chatId)})
          });
          const j = await res.json();
          if (j.ok) {
            document.getElementById('status').innerText = '🎮 Ойын басталды — карталар бөлінді';
            // show placeholder cards
            renderCards(6);
          } else {
            alert(j.error || 'Қате');
          }
        };

        document.getElementById('adviceBtn').onclick = async () => {
          if (!user) return alert('Telegram ішінде ашыңыз');
          // sample minimal payload
          const sampleHand = ['6♠','9♥','A♣'];
          const sampleTable = [];
          const sampleMove = sampleHand[0];
          await fetch(backend + '/advice', {
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body: JSON.stringify({user_id:user.id, chat_id: parseInt(chatId), hand: sampleHand, table: sampleTable, move: sampleMove})
          });
        };

        function renderCards(n){
          const container = document.getElementById('cards');
          container.innerHTML = '';
          for(let i=0;i<n;i++){
            const d = document.createElement('div');
            d.className='card';
            d.style.transform = 'rotate(' + (Math.random()*12-6) + 'deg)';
            d.innerText = '♠';
            container.appendChild(d);
          }
        }
      </script>
    </body>
    </html>
    """
    return Response(content=html, media_type="text/html")

# ---------------------------
# Root health
# ---------------------------
@app.get("/")
async def root():
    return {"status":"Durak bot running (webhook)"}

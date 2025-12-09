import json
import threading
import time
from datetime import datetime
from telegram import Bot
import websocket
import os

# =========================
# 🔥 ВИМКНУТИ ПРОКСІ RAILWAY
# =========================
for key in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"]:
    os.environ.pop(key, None)

# =========================
# 🔐 ДАНІ З ENV
# =========================
TOKEN = os.getenv("TG_TOKEN")
CHAT_ID = os.getenv("TG_CHAT_ID")

# =========================
# ⚙️ НАЛАШТУВАННЯ
# =========================
ALERT_DIFF = 5.0
MIN_REPEAT_DIFF = 1.0

bot = Bot(token=TOKEN)
WS_URL = "wss://contract.mexc.com/ws"

last_prices = {}
mark_prices = {}
last_alerts = {}

def on_message(ws, message):
    try:
        data = json.loads(message)

        if not isinstance(data, dict):
            return

        channel = data.get("channel")
        payload = data.get("data")

        if not channel or not payload:
            return

        if channel == "push.ticker":
            symbol = payload.get("symbol")
            last_prices[symbol] = float(payload.get("lastPrice"))

        elif channel == "push.mark.price":
            symbol = payload.get("symbol")
            mark_prices[symbol] = float(payload.get("markPrice"))

        if "symbol" in locals() and symbol in last_prices and symbol in mark_prices:
            last = last_prices[symbol]
            mark = mark_prices[symbol]
            diff = (last - mark) / mark * 100

            if abs(diff) >= ALERT_DIFF:
                sym = symbol.replace("_", "")
                d = round(diff, 2)

                if sym in last_alerts and abs(d - last_alerts[sym]) < MIN_REPEAT_DIFF:
                    return

                last_alerts[sym] = d
                now = datetime.now().strftime("%H:%M:%S")

                text = (
                    f"🚨 MEXC FUTURES ALERT\n\n"
                    f"{sym}\n"
                    f"Last: {last}\n"
                    f"Mark: {mark}\n"
                    f"Δ: {d}%\n"
                    f"⏱ {now}"
                )

                bot.send_message(chat_id=CHAT_ID, text=text)

    except Exception as e:
        print("MESSAGE ERROR:", e)

def on_open(ws):
    print("✅ Socket підключений")

    ws.send(json.dumps({
        "method": "sub.ticker",
        "params": [],
        "id": 1
    }))

    ws.send(json.dumps({
        "method": "sub.mark.price",
        "params": [],
        "id": 2
    }))

def on_error(ws, error):
    print("SOCKET ERROR:", error)

def on_close(ws, close_status_code, close_msg):
    print("❌ Socket закрито. Перепідключення через 5 сек...")
    time.sleep(5)
    start_socket()

def start_socket():
    ws = websocket.WebSocketApp(
        WS_URL,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    ws.run_forever(ping_interval=20, ping_timeout=10)

print("✅ Автобот запущений (WebSocket)...")
threading.Thread(target=start_socket).start()

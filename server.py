import sqlite3
import asyncio
from datetime import datetime
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
import MetaTrader5 as mt5

app = FastAPI()

SYMBOL = "XAUUSD"
MAGIC_NUMBER = 108801
DB_FILE = "trading_agent_memory.db"

# Timeframe mapping
TF_MAP = {
    "1M": mt5.TIMEFRAME_M1,
    "5M": mt5.TIMEFRAME_M5,
    "15M": mt5.TIMEFRAME_M15,
    "1H": mt5.TIMEFRAME_H1
}

def get_real_mt5_data(timeframe_str="5M"):
    if not mt5.initialize():
        return None

    acc = mt5.account_info()
    sym = mt5.symbol_info(SYMBOL)
    tick = mt5.symbol_info_tick(SYMBOL)

    account_data = {
        "login": acc.login if acc else "N/A",
        "server": acc.server if acc else "N/A",
        "balance": round(acc.balance, 2) if acc else 0.0,
        "equity": round(acc.equity, 2) if acc else 0.0,
        "pnl": round(acc.profit, 2) if acc else 0.0,
        "margin_free": round(acc.margin_free, 2) if acc else 0.0,
        "margin_level": round(acc.margin_level, 1) if acc and acc.margin_level else 100.0,
        "leverage": acc.leverage if acc else 100
    }

    market_data = {
        "symbol": SYMBOL,
        "bid": round(tick.bid, 2) if tick else 0.0,
        "ask": round(tick.ask, 2) if tick else 0.0,
        "spread": sym.spread if sym else 0,
        "is_open": (sym.trade_mode == mt5.SYMBOL_TRADE_MODE_FULL) if sym else False
    }

    raw_positions = mt5.positions_get(symbol=SYMBOL) or []
    positions = []
    for p in raw_positions:
        positions.append({
            "ticket": p.ticket,
            "type": "BUY" if p.type == mt5.ORDER_TYPE_BUY else "SELL",
            "volume": p.volume,
            "entry": round(p.price_open, 2),
            "current": round(p.price_current, 2),
            "sl": round(p.sl, 2),
            "tp": round(p.tp, 2),
            "pnl": round(p.profit, 2)
        })

    # Selected Timeframe ke candles fetch karein
    selected_tf = TF_MAP.get(timeframe_str, mt5.TIMEFRAME_M5)
    rates = mt5.copy_rates_from_pos(SYMBOL, selected_tf, 0, 60)
    candles = []
    if rates is not None and len(rates) > 0:
        for r in rates:
            candles.append({
                "open": round(r['open'], 2),
                "high": round(r['high'], 2),
                "low": round(r['low'], 2),
                "close": round(r['close'], 2),
                "time": int(r['time'])
            })

    db_logs = []
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT ticket, action, pnl, bias_15m, mistake_tag, open_time FROM trades ORDER BY ticket DESC LIMIT 5")
        rows = c.fetchall()
        for row in rows:
            db_logs.append({
                "ticket": row[0],
                "action": row[1],
                "pnl": row[2] or 0.0,
                "bias": row[3],
                "tag": row[4] or "PROCESSING",
                "time": row[5]
            })
        conn.close()
    except Exception:
        pass

    return {
        "account": account_data,
        "market": market_data,
        "positions": positions,
        "candles": candles,
        "logs": db_logs,
        "tf": timeframe_str,
        "time": datetime.utcnow().strftime("%H:%M:%S")
    }

@app.get("/")
def serve_dashboard():
    with open("index.html", "r", encoding="utf-8") as f:
        html = f.read()
    return HTMLResponse(content=html)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    current_client_tf = "5M"

    async def listen_for_tf_changes():
        nonlocal current_client_tf
        try:
            while True:
                msg = await websocket.receive_text()
                if msg in TF_MAP:
                    current_client_tf = msg
        except Exception:
            pass

    asyncio.create_task(listen_for_tf_changes())

    while True:
        try:
            data = get_real_mt5_data(current_client_tf)
            if data:
                await websocket.send_json(data)
            await asyncio.sleep(1.0)
        except Exception:
            break
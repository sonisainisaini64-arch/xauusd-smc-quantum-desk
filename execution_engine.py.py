import MetaTrader5 as mt5
import sqlite3
from datetime import datetime

DB_FILE = "trading_agent_memory.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            ticket INTEGER PRIMARY KEY,
            symbol TEXT,
            action TEXT,
            entry_price REAL,
            sl REAL,
            tp REAL,
            lot_size REAL,
            bias_15m TEXT,
            fvg_size REAL,
            open_time TEXT,
            close_time TEXT,
            exit_price REAL,
            pnl REAL,
            status TEXT,
            mistake_tag TEXT
        )
    """)
    conn.commit()
    conn.close()

def log_trade_entry(trade_data):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO trades (
            ticket, symbol, action, entry_price, sl, tp, 
            lot_size, bias_15m, fvg_size, open_time, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN')
    """, (
        trade_data['ticket'],
        trade_data['symbol'],
        trade_data['action'],
        trade_data['entry_price'],
        trade_data['sl'],
        trade_data['tp'],
        trade_data['lot_size'],
        trade_data['bias_15m'],
        trade_data['fvg_size'],
        datetime.utcnow().isoformat()
    ))
    conn.commit()
    conn.close()

def calculate_lot_size(symbol, sl_points, risk_percent=0.5):
    account_info = mt5.account_info()
    if not account_info:
        return 0.01

    equity = account_info.equity
    risk_amount = equity * (risk_percent / 100.0)
    
    symbol_info = mt5.symbol_info(symbol)
    if not symbol_info:
        return 0.01

    point = symbol_info.point
    tick_value = symbol_info.trade_tick_value
    
    if sl_points <= 0 or tick_value <= 0:
        return symbol_info.volume_min

    raw_lot = risk_amount / (sl_points * tick_value)
    step = symbol_info.volume_step
    lot = round(raw_lot / step) * step
    lot = max(symbol_info.volume_min, min(lot, symbol_info.volume_max))
    
    return round(lot, 2)

def execute_trade(signal, symbol="XAUUSD", max_spread=40):
    symbol_info = mt5.symbol_info(symbol)
    if not symbol_info.visible:
        mt5.symbol_select(symbol, True)

    current_spread = symbol_info.spread
    if current_spread > max_spread:
        print(f"[!] Trade Skipped: High Spread ({current_spread} > {max_spread})")
        return False

    is_buy = signal['action'] == "BUY"
    order_type = mt5.ORDER_TYPE_BUY if is_buy else mt5.ORDER_TYPE_SELL
    price = symbol_info.ask if is_buy else symbol_info.bid
    
    sl_distance_points = abs(price - signal['sl']) / symbol_info.point
    lot_size = calculate_lot_size(symbol, sl_distance_points, risk_percent=0.5)

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot_size,
        "type": order_type,
        "price": price,
        "sl": signal['sl'],
        "tp": signal['tp'],
        "deviation": 20,
        "magic": 108801,
        "comment": "SMC_AI_Agent_V1",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"[!] Order Rejected: {result.comment} (Code: {result.retcode})")
        return False

    print(f"[✓] Order Placed! Ticket: {result.order}, Lots: {lot_size}, Price: {price}")
    
    log_data = {
        'ticket': result.order,
        'symbol': symbol,
        'action': signal['action'],
        'entry_price': price,
        'sl': signal['sl'],
        'tp': signal['tp'],
        'lot_size': lot_size,
        'bias_15m': signal['bias'],
        'fvg_size': signal['fvg_size']
    }
    log_trade_entry(log_data)
    return True

def update_closed_trades():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT ticket, entry_price, sl, tp, action FROM trades WHERE status = 'OPEN'")
    open_trades = cursor.fetchall()
    
    for ticket, entry, sl, tp, action in open_trades:
        deals = mt5.history_deals_get(position=ticket)
        if deals and len(deals) > 1:
            closing_deal = deals[-1]
            pnl = closing_deal.profit
            exit_price = closing_deal.price
            close_time = datetime.fromtimestamp(closing_deal.time).isoformat()
            
            mistake_tag = "CLEAN_WIN" if pnl > 0 else "UNDETERMINED_LOSS"
            if pnl < 0:
                if abs(exit_price - sl) <= 0.30:
                    mistake_tag = "TIGHT_SL_WICKED"
                else:
                    mistake_tag = "REGIME_FAILURE"

            cursor.execute("""
                UPDATE trades 
                SET status = 'CLOSED', exit_price = ?, pnl = ?, close_time = ?, mistake_tag = ?
                WHERE ticket = ?
            """, (exit_price, pnl, close_time, mistake_tag, ticket))
            
    conn.commit()
    conn.close()
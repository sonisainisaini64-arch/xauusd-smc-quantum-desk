import time
from datetime import datetime
import MetaTrader5 as mt5

from strategy_engine import init_mt5, evaluate_market
from execution_engine import init_db, execute_trade, update_closed_trades

SYMBOL = "XAUUSD"
TIMEFRAME_MINUTES = 5
MAX_SPREAD_POINTS = 40
MAGIC_NUMBER = 108801

def has_open_position(symbol=SYMBOL):
    positions = mt5.positions_get(symbol=symbol)
    if positions is None:
        return False
    bot_positions = [pos for pos in positions if pos.magic == MAGIC_NUMBER]
    return len(bot_positions) > 0

def seconds_until_next_candle(interval_minutes=5):
    now = datetime.now()
    minutes_passed = now.minute % interval_minutes
    seconds_passed = (minutes_passed * 60) + now.second + (now.microsecond / 1_000_000.0)
    total_interval_seconds = interval_minutes * 60
    remaining = total_interval_seconds - seconds_passed
    return max(0.5, remaining)

def run_agent():
    print("=" * 60)
    print(f"[*] Starting SMC Self-Improving Trading Agent for {SYMBOL}")
    print(f"[*] Timeframe: M5 Execution | M15 Structure Bias")
    print("=" * 60)

    init_mt5()
    init_db()

    account = mt5.account_info()
    if account is None:
        print("[!] Unable to fetch account info. Make sure MT5 is open and logged in.")
        return

    print(f"[✓] Connected: Account {account.login} | Server: {account.server}")
    print(f"[✓] Equity: ${account.equity:.2f} | Leverage: 1:{account.leverage}")

    try:
        while True:
            update_closed_trades()

            sleep_time = seconds_until_next_candle(TIMEFRAME_MINUTES) + 2.0
            next_check = datetime.now().timestamp() + sleep_time
            print(f"\n[~] Waiting for next 5m candle close ({datetime.fromtimestamp(next_check).strftime('%H:%M:%S')})...")
            time.sleep(sleep_time)

            if not mt5.terminal_info().connected:
                print("[!] Terminal disconnected. Reconnecting...")
                mt5.initialize()
                continue

            print(f"\n[+] Analyzing market at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}...")

            if has_open_position(SYMBOL):
                print(f"[*] Position already active for {SYMBOL}. Skipping new entries.")
                continue

            signal = evaluate_market(SYMBOL)
            
            if signal:
                print(f"[★] SIGNAL: {signal['action']} at {signal['entry']}")
                print(f"    15m Bias: {signal['bias']} | FVG Size: {signal['fvg_size']}")
                print(f"    SL: {signal['sl']} | TP: {signal['tp']}")

                success = execute_trade(signal, symbol=SYMBOL, max_spread=MAX_SPREAD_POINTS)
                if success:
                    print("[✓] Trade successfully placed & recorded.")
                else:
                    print("[X] Trade rejected by risk checks.")
            else:
                print("[-] No valid setup on this candle.")

    except KeyboardInterrupt:
        print("\n[!] Stopped manually.")
    finally:
        mt5.shutdown()
        print("[✓] MT5 disconnected.")

if __name__ == "__main__":
    run_agent()
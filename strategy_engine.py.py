import MetaTrader5 as mt5
import pandas as pd
import numpy as np

def init_mt5():
    if not mt5.initialize():
        raise RuntimeError(f"MT5 Init Failed: {mt5.last_error()}")

def get_resampled_data(symbol="XAUUSD", n_bars=3000):
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, n_bars)
    if rates is None or len(rates) == 0:
        return None, None
        
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    
    resample_rules = {
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'tick_volume': 'sum',
        'spread': 'mean'
    }
    
    df_5m = df.resample('5min').agg(resample_rules).dropna()
    df_15m = df.resample('15min').agg(resample_rules).dropna()
    
    return df_5m, df_15m

def detect_swings(df, window=3):
    df = df.copy()
    df['swing_high'] = False
    df['swing_low'] = False
    
    for i in range(window, len(df) - window):
        if all(df['high'].iloc[i] > df['high'].iloc[i - j] for j in range(1, window + 1)) and \
           all(df['high'].iloc[i] > df['high'].iloc[i + j] for j in range(1, window + 1)):
            df.loc[df.index[i], 'swing_high'] = True
            
        if all(df['low'].iloc[i] < df['low'].iloc[i - j] for j in range(1, window + 1)) and \
           all(df['low'].iloc[i] < df['low'].iloc[i + j] for j in range(1, window + 1)):
            df.loc[df.index[i], 'swing_low'] = True
            
    return df

def get_15m_bias(df_15m):
    df = detect_swings(df_15m, window=2)
    recent_highs = df[df['swing_high']]['high'].tail(2)
    recent_lows = df[df['swing_low']]['low'].tail(2)
    
    if len(recent_highs) >= 2 and len(recent_lows) >= 2:
        if recent_highs.iloc[-1] > recent_highs.iloc[-2] and recent_lows.iloc[-1] > recent_lows.iloc[-2]:
            return "BULLISH"
        elif recent_highs.iloc[-1] < recent_highs.iloc[-2] and recent_lows.iloc[-1] < recent_lows.iloc[-2]:
            return "BEARISH"
    return "NEUTRAL"

def find_5m_fvg(df_5m):
    c1, c2, c3 = df_5m.iloc[-3], df_5m.iloc[-2], df_5m.iloc[-1]
    
    if c3['low'] > c1['high']:
        return {'type': 'BULLISH', 'top': c3['low'], 'bottom': c1['high'], 'size': c3['low'] - c1['high']}
        
    if c3['high'] < c1['low']:
        return {'type': 'BEARISH', 'top': c1['low'], 'bottom': c3['high'], 'size': c1['low'] - c3['high']}
        
    return None

def evaluate_market(symbol="XAUUSD"):
    df_5m, df_15m = get_resampled_data(symbol)
    if df_5m is None or len(df_5m) < 50:
        return None

    bias = get_15m_bias(df_15m)
    df_5m_swings = detect_swings(df_5m, window=3)
    
    swing_lows = df_5m_swings[df_5m_swings['swing_low']]['low']
    swing_highs = df_5m_swings[df_5m_swings['swing_high']]['high']
    if len(swing_lows) == 0 or len(swing_highs) == 0:
        return None

    recent_swing_low = swing_lows.iloc[-1]
    recent_swing_high = swing_highs.iloc[-1]
    
    fvg = find_5m_fvg(df_5m)
    last_close = df_5m['close'].iloc[-1]
    signal = None
    
    if bias == "BULLISH" and fvg and fvg['type'] == 'BULLISH':
        sl = recent_swing_low - 0.50
        risk = last_close - sl
        if risk > 0:
            tp = last_close + (risk * 2.5)
            signal = {
                "action": "BUY",
                "entry": last_close,
                "sl": round(sl, 2),
                "tp": round(tp, 2),
                "bias": bias,
                "fvg_size": round(fvg['size'], 2)
            }
            
    elif bias == "BEARISH" and fvg and fvg['type'] == 'BEARISH':
        sl = recent_swing_high + 0.50
        risk = sl - last_close
        if risk > 0:
            tp = last_close - (risk * 2.5)
            signal = {
                "action": "SELL",
                "entry": last_close,
                "sl": round(sl, 2),
                "tp": round(tp, 2),
                "bias": bias,
                "fvg_size": round(fvg['size'], 2)
            }
            
    return signal
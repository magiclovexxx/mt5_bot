"""
Phân tích BB Breakout — Limit Entry + RSI Divergence Filter
"""

import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf8')

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from ta.volatility import BollingerBands, AverageTrueRange
from ta.momentum import RSIIndicator
from src.fetch_data import initialize_mt5

# ══════════════════════════════════════════
# CẤU HÌNH
# ══════════════════════════════════════════
SYMBOL       = "GOLD"
BARS_1Y      = 250 * 24
BB_WINDOW    = 20
BB_STD       = 2
ATR_WINDOW   = 14
RSI_WINDOW   = 14
DIV_LOOKBACK = 20
FORWARD_BARS = 120

RR_RATIOS    = [2, 3]
SL_VAL       = 1.0  # ATR 1.0

OUTPUT_FILE = "results/GOLD_BB_Limit_RSI_Div_Summary.txt"

# ══════════════════════════════════════════
# DATA
# ══════════════════════════════════════════
def load_data(tf, bars):
    # Lấy 1 năm dữ liệu mới nhất
    rates = mt5.copy_rates_from_pos(SYMBOL, tf, 0, bars)
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    return df

def apply_indicators(df):
    bb = BollingerBands(close=df['close'], window=BB_WINDOW, window_dev=BB_STD)
    df['BB_Upper'] = bb.bollinger_hband()
    df['BB_Lower'] = bb.bollinger_lband()
    df['ATR']      = AverageTrueRange(
                         high=df['high'], low=df['low'],
                         close=df['close'], window=ATR_WINDOW).average_true_range()
    df['RSI']      = RSIIndicator(close=df['close'], window=RSI_WINDOW).rsi()
    
    df['BB_Upper_prev'] = df['BB_Upper'].shift(1)
    df['BB_Lower_prev'] = df['BB_Lower'].shift(1)
    df['ATR_prev']      = df['ATR'].shift(1)
    df['RSI_prev']      = df['RSI'].shift(1)
    
    return df.dropna()

def simulate_trade(high_arr, low_arr, start_idx, rev_type, entry_price, sl_dist, rr, forward=FORWARD_BARS):
    if rev_type == 'Đỉnh': # SELL
        sl = entry_price + sl_dist
        tp = entry_price - sl_dist * rr
        
        hit_sl = high_arr[start_idx] >= sl
        hit_tp = low_arr[start_idx] <= tp
        
        if hit_sl: return 'SL'
        if hit_tp: return 'TP'
        
        end_idx = min(start_idx + 1 + forward, len(high_arr))
        for i in range(start_idx + 1, end_idx):
            if high_arr[i] >= sl: return 'SL'
            if low_arr[i]  <= tp: return 'TP'
            
    else: # BUY
        sl = entry_price - sl_dist
        tp = entry_price + sl_dist * rr
        
        hit_sl = low_arr[start_idx] <= sl
        hit_tp = high_arr[start_idx] >= tp
        
        if hit_sl: return 'SL'
        if hit_tp: return 'TP'
        
        end_idx = min(start_idx + 1 + forward, len(low_arr))
        for i in range(start_idx + 1, end_idx):
            if low_arr[i]  <= sl: return 'SL'
            if high_arr[i] >= tp: return 'TP'
            
    return 'None'

def run_analysis(df, tf_label):
    highs = df['high'].values
    lows  = df['low'].values
    rsis  = df['RSI'].values
    
    df['Sell_Limit'] = df['BB_Upper_prev']
    df['Buy_Limit']  = df['BB_Lower_prev']
    
    sell_touches = df['high'] >= df['Sell_Limit']
    buy_touches  = df['low']  <= df['Buy_Limit']
    
    sell_indices_all = np.where(sell_touches)[0]
    buy_indices_all  = np.where(buy_touches)[0]
    
    # Filter valid indices
    sell_indices_all = sell_indices_all[(sell_indices_all > DIV_LOOKBACK) & (sell_indices_all < len(df) - FORWARD_BARS)]
    buy_indices_all  = buy_indices_all[(buy_indices_all > DIV_LOOKBACK) & (buy_indices_all < len(df) - FORWARD_BARS)]
    
    sell_indices_div = []
    buy_indices_div = []
    
    # Tính Divergence
    for i in buy_indices_all:
        window_lows = lows[i-DIV_LOOKBACK:i]
        min_idx = np.argmin(window_lows)
        abs_min_idx = i - DIV_LOOKBACK + min_idx
        
        # Bullish Divergence: Giá chạm band thấp hơn đáy cũ, nhưng RSI hiện tại (T-1) cao hơn RSI tại đáy cũ
        if df['Buy_Limit'].iloc[i] < lows[abs_min_idx] and df['RSI_prev'].iloc[i] > rsis[abs_min_idx]:
            buy_indices_div.append(i)

    for i in sell_indices_all:
        window_highs = highs[i-DIV_LOOKBACK:i]
        max_idx = np.argmax(window_highs)
        abs_max_idx = i - DIV_LOOKBACK + max_idx
        
        # Bearish Divergence: Giá chạm band cao hơn đỉnh cũ, nhưng RSI hiện tại (T-1) thấp hơn RSI tại đỉnh cũ
        if df['Sell_Limit'].iloc[i] > highs[abs_max_idx] and df['RSI_prev'].iloc[i] < rsis[abs_max_idx]:
            sell_indices_div.append(i)
            
    print(f"[{tf_label}] SELL: Total touches={len(sell_indices_all)}, with Div={len(sell_indices_div)}")
    print(f"[{tf_label}] BUY : Total touches={len(buy_indices_all)}, with Div={len(buy_indices_div)}")
    
    results = []
    
    for setup_name, s_idx_list, b_idx_list in [
        ("No Filter (Touch Band)", sell_indices_all, buy_indices_all),
        ("RSI Divergence Filter", sell_indices_div, buy_indices_div)
    ]:
        for rr in RR_RATIOS:
            # SELL
            sell_tp, sell_sl = 0, 0
            for idx in s_idx_list:
                entry = df['Sell_Limit'].iloc[idx]
                atr   = df['ATR_prev'].iloc[idx]
                sl_dist = atr * SL_VAL
                res = simulate_trade(highs, lows, idx, 'Đỉnh', entry, sl_dist, rr, FORWARD_BARS)
                if res == 'TP': sell_tp += 1
                elif res == 'SL': sell_sl += 1
            
            total_s = len(s_idx_list)
            if total_s > 0:
                ev_s = (sell_tp / total_s) * rr - (sell_sl / total_s)
                results.append({
                    'tf': tf_label, 'dir': 'SELL', 'filter': setup_name,
                    'rr': f"1:{rr}", 'total': total_s, 'tp_pct': sell_tp / total_s, 'ev': ev_s
                })
                
            # BUY
            buy_tp, buy_sl = 0, 0
            for idx in b_idx_list:
                entry = df['Buy_Limit'].iloc[idx]
                atr   = df['ATR_prev'].iloc[idx]
                sl_dist = atr * SL_VAL
                res = simulate_trade(highs, lows, idx, 'Đáy', entry, sl_dist, rr, FORWARD_BARS)
                if res == 'TP': buy_tp += 1
                elif res == 'SL': buy_sl += 1
            
            total_b = len(b_idx_list)
            if total_b > 0:
                ev_b = (buy_tp / total_b) * rr - (buy_sl / total_b)
                results.append({
                    'tf': tf_label, 'dir': 'BUY', 'filter': setup_name,
                    'rr': f"1:{rr}", 'total': total_b, 'tp_pct': buy_tp / total_b, 'ev': ev_b
                })
                
    return pd.DataFrame(results)

def main():
    print("Khởi tạo MT5...")
    initialize_mt5()
    
    all_results = []
    for tf_label, tf_mt5, bars in [
        ("M15", mt5.TIMEFRAME_M15, BARS_1Y * 4),
        ("H1",  mt5.TIMEFRAME_H1,  BARS_1Y),
    ]:
        print(f"\n[{tf_label}] Tải {bars:,} nến...")
        df = load_data(tf_mt5, bars)
        df = apply_indicators(df)
        res_df = run_analysis(df, tf_label)
        all_results.append(res_df)
    
    final_df = pd.concat(all_results, ignore_index=True)
    
    lines = []
    lines.append("=========================================================================")
    lines.append("  SO SÁNH: LIMIT ENTRY 0.0% (CHẠM BAND) CÓ VÀ KHÔNG CÓ RSI DIVERGENCE")
    lines.append("  SL: ATR 1.0 | RR: 1:2 & 1:3 | Dữ liệu: 1 năm gần nhất")
    lines.append("=========================================================================\n")
    
    for tf_label in ['M15', 'H1']:
        for dr in ['BUY', 'SELL']:
            lines.append(f"── {tf_label} {dr} ───────────────────────────────────────────────")
            sub = final_df[(final_df['tf'] == tf_label) & (final_df['dir'] == dr)]
            
            lines.append(f"{'Filter':<24} | {'R:R':<6} | {'Trades':<8} | {'TP%':<8} | {'SL%':<8} | {'EV (R)':<8}")
            lines.append("-" * 75)
            for _, r in sub.iterrows():
                flt    = r['filter']
                rr_str = r['rr']
                trd    = f"{int(r['total']):,}"
                tp_pct = f"{r['tp_pct']*100:.1f}%"
                sl_pct = f"{(1 - r['tp_pct'])*100:.1f}%" # Approx
                ev     = f"{r['ev']:.3f}"
                
                tag = "🏆" if r['ev'] >= 1.5 else "✅" if r['ev'] >= 1.0 else "⚠️" if r['ev'] > 0 else "❌"
                lines.append(f"{flt:<24} | {rr_str:<6} | {trd:<8} | {tp_pct:<8} | {sl_pct:<8} | {ev:<8} {tag}")
            lines.append("\n")
            
    final_str = "\n".join(lines)
    print(final_str)
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(final_str)
    print(f"✅ Đã lưu kết quả tại {OUTPUT_FILE}")
    mt5.shutdown()

if __name__ == "__main__":
    main()

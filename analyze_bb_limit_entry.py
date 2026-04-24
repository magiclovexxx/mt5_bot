"""
Phân tích BB Breakout — GOLD (XAUUSD) — MỚI: Limit Entry tại BB ± X%
Strategy: 
1. Tính toán BB_Upper và BB_Lower của nến T-1.
2. Đặt Limit Order: 
   - SELL Limit tại BB_Upper(T-1) * (1 + X/100)
   - BUY Limit tại BB_Lower(T-1) * (1 - X/100)
3. Nếu High/Low của nến T chạm Limit Order, lệnh khớp NGAY LẬP TỨC tại giá Limit.
4. SL/TP tính bằng khoảng cách tuyệt đối từ Entry.
"""

import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf8')

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from ta.volatility import BollingerBands, AverageTrueRange
from src.fetch_data import initialize_mt5

# ══════════════════════════════════════════
# CẤU HÌNH
# ══════════════════════════════════════════
SYMBOL       = "GOLD"
BARS_1Y      = 250 * 24
BB_WINDOW    = 20
BB_STD       = 2
ATR_WINDOW   = 14
FORWARD_BARS = 120

ENTRY_X_PCTS = [0.0, 0.05, 0.1, 0.15, 0.2, 0.3]
RR_RATIOS    = [2, 3]
SL_CONFIGS   = [
    ("ATR", 1.0)
]

OUTPUT_FILE = "results/GOLD_BB_Limit_Entry_Old_Year_Summary.txt"

# ══════════════════════════════════════════
# DATA
# ══════════════════════════════════════════
def load_data(tf, bars):
    # Lấy dữ liệu lùi về trước 'bars' nến (nghĩa là năm trước đó)
    rates = mt5.copy_rates_from_pos(SYMBOL, tf, bars, bars)
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    print(f"  --> Data range: {df.index.min()} to {df.index.max()}")
    return df

def apply_indicators(df):
    bb = BollingerBands(close=df['close'], window=BB_WINDOW, window_dev=BB_STD)
    df['BB_Upper'] = bb.bollinger_hband()
    df['BB_Lower'] = bb.bollinger_lband()
    df['ATR']      = AverageTrueRange(
                         high=df['high'], low=df['low'],
                         close=df['close'], window=ATR_WINDOW).average_true_range()
    
    # Dịch BB và ATR xuống 1 nến để không bị look-ahead bias khi đặt Limit Order
    df['BB_Upper_prev'] = df['BB_Upper'].shift(1)
    df['BB_Lower_prev'] = df['BB_Lower'].shift(1)
    df['ATR_prev']      = df['ATR'].shift(1)
    
    return df.dropna()

def simulate_trade(high_arr, low_arr, start_idx, rev_type, entry_price, sl_dist, rr, forward=FORWARD_BARS):
    if rev_type == 'Đỉnh': # SELL
        sl = entry_price + sl_dist
        tp = entry_price - sl_dist * rr
        
        # Check current candle first
        hit_sl = high_arr[start_idx] >= sl
        hit_tp = low_arr[start_idx] <= tp
        
        if hit_sl: return 'SL'
        if hit_tp: return 'TP'
        
        # Check future candles
        end_idx = min(start_idx + 1 + forward, len(high_arr))
        for i in range(start_idx + 1, end_idx):
            if high_arr[i] >= sl: return 'SL'
            if low_arr[i]  <= tp: return 'TP'
            
    else: # BUY
        sl = entry_price - sl_dist
        tp = entry_price + sl_dist * rr
        
        # Check current candle first
        hit_sl = low_arr[start_idx] <= sl
        hit_tp = high_arr[start_idx] >= tp
        
        if hit_sl: return 'SL'
        if hit_tp: return 'TP'
        
        # Check future candles
        end_idx = min(start_idx + 1 + forward, len(low_arr))
        for i in range(start_idx + 1, end_idx):
            if low_arr[i]  <= sl: return 'SL'
            if high_arr[i] >= tp: return 'TP'
            
    return 'None'

def run_analysis(df, tf_label):
    results = []
    total_candles = len(df)
    
    high_arr = df['high'].values
    low_arr  = df['low'].values
    
    for x_pct in ENTRY_X_PCTS:
        print(f"[{tf_label}] Quét Entry X% = {x_pct}% ...")
        # Pre-calculate entry arrays
        # Lệnh Limit SELL tại BB_Upper_prev * (1 + x%)
        df['Sell_Limit'] = df['BB_Upper_prev'] * (1 + x_pct / 100.0)
        # Lệnh Limit BUY tại BB_Lower_prev * (1 - x%)
        df['Buy_Limit']  = df['BB_Lower_prev'] * (1 - x_pct / 100.0)
        
        # Tìm index các nến khớp lệnh
        sell_mask = df['high'] >= df['Sell_Limit']
        buy_mask  = df['low']  <= df['Buy_Limit']
        
        sell_indices = np.where(sell_mask)[0]
        buy_indices  = np.where(buy_mask)[0]
        
        # Bỏ đi những tín hiệu quá gần cuối (không đủ FORWARD_BARS)
        sell_indices = sell_indices[sell_indices < total_candles - FORWARD_BARS]
        buy_indices  = buy_indices[buy_indices < total_candles - FORWARD_BARS]
        
        for sl_type, sl_val in SL_CONFIGS:
            for rr in RR_RATIOS:
                # ── XỬ LÝ SELL ──
                sell_tp, sell_sl, sell_none = 0, 0, 0
                for idx in sell_indices:
                    row = df.iloc[idx]
                    entry = row['Sell_Limit']
                    atr   = row['ATR_prev']
                    
                    if sl_type == "ATR":
                        sl_dist = atr * sl_val
                    else: # PCT
                        sl_dist = entry * (sl_val / 100.0)
                        
                    res = simulate_trade(high_arr, low_arr, idx, 'Đỉnh', entry, sl_dist, rr, FORWARD_BARS)
                    if res == 'TP': sell_tp += 1
                    elif res == 'SL': sell_sl += 1
                    else: sell_none += 1
                
                sell_total = len(sell_indices)
                if sell_total > 0:
                    ev_sell = (sell_tp / sell_total) * rr - (sell_sl / sell_total)
                    results.append({
                        'tf': tf_label, 'dir': 'SELL', 'x_pct': x_pct,
                        'sl_type': f"{sl_type} {sl_val}", 'rr': f"1:{rr}",
                        'total': sell_total, 'tp_pct': sell_tp / sell_total,
                        'ev': ev_sell
                    })
                
                # ── XỬ LÝ BUY ──
                buy_tp, buy_sl, buy_none = 0, 0, 0
                for idx in buy_indices:
                    row = df.iloc[idx]
                    entry = row['Buy_Limit']
                    atr   = row['ATR_prev']
                    
                    if sl_type == "ATR":
                        sl_dist = atr * sl_val
                    else: # PCT
                        sl_dist = entry * (sl_val / 100.0)
                        
                    res = simulate_trade(high_arr, low_arr, idx, 'Đáy', entry, sl_dist, rr, FORWARD_BARS)
                    if res == 'TP': buy_tp += 1
                    elif res == 'SL': buy_sl += 1
                    else: buy_none += 1
                
                buy_total = len(buy_indices)
                if buy_total > 0:
                    ev_buy = (buy_tp / buy_total) * rr - (buy_sl / buy_total)
                    results.append({
                        'tf': tf_label, 'dir': 'BUY', 'x_pct': x_pct,
                        'sl_type': f"{sl_type} {sl_val}", 'rr': f"1:{rr}",
                        'total': buy_total, 'tp_pct': buy_tp / buy_total,
                        'ev': ev_buy
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
    lines.append("  TỔNG HỢP: LIMIT ENTRY TẠI BB ± X%")
    lines.append("  Mô tả:")
    lines.append("   - Entry SELL = BB_Upper_prev * (1 + X%)")
    lines.append("   - Entry BUY  = BB_Lower_prev * (1 - X%)")
    lines.append("   - Lệnh khớp ngay trong nến nếu giá chạm Limit.")
    lines.append("=========================================================================\n")
    
    for tf_label in ['M15', 'H1']:
        for dr in ['BUY', 'SELL']:
            lines.append(f"── {tf_label} {dr} ───────────────────────────────────────────────")
            sub = final_df[(final_df['tf'] == tf_label) & (final_df['dir'] == dr)]
            # Lọc ra tất cả cấu hình (vì số lượng ít)
            top = sub.sort_values(by='x_pct', ascending=True)
            
            lines.append(f"{'Entry X%':<10} | {'SL Method':<12} | {'R:R':<6} | {'Trades':<8} | {'TP%':<8} | {'SL%':<8} | {'EV (R)':<8}")
            lines.append("-" * 75)
            for _, r in top.iterrows():
                x_str  = f"{r['x_pct']}%"
                sl_str = r['sl_type']
                rr_str = r['rr']
                trd    = f"{int(r['total']):,}"
                tp_pct = f"{r['tp_pct']*100:.1f}%"
                
                # Tính SL%
                sl_pct_val = 1 - r['tp_pct']  # Approximation since none_pct is usually 0
                # Nhưng chính xác hơn ta nên lấy từ result, wait, ta cần lưu sl_pct
                # Hiện tại tôi đã lưu ev và tp_pct, ta sẽ tính ngược sl_pct = sl / total trong result.
                # Tuy nhiên, trong run_analysis đã có: ev = (tp/total)*rr - (sl/total). 
                # Vậy sl/total = (tp/total)*rr - ev
                sl_pct_val = (r['tp_pct'] * float(rr_str.split(':')[1])) - r['ev']
                sl_pct = f"{sl_pct_val*100:.1f}%"
                
                ev     = f"{r['ev']:.3f}"
                
                tag = "🏆" if r['ev'] >= 1.5 else "✅" if r['ev'] >= 1.0 else "⚠️" if r['ev'] > 0 else "❌"
                lines.append(f"{x_str:<10} | {sl_str:<12} | {rr_str:<6} | {trd:<8} | {tp_pct:<8} | {sl_pct:<8} | {ev:<8} {tag}")
            lines.append("\n")
            
    final_str = "\n".join(lines)
    print(final_str)
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(final_str)
    print(f"✅ Đã lưu kết quả tại {OUTPUT_FILE}")
    mt5.shutdown()

if __name__ == "__main__":
    main()

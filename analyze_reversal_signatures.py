import MetaTrader5 as mt5
import pandas as pd
import os
from datetime import datetime, timedelta
from src.fetch_data import initialize_mt5
from src.indicators import apply_indicators
from src.analysis import analyze_volatility_and_reversals

import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf8')

def get_rates_for_window(symbol, tf_str, end_time, count=60):
    timeframe_mapping = {
        "M1": mt5.TIMEFRAME_M1,
        "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15,
        "H1": mt5.TIMEFRAME_H1
    }
    tf = timeframe_mapping.get(tf_str)
    # Lấy dữ liệu lùi lại từ end_time
    rates = mt5.copy_rates_from(symbol, tf, end_time, count)
    if rates is None or len(rates) == 0:
        return None
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    return df

def check_signals(df, reversal_type):
    """
    Kiểm tra xem trong window dữ liệu có các tín hiệu mong muốn không.
    """
    if df is None or len(df) < 30: return {}
    
    # Tính BB trực tiếp
    ma = df['close'].rolling(window=20).mean()
    std = df['close'].rolling(window=20).std()
    df['BB_Upper'] = ma + (std * 2)
    df['BB_Lower'] = ma - (std * 2)
    
    # Tính RSI trực tiếp
    import pandas_ta as ta
    df['RSI_14'] = ta.rsi(df['close'], length=14)
    
    # 1. BB Breakout
    if reversal_type == 'Đỉnh':
        bb_break = (df['high'] > df['BB_Upper']).any()
    else:
        bb_break = (df['low'] < df['BB_Lower']).any()
        
    # 2. Volume Spike
    vol_ma = df['tick_volume'].mean()
    vol_spike = (df['tick_volume'] > 1.5 * vol_ma).any()
    
    # 3. RSI Divergence (Logic đơn giản trong window 60 nến)
    has_div = False
    for i in range(20, len(df)):
        curr_rsi = df.iloc[i]['RSI_14']
        if reversal_type == 'Đỉnh' and curr_rsi > 60:
            prev_window = df.iloc[max(0, i-30):i]
            if not prev_window.empty:
                prev_high = prev_window['high'].max()
                prev_rsi = df.loc[prev_window['high'].idxmax(), 'RSI_14']
                if df.iloc[i]['high'] > prev_high and curr_rsi < prev_rsi:
                    has_div = True; break
        elif reversal_type == 'Đáy' and curr_rsi < 40:
            prev_window = df.iloc[max(0, i-30):i]
            if not prev_window.empty:
                prev_low = prev_window['low'].min()
                prev_rsi = df.loc[prev_window['low'].idxmin(), 'RSI_14']
                if df.iloc[i]['low'] < prev_low and curr_rsi > prev_rsi:
                    has_div = True; break
                    
    return {
        'BB_Break': bb_break,
        'Vol_Spike': vol_spike,
        'RSI_Div': has_div
    }

def main():
    print("Bắt đầu Phân tích 'Dấu vết Đảo chiều' (Deep Dive 60 nến)...")
    symbol = "GOLD"
    initialize_mt5()
    
    # 1. Lấy dữ liệu H1 trong 3 năm
    rates_h1 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 3 * 250 * 24)
    df_h1 = pd.DataFrame(rates_h1)
    df_h1['time'] = pd.to_datetime(df_h1['time'], unit='s')
    df_h1.set_index('time', inplace=True)
    df_h1 = apply_indicators(df_h1)
    
    # 2. Tìm Đỉnh/Đáy ngày trên H1
    df_h1['Date'] = df_h1.index.date
    reversals = []
    for date, group in df_h1.groupby('Date'):
        if len(group) < 12: continue
        top_idx = group['high'].idxmax()
        bot_idx = group['low'].idxmin()
        reversals.append({'time': top_idx, 'type': 'Đỉnh'})
        reversals.append({'time': bot_idx, 'type': 'Đáy'})
        
    print(f"Tìm thấy {len(reversals)} điểm đảo chiều H1 (trong 3 năm). Đang truy vết M1, M5, M15...")
    
    results = {
        'M1': {'BB': 0, 'Vol': 0, 'Div': 0, 'Total': 0},
        'M5': {'BB': 0, 'Vol': 0, 'Div': 0, 'Total': 0},
        'M15': {'BB': 0, 'Vol': 0, 'Div': 0, 'Total': 0}
    }
    
    count = 0
    for rev in reversals:
        count += 1
        if count % 20 == 0: print(f"Đã xử lý {count}/{len(reversals)} điểm...")
        
        for tf in ['M1', 'M5', 'M15']:
            df_tf = get_rates_for_window(symbol, tf, rev['time'], 60)
            signals = check_signals(df_tf, rev['type'])
            
            if signals:
                results[tf]['Total'] += 1
                if signals['BB_Break']: results[tf]['BB'] += 1
                if signals['Vol_Spike']: results[tf]['Vol'] += 1
                if signals['RSI_Div']: results[tf]['Div'] += 1
                
    # 3. Xuất kết quả
    report = []
    report.append("=== PHÂN TÍCH DẤU VẾT ĐẢO CHIỀU (TRƯỚC KHI ĐẠT ĐỈNH/ĐÁY H1) ===")
    report.append(f"Dữ liệu: 3 năm H1. Tổng số điểm kiểm tra: {len(reversals)}")
    report.append("Phương pháp: Lấy 60 nến của khung nhỏ TRƯỚC thời điểm H1 đảo chiều để soi dấu hiệu.")
    
    for tf, data in results.items():
        if data['Total'] == 0: continue
        report.append(f"\n--- KHUNG {tf} ---")
        report.append(f" - Tỉ lệ xuất hiện Phân kỳ RSI: {round(data['Div']/data['Total']*100, 2)}%")
        report.append(f" - Tỉ lệ giá vỡ dải Bollinger Band: {round(data['BB']/data['Total']*100, 2)}%")
        report.append(f" - Tỉ lệ có Volume đột biến: {round(data['Vol']/data['Total']*100, 2)}%")
        
    final_report = "\n".join(report)
    print("\n" + final_report)
    
    with open("results/GOLD_Reversal_Signatures.txt", "w", encoding="utf-8") as f:
        f.write(final_report)
        
    mt5.shutdown()

if __name__ == "__main__":
    main()

import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta
import os

def initialize_mt5():
    if not mt5.initialize():
        print("initialize() failed, error code =", mt5.last_error())
        quit()
    print("MT5 initialized successfully.")

def fetch_data(symbol, timeframe_str, years=2):
    timeframe_mapping = {
        "M1": mt5.TIMEFRAME_M1,
        "M15": mt5.TIMEFRAME_M15,
        "H1": mt5.TIMEFRAME_H1,
        "H4": mt5.TIMEFRAME_H4,
        "D1": mt5.TIMEFRAME_D1
    }
    
    tf = timeframe_mapping.get(timeframe_str)
    if not tf:
        print(f"Timeframe {timeframe_str} not supported.")
        return None

    # Calculate number of bars for 2 years
    # Rough estimate: 250 trading days/year
    if timeframe_str == "M1":
        num_bars = 40000 # Khoảng 1 tháng dữ liệu M1 để tránh lỗi giới hạn
    elif timeframe_str == "M15":
        num_bars = 2 * 250 * 24 * 4
    elif timeframe_str == "H1":
        num_bars = 2 * 250 * 24
    elif timeframe_str == "H4":
        num_bars = 2 * 250 * 6
    else: # D1
        num_bars = 2 * 250

    print(f"Fetching {num_bars} bars for {symbol} on {timeframe_str}...")
    
    # Đảm bảo symbol hiển thị trong Market Watch trước khi lấy dữ liệu
    if not mt5.symbol_select(symbol, True):
        print(f"Failed to select {symbol} in Market Watch. Kiểm tra lại tên mã giao dịch trên sàn của bạn.")
        return None

    rates = mt5.copy_rates_from_pos(symbol, tf, 0, num_bars)
    
    if rates is None or len(rates) == 0:
        print(f"Failed to fetch data for {symbol}.")
        return None
        
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    
    # Save to CSV
    os.makedirs('data', exist_ok=True)
    file_path = f"data/{symbol}_{timeframe_str}.csv"
    df.to_csv(file_path)
    print(f"Saved to {file_path}")
    return df

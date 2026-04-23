import MetaTrader5 as mt5
import pandas as pd
import pandas_ta as ta
import sys
import io
from src.fetch_data import initialize_mt5
from src.indicators import apply_indicators
from src.backtest_engine import BacktestEngine

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf8')

def fetch_history(symbol, tf_str, years=1):
    timeframe_mapping = {
        "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15,
        "H1": mt5.TIMEFRAME_H1
    }
    tf = timeframe_mapping[tf_str]
    # Lấy khoảng 1 năm dữ liệu
    num_bars = years * 250 * 24 * (60 // int(tf_str[1:])) if tf_str != "H1" else years * 250 * 24
    
    print(f"Đang lấy {num_bars} nến {tf_str} cho {symbol}...")
    rates = mt5.copy_rates_from_pos(symbol, tf, 0, int(num_bars))
    if rates is None: return None
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    return df

def main():
    symbol = "GOLD"
    initialize_mt5()
    
    # 1. Fetch dữ liệu
    df_h1 = fetch_history(symbol, "H1")
    df_m15 = fetch_history(symbol, "M15")
    df_m5 = fetch_history(symbol, "M5")
    
    if df_h1 is None or df_m5 is None:
        print("Không lấy được dữ liệu.")
        return

    # 2. Chuẩn bị Indicators
    print("Đang tính toán chỉ báo...")
    df_h1 = apply_indicators(df_h1)
    df_m5['RSI_14'] = ta.rsi(df_m5['close'], length=14)
    
    # 3. Chạy Backtest
    engine = BacktestEngine(df_m5, df_m15, df_h1)
    results = engine.run()
    
    print("\n" + results)
    
    with open("results/GOLD_Backtest_Report.txt", "w", encoding="utf-8") as f:
        f.write(results)
        
    mt5.shutdown()

if __name__ == "__main__":
    main()

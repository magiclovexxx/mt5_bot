import os
import MetaTrader5 as mt5
import pandas as pd
from src.fetch_data import initialize_mt5, fetch_data
from src.indicators import apply_indicators
from src.analysis import analyze_volatility_and_reversals

def main():
    print("Starting MT5 Analyzer...")
    
    # 1. Configuration
    symbols = ["EURUSD", "GOLD"] # Danh sách các cặp tiền cần lấy dữ liệu
    timeframes = ["M1", "M15", "H1"] # Bạn có thể thay đổi khung thời gian
    
    # Ensure directories exist
    os.makedirs('data', exist_ok=True)
    os.makedirs('results', exist_ok=True)
    
    # 2. Fetch Data
    initialize_mt5()
    
    for symbol in symbols:
        for tf in timeframes:
            print(f"\n--- Processing {symbol} on {tf} ---")
            df = fetch_data(symbol, tf, years=2)
            
            if df is None or df.empty:
                continue
                
            # 3. Apply Indicators
            print(f"Calculating Indicators (BB, RSI, EMA, ATR) for {symbol} - {tf}...")
            df = apply_indicators(df)
            
            # 4. Analyze
            print(f"Finding High Volatility and Reversal points for {symbol} - {tf}...")
            full_df, summary_df = analyze_volatility_and_reversals(df)
            
            # 5. Save Results
            if not summary_df.empty:
                result_file = f"results/{symbol}_{tf}_reversals.csv"
                summary_df.to_csv(result_file, index=False)
                print(f"Found {len(summary_df)} reversal points. Saved summary to {result_file}")
                
                # Print a quick sample
                print("\nSample Reversals:")
                print(summary_df.tail(5).to_string())
            else:
                print(f"No reversals found (or not enough data) for {symbol} - {tf}.")

    mt5.shutdown()
    print("\nDone!")

if __name__ == "__main__":
    main()

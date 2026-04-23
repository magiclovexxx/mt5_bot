import os
import sys
import io
import MetaTrader5 as mt5
import pandas as pd
from src.fetch_data import initialize_mt5, fetch_data
from src.indicators import apply_indicators
from src.cross_timeframe import (
    analyze_cross_timeframe_reversals, 
    analyze_h1_cross_timeframe,
    generate_trading_strategy_guide
)

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf8')

def main():
    print("Bắt đầu Phân tích Chiến lược GOLD...")
    symbol = "GOLD" 
    os.makedirs('results', exist_ok=True)
    initialize_mt5()
    
    # Fetch & Prepare Data
    df_m1 = apply_indicators(fetch_data(symbol, "M1"))
    df_m15 = apply_indicators(fetch_data(symbol, "M15"))
    df_h1 = apply_indicators(fetch_data(symbol, "H1"))
    
    if df_m1 is None or df_m15 is None or df_h1 is None:
        mt5.shutdown()
        return

    # Analyze
    cross_df_m15 = analyze_cross_timeframe_reversals(df_m15, df_m1, df_h1, symbol)
    cross_df_h1 = analyze_h1_cross_timeframe(df_h1, df_m15, df_m1, symbol)
    
    # Generate Strategy Guide
    strategy_guide = generate_trading_strategy_guide(cross_df_m15, cross_df_h1)
    
    print("\n" + strategy_guide)
    
    # Save results
    with open(f"results/{symbol}_Trading_Strategy.txt", "w", encoding="utf-8") as f:
        f.write(strategy_guide)
        
    if not cross_df_m15.empty:
        cross_df_m15.to_csv(f"results/{symbol}_Detailed_M15.csv", index=False)
    if not cross_df_h1.empty:
        cross_df_h1.to_csv(f"results/{symbol}_Detailed_H1.csv", index=False)
        
    print(f"\nĐã xuất chiến lược vào results/{symbol}_Trading_Strategy.txt")
    mt5.shutdown()

if __name__ == "__main__":
    main()

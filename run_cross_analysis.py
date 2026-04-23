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
from src.analysis import analyze_volatility_and_reversals
from src.reversal_probability import calculate_signal_probabilities, format_probability_report

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

    # 1. Phân tích xác suất (Phần mới)
    print("Đang tính toán xác suất đảo chiều cho các tín hiệu...")
    df_m1_processed, _ = analyze_volatility_and_reversals(df_m1)
    df_m15_processed, _ = analyze_volatility_and_reversals(df_m15)
    df_h1_processed, _ = analyze_volatility_and_reversals(df_h1)
    
    prob_m1 = calculate_signal_probabilities(df_m1_processed)
    prob_m15 = calculate_signal_probabilities(df_m15_processed)
    prob_h1 = calculate_signal_probabilities(df_h1_processed)
    
    prob_report_m1 = format_probability_report(prob_m1, "M1")
    prob_report_m15 = format_probability_report(prob_m15, "M15")
    prob_report_h1 = format_probability_report(prob_h1, "H1")

    # 2. Analyze Cross-Timeframe
    cross_df_m15 = analyze_cross_timeframe_reversals(df_m15, df_m1, df_h1, symbol)
    cross_df_h1 = analyze_h1_cross_timeframe(df_h1, df_m15, df_m1, symbol)
    
    # 3. Generate Strategy Guide
    strategy_guide = generate_trading_strategy_guide(cross_df_m15, cross_df_h1)
    
    print("\n" + strategy_guide)
    
    # Save Strategy Guide
    with open(f"results/{symbol}_Trading_Strategy.txt", "w", encoding="utf-8") as f:
        f.write(strategy_guide)
    
    # Update Statistics Report (Bổ sung vào file GOLD_Cross_Statistics.txt)
    stats_file = f"results/{symbol}_Cross_Statistics.txt"
    with open(stats_file, "a", encoding="utf-8") as f:
        f.write("\n\n" + "="*50)
        f.write("\nPHẦN BỔ SUNG: PHÂN TÍCH XÁC SUẤT M1 (Dành cho Scalping)")
        f.write("\n" + "="*50)
        f.write("\n" + prob_report_m1)
        f.write("\n" + prob_report_m15)
        f.write("\n" + prob_report_h1)
        
    if not cross_df_m15.empty:
        cross_df_m15.to_csv(f"results/{symbol}_Detailed_M15.csv", index=False)
    if not cross_df_h1.empty:
        cross_df_h1.to_csv(f"results/{symbol}_Detailed_H1.csv", index=False)
        
    print(f"\nĐã cập nhật xác suất vào {stats_file}")
    print(f"Đã xuất chiến lược vào results/{symbol}_Trading_Strategy.txt")
    mt5.shutdown()

if __name__ == "__main__":
    main()

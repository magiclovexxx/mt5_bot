import os
import sys
import io
import MetaTrader5 as mt5
import pandas as pd
from src.fetch_data import initialize_mt5, fetch_data
from src.indicators import apply_indicators
from src.cross_timeframe import analyze_cross_timeframe_reversals, generate_reversal_statistics

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf8')

def main():
    print("Bắt đầu Cross-Timeframe Analyzer...")
    
    symbol = "GOLD" 
    
    os.makedirs('data', exist_ok=True)
    os.makedirs('results', exist_ok=True)
    
    initialize_mt5()
    
    # 1. Fetch M1 và M15
    print(f"\n--- Fetching {symbol} M1 (Khoảng 1 tháng) ---")
    df_m1 = fetch_data(symbol, "M1")
    
    print(f"\n--- Fetching {symbol} M15 (2 năm) ---")
    df_m15 = fetch_data(symbol, "M15")
    
    if df_m1 is None or df_m15 is None or df_m1.empty or df_m15.empty:
        print("Lỗi không lấy được đủ dữ liệu M1 hoặc M15.")
        mt5.shutdown()
        return
        
    # 2. Tính toán chỉ báo
    print("\nĐang tính toán các chỉ báo cho M1...")
    df_m1 = apply_indicators(df_m1)
    
    print("Đang tính toán các chỉ báo cho M15...")
    df_m15 = apply_indicators(df_m15)
    
    # 3. Phân tích chéo
    print("\nThực hiện phân tích chéo điểm đảo chiều M15 và kiểm tra RSI trên M1...")
    cross_df = analyze_cross_timeframe_reversals(df_m15, df_m1, symbol)
    
    # 4. Lưu và in kết quả
    if not cross_df.empty:
        result_file = f"results/{symbol}_Cross_M15_M1_reversals.csv"
        cross_df.to_csv(result_file, index=False)
        print(f"\nĐã lưu {len(cross_df)} điểm đảo chiều kèm dữ liệu chéo vào {result_file}")
        
        # Tạo thống kê
        stats = generate_reversal_statistics(cross_df)
        print("\n" + stats)
        
        # Ghi thống kê ra file text
        with open(f"results/{symbol}_Cross_Statistics.txt", "w", encoding="utf-8") as f:
            f.write(stats)
            
    else:
        print("Không có điểm đảo chiều hoặc lỗi phân tích.")

    mt5.shutdown()

if __name__ == "__main__":
    main()

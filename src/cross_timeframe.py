import pandas as pd
from datetime import timedelta

def analyze_cross_timeframe_reversals(df_m15, df_m1, df_h1, symbol):
    from src.analysis import analyze_volatility_and_reversals
    print(f"Bắt đầu phân tích chéo cho {symbol} trên khung M15...")
    df_m15_full, summary_m15 = analyze_volatility_and_reversals(df_m15)
    
    if summary_m15.empty: return pd.DataFrame()
        
    cross_results = []
    for _, row in summary_m15.iterrows():
        m15_time = row['Time']
        reversal_type = row['Type']
        end_time = m15_time + timedelta(minutes=14)
        m1_window = df_m1[(df_m1.index >= m15_time) & (df_m1.index <= end_time)]
        if m1_window.empty: continue
            
        m1_rsi_min = m1_window['RSI_14'].min()
        m1_rsi_max = m1_window['RSI_14'].max()
        
        hour = m15_time.hour
        if 0 <= hour < 8: session = "Asian Session (00:00-08:00)"
        elif 8 <= hour < 15: session = "London Session (08:00-15:00)"
        else: session = "NY Session (15:00-24:00)"
            
        cross_results.append({
            'Time': m15_time,
            'Hour': hour,
            'Session': session,
            'Type': reversal_type,
            'Close_Price': row['Close_Price'],
            'Base_RSI': row['RSI'],
            'STOCH_K': row['STOCH_K'],
            'M1_RSI_Extreme': m1_rsi_min if reversal_type == 'Đáy' else m1_rsi_max,
            'RR_Ratio': row['RR_Ratio'],
            'Risk': row['Risk'],
            'Max_Reward': row['Max_Reward'],
            'Volume_Spike': row['Volume_Spike'],
            'Pattern': row['Pattern'],
            'Divergence': row['Divergence'],
            'Near_SR': row['Near_SR']
        })
    return pd.DataFrame(cross_results)

def analyze_h1_cross_timeframe(df_h1, df_m15, df_m1, symbol):
    from src.analysis import analyze_volatility_and_reversals
    print(f"Bắt đầu phân tích chéo cho {symbol} trên khung H1...")
    df_h1_full, summary_h1 = analyze_volatility_and_reversals(df_h1)
    
    if summary_h1.empty: return pd.DataFrame()
        
    cross_results = []
    for _, row in summary_h1.iterrows():
        h1_time = row['Time']
        reversal_type = row['Type']
        end_time = h1_time + timedelta(minutes=59)
        m1_window = df_m1[(df_m1.index >= h1_time) & (df_m1.index <= end_time)]
        
        m1_rsi_min = m1_window['RSI_14'].min() if not m1_window.empty else None
        m1_rsi_max = m1_window['RSI_14'].max() if not m1_window.empty else None
        
        hour = h1_time.hour
        if 0 <= hour < 8: session = "Asian Session (00:00-08:00)"
        elif 8 <= hour < 15: session = "London Session (08:00-15:00)"
        else: session = "NY Session (15:00-24:00)"
            
        cross_results.append({
            'Time': h1_time,
            'Hour': hour,
            'Session': session,
            'Type': reversal_type,
            'Close_Price': row['Close_Price'],
            'Base_RSI': row['RSI'],
            'STOCH_K': row['STOCH_K'],
            'M1_RSI_Extreme': m1_rsi_min if reversal_type == 'Đáy' else m1_rsi_max,
            'RR_Ratio': row['RR_Ratio'],
            'Risk': row['Risk'],
            'Max_Reward': row['Max_Reward'],
            'Volume_Spike': row['Volume_Spike'],
            'Pattern': row['Pattern'],
            'Divergence': row['Divergence'],
            'Near_SR': row['Near_SR']
        })
    return pd.DataFrame(cross_results)

def generate_trading_strategy_guide(df_m15, df_h1):
    if df_m15.empty and df_h1.empty: return "Không có dữ liệu."
    df = df_h1 if not df_h1.empty else df_m15
    total = len(df)
    
    stats = []
    stats.append("================================================================")
    stats.append("   BẢN TỔNG HỢP CHIẾN LƯỢC BẮT ĐỈNH/ĐÁY GOLD (DỰA TRÊN THỐNG KÊ)")
    stats.append("================================================================\n")
    
    # 1. Hiệu quả R:R
    avg_rr = df['RR_Ratio'].mean()
    win_rate_1_1 = len(df[df['RR_Ratio'] >= 1.0]) / total * 100
    win_rate_1_2 = len(df[df['RR_Ratio'] >= 2.0]) / total * 100
    
    stats.append(f"1. PHÂN TÍCH TỈ LỆ R:R (RISK/REWARD):")
    stats.append(f" - Tỉ lệ R:R trung bình tiềm năng: 1:{round(avg_rr, 2)}")
    stats.append(f" - Xác suất đạt R:R 1:1: {round(win_rate_1_1, 2)}%")
    stats.append(f" - Xác suất đạt R:R 1:2: {round(win_rate_1_2, 2)}%")
    stats.append(f" - Nhận xét: Với tỉ lệ thắng R:R 1:1 trên {round(win_rate_1_1, 2)}%, hệ thống có kỳ vọng dương.")

    # 2. Vùng giá quan trọng
    sr_hits = len(df[df['Near_SR'] != 'None'])
    stats.append(f"\n2. VÙNG GIÁ QUAN TRỌNG (SUPPORT/RESISTANCE):")
    stats.append(f" - Tỷ lệ đảo chiều tại các mức Pivot: {sr_hits} lần ({round(sr_hits/total*100, 2)}%)")

    # 3. Tín hiệu đồng thuận
    stats.append(f"\n3. CÁC TÍN HIỆU ĐỒNG THUẬN (CONFLUENCE):")
    stats.append(f" - Phân kỳ RSI: {round(len(df[df['Divergence'] != 'None'])/total*100, 2)}%")
    stats.append(f" - Khối lượng đột biến: {round(len(df[df['Volume_Spike'] == True])/total*100, 2)}%")
    stats.append(f" - Nến Pin Bar/Engulfing: {round(len(df[df['Pattern'] != 'None'])/total*100, 2)}%")

    # 4. Checklist & Timing
    stats.append("\n4. BỘ QUY TẮC VÀNG & TIMING:")
    stats.append(" - Ưu tiên khung giờ: 22:00, 01:00, 17:00.")
    stats.append(" - SL: Đặt dưới đáy/trên đỉnh + ATR * 0.5.")
    stats.append(" - TP: Tối thiểu 1:1.5 hoặc tại các mức Pivot kế tiếp.")
    
    return "\n".join(stats)

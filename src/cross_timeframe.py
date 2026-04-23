import pandas as pd
from datetime import timedelta

def analyze_cross_timeframe_reversals(df_m15, df_m1, symbol):
    """
    Phân tích chéo khung thời gian: Tìm điểm đảo chiều trên M15 và xem xét RSI trên M1,
    cũng như thống kê các khoảng thời gian và ATR.
    """
    from src.analysis import analyze_volatility_and_reversals
    
    print(f"Bắt đầu phân tích chéo cho {symbol}...")
    # 1. Tìm các điểm đảo chiều trên M15
    df_m15_full, summary_m15 = analyze_volatility_and_reversals(df_m15)
    
    if summary_m15.empty:
        print("Không tìm thấy điểm đảo chiều nào trên M15.")
        return pd.DataFrame()
        
    cross_results = []
    
    for _, row in summary_m15.iterrows():
        m15_time = row['Time']
        reversal_type = row['Type']
        
        # Cây nến M15 bắt đầu từ m15_time và kết thúc trước m15_time + 15 phút
        end_time = m15_time + timedelta(minutes=14)
        
        # Lấy các nến M1 trong khoảng 15 phút này
        m1_window = df_m1[(df_m1.index >= m15_time) & (df_m1.index <= end_time)]
        
        if m1_window.empty:
            continue
            
        # Lấy RSI của M1 trong khoảng 15 phút này (thấp nhất và cao nhất)
        m1_rsi_min = m1_window['RSI_14'].min()
        m1_rsi_max = m1_window['RSI_14'].max()
        m1_rsi_close = m1_window['RSI_14'].iloc[-1] # RSI tại thời điểm đóng nến M15
        
        # Lấy ATR của M1
        m1_atr_max = m1_window['ATR_14'].max() if 'ATR_14' in m1_window.columns else None
        
        # Phân loại khoảng thời gian (Giờ)
        hour = m15_time.hour
        if 0 <= hour < 8:
            session = "Asian Session (00:00-08:00)"
        elif 8 <= hour < 15:
            session = "London Session (08:00-15:00)"
        else:
            session = "NY Session (15:00-24:00)"
            
        # --- Tính toán độ lệch (breakout) khỏi Bollinger Bands ---
        
        # 1. Tính BB breakout cho M15
        m15_bb_lower = row['BB_Lower']
        m15_bb_upper = row['BB_Upper']
        m15_close = row['Close_Price']
        
        m15_low = row['low'] if 'low' in row else m15_close
        m15_high = row['high'] if 'high' in row else m15_close
        
        m15_bb_breakout_percent = 0.0
        if reversal_type == 'Bullish Reversal (Daily Valley)' and pd.notnull(m15_bb_lower):
            # Nếu giá Low M15 thấp hơn BB Lower, tính % vượt mức
            if m15_low < m15_bb_lower:
                m15_bb_breakout_percent = ((m15_bb_lower - m15_low) / m15_bb_lower) * 100
        elif reversal_type == 'Bearish Reversal (Daily Peak)' and pd.notnull(m15_bb_upper):
            # Nếu giá High M15 cao hơn BB Upper, tính % vượt mức
            if m15_high > m15_bb_upper:
                m15_bb_breakout_percent = ((m15_high - m15_bb_upper) / m15_bb_upper) * 100
                
        # 2. Tính BB breakout lớn nhất cho M1 (trong cùng khung 15 phút)
        m1_bb_breakout_percent = 0.0
        if not m1_window.empty and 'BB_Lower' in m1_window.columns and 'BB_Upper' in m1_window.columns:
            if reversal_type == 'Bullish Reversal (Daily Valley)':
                # Tìm nến M1 đâm sâu nhất xuống dưới BB Lower (tính theo giá Low)
                m1_breakouts = m1_window[m1_window['low'] < m1_window['BB_Lower']]
                if not m1_breakouts.empty:
                    # Tính % cho các điểm đâm vỡ, sau đó lấy điểm đâm sâu nhất
                    breakout_pcts = ((m1_breakouts['BB_Lower'] - m1_breakouts['low']) / m1_breakouts['BB_Lower']) * 100
                    m1_bb_breakout_percent = breakout_pcts.max()
                    
            elif reversal_type == 'Bearish Reversal (Daily Peak)':
                # Tìm nến M1 đâm mạnh nhất lên trên BB Upper (tính theo giá High)
                m1_breakouts = m1_window[m1_window['high'] > m1_window['BB_Upper']]
                if not m1_breakouts.empty:
                    breakout_pcts = ((m1_breakouts['high'] - m1_breakouts['BB_Upper']) / m1_breakouts['BB_Upper']) * 100
                    m1_bb_breakout_percent = breakout_pcts.max()
                    
        cross_results.append({
            'Time_M15': m15_time,
            'Hour': hour,
            'Session': session,
            'Type': reversal_type,
            'Close_Price': m15_close,
            'M15_RSI': row['RSI'],
            'M1_RSI_Min': round(m1_rsi_min, 2) if pd.notnull(m1_rsi_min) else None,
            'M1_RSI_Max': round(m1_rsi_max, 2) if pd.notnull(m1_rsi_max) else None,
            'M1_RSI_Close': round(m1_rsi_close, 2) if pd.notnull(m1_rsi_close) else None,
            'M15_ATR': row.get('ATR', None),
            'M1_ATR_Max': round(m1_atr_max, 5) if pd.notnull(m1_atr_max) else None,
            'M15_ATR_High_Volatility': row['High_Volatility'],
            'M15_BB_Lower': m15_bb_lower,
            'M15_BB_Upper': m15_bb_upper,
            'M15_BB_Breakout_%': round(m15_bb_breakout_percent, 3),
            'M1_Max_BB_Breakout_%': round(m1_bb_breakout_percent, 3)
        })
        
    cross_df = pd.DataFrame(cross_results)
    
    return cross_df

def generate_reversal_statistics(cross_df):
    """
    Liệt kê các khoảng RSI, khoảng thời gian xác suất đảo chiều xảy ra nhiều, ATR cao
    """
    if cross_df.empty:
        return ""
        
    stats_output = []
    stats_output.append("=== THỐNG KÊ ĐIỂM ĐẢO CHIỀU (M15 kết hợp M1) ===")
    
    # Tổng số điểm đảo chiều
    total = len(cross_df)
    bullish = len(cross_df[cross_df['Type'] == 'Bullish Reversal (Daily Valley)'])
    bearish = len(cross_df[cross_df['Type'] == 'Bearish Reversal (Daily Peak)'])
    stats_output.append(f"\nTổng số điểm đảo chiều M15 trong ngày: {total} (Tăng: {bullish}, Giảm: {bearish})")
    
    # 1. Khoảng thời gian dễ xảy ra đảo chiều nhất
    stats_output.append("\n1. XÁC SUẤT ĐẢO CHIỀU THEO PHIÊN (SESSION):")
    session_counts = cross_df['Session'].value_counts()
    for session, count in session_counts.items():
        stats_output.append(f" - {session}: {count} lần ({round(count/total*100, 2)}%)")
        
    stats_output.append("\n2. KHUNG GIỜ CỤ THỂ XẢY RA NHIỀU NHẤT (Top 5):")
    hour_counts = cross_df['Hour'].value_counts().head(5)
    for hour, count in hour_counts.items():
        stats_output.append(f" - {hour}:00 - {hour}:59 : {count} lần ({round(count/total*100, 2)}%)")
        
    # 2. Khoảng RSI M15 khi đảo chiều
    bullish_df = cross_df[cross_df['Type'] == 'Bullish Reversal (Daily Valley)']
    bearish_df = cross_df[cross_df['Type'] == 'Bearish Reversal (Daily Peak)']
    
    stats_output.append("\n3. RSI M15 KHI ĐẢO CHIỀU TĂNG (Bắt đáy):")
    stats_output.append(f" - RSI M15 trung bình: {round(bullish_df['M15_RSI'].mean(), 2)}")
    stats_output.append(f" - Phổ biến nhất (75% trường hợp) RSI M15 rơi vào khoảng: {round(bullish_df['M15_RSI'].quantile(0.1), 2)} đến {round(bullish_df['M15_RSI'].quantile(0.85), 2)}")
    
    stats_output.append("\n4. RSI M1 KHI ĐẢO CHIỀU TĂNG (Timing ở khung nhỏ):")
    stats_output.append(f" - RSI M1 Min trung bình trong vùng nến M15: {round(bullish_df['M1_RSI_Min'].mean(), 2)}")
    stats_output.append(f" - (Điều này cho thấy ở khung M1, RSI thường bị đẩy xuống cực thấp trước khi rút chân tăng)")
    
    stats_output.append("\n5. RSI M15 KHI ĐẢO CHIỀU GIẢM (Bắt đỉnh):")
    stats_output.append(f" - RSI M15 trung bình: {round(bearish_df['M15_RSI'].mean(), 2)}")
    stats_output.append(f" - Phổ biến nhất (75% trường hợp) RSI M15 rơi vào khoảng: {round(bearish_df['M15_RSI'].quantile(0.15), 2)} đến {round(bearish_df['M15_RSI'].quantile(0.9), 2)}")
    
    stats_output.append("\n6. RSI M1 KHI ĐẢO CHIỀU GIẢM:")
    stats_output.append(f" - RSI M1 Max trung bình trong vùng nến M15: {round(bearish_df['M1_RSI_Max'].mean(), 2)}")
    
    # 3. Yếu tố Volatility (ATR cao)
    high_vol = len(cross_df[cross_df['M15_ATR_High_Volatility'] == True])
    stats_output.append("\n7. ĐỘ BIẾN ĐỘNG (VOLATILITY / ATR):")
    stats_output.append(f" - Số điểm đảo chiều đi kèm với mức ATR tăng đột biến (Cao hơn 1.5x trung bình): {high_vol} lần ({round(high_vol/total*100, 2)}%)")
    if high_vol/total < 0.3:
        stats_output.append(" - Nhận xét: Phần lớn các điểm đảo chiều diễn ra trong lúc thị trường có độ biến động bình thường (sideway/ít tin tức).")
    else:
        stats_output.append(" - Nhận xét: Có một lượng đáng kể các cú đảo chiều là những cú rũ (sweep) mạnh với độ biến động cực cao.")
        
    # 4. Yếu tố Bollinger Bands (BB) Breakout
    stats_output.append("\n8. BOLLINGER BANDS (BB) BREAKOUT KHI ĐẢO CHIỀU:")
    
    # Lọc ra các điểm có vỡ band (Breakout % > 0)
    m15_bb_breakouts = cross_df[cross_df['M15_BB_Breakout_%'] > 0]
    m1_bb_breakouts = cross_df[cross_df['M1_Max_BB_Breakout_%'] > 0]
    
    stats_output.append(f" - Số lần đảo chiều xảy ra khi giá M15 đang đóng NẰM NGOÀI BB: {len(m15_bb_breakouts)} lần ({round(len(m15_bb_breakouts)/total*100, 2)}%)")
    if not m15_bb_breakouts.empty:
        stats_output.append(f"   + Trung bình giá M15 vỡ khỏi Band: {round(m15_bb_breakouts['M15_BB_Breakout_%'].mean(), 3)}%")
        stats_output.append(f"   + Lớn nhất từng ghi nhận: {round(m15_bb_breakouts['M15_BB_Breakout_%'].max(), 3)}%")
        
    stats_output.append(f" - Số lần ở khung M1 (nến timing) đâm VỠ RA NGOÀI BB trước khi rút chân: {len(m1_bb_breakouts)} lần ({round(len(m1_bb_breakouts)/total*100, 2)}%)")
    if not m1_bb_breakouts.empty:
        stats_output.append(f"   + Trung bình giá M1 đâm sâu/thủng Band: {round(m1_bb_breakouts['M1_Max_BB_Breakout_%'].mean(), 3)}%")
        stats_output.append(f"   + Lớn nhất từng ghi nhận (thường là Spike/Tin tức): {round(m1_bb_breakouts['M1_Max_BB_Breakout_%'].max(), 3)}%")
    
    return "\n".join(stats_output)

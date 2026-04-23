import pandas as pd

def calculate_signal_probabilities(df):
    """
    Tính toán xác suất đảo chiều khi có tín hiệu cụ thể.
    Xác suất = (Số lần có tín hiệu VÀ có đảo chiều) / (Tổng số lần có tín hiệu)
    """
    if df.empty:
        return {}

    # Định nghĩa các tín hiệu (đồng bộ với src/analysis.py)
    signals = {
        'Volume Spike': df['Volume_Spike'],
        'RSI Divergence': df['RSI_Div'] != 'None',
        'Pin Bar': df['Is_PinBar'],
        'Engulfing': df['Is_Bullish_Engulfing'] | df['Is_Bearish_Engulfing'],
        'Bollinger Bands Breakout': (df['low'] < df['BB_Lower']) | (df['high'] > df['BB_Upper'])
    }

    results = {}
    is_reversal = df['Reversal_Type'] != 'None'

    for name, condition in signals.items():
        total_signals = condition.sum()
        if total_signals > 0:
            successful_reversals = (condition & is_reversal).sum()
            probability = (successful_reversals / total_signals) * 100
            
            # Tính toán delta cho phân kỳ (nếu là RSI Divergence)
            avg_price_diff = 0
            avg_rsi_diff = 0
            if name == 'RSI Divergence':
                div_data = df[condition]
                avg_price_diff = div_data['Div_Price_Diff'].mean()
                avg_rsi_diff = div_data['Div_RSI_Diff'].mean()
                
            results[name] = {
                'total': int(total_signals),
                'success': int(successful_reversals),
                'prob': round(probability, 2),
                'avg_price_diff': round(avg_price_diff, 2),
                'avg_rsi_diff': round(avg_rsi_diff, 2)
            }
        else:
            results[name] = {'total': 0, 'success': 0, 'prob': 0.0, 'avg_price_diff': 0, 'avg_rsi_diff': 0}

    return results

def format_probability_report(probs, timeframe_name):
    """
    Định dạng kết quả thành chuỗi văn bản để bổ sung vào báo cáo.
    """
    lines = []
    lines.append(f"\n=== XÁC SUẤT ĐẢO CHIỀU KHI CÓ TÍN HIỆU ({timeframe_name}) ===")
    lines.append("Công thức: P(Đảo chiều | Tín hiệu) - Nếu tín hiệu xuất hiện, bao nhiêu % sẽ là đỉnh/đáy ngày.")
    
    for signal, data in probs.items():
        suffix = ""
        if signal == 'RSI Divergence' and data['total'] > 0:
            suffix = f" (Khoảng cách giá TB: {data['avg_price_diff']}, RSI Delta TB: {data['avg_rsi_diff']})"
        
        lines.append(f" - {signal}: {data['prob']}% (Thành công {data['success']}/{data['total']} lần xuất hiện){suffix}")
    
    return "\n".join(lines)

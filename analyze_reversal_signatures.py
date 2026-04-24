import MetaTrader5 as mt5
import pandas as pd
import os
from datetime import datetime, timedelta
from src.fetch_data import initialize_mt5
# from src.indicators import apply_indicators (Xóa phụ thuộc)
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
    Kiểm tra và tính toán các thông số chi tiết của tín hiệu trong window.
    """
    if df is None or len(df) < 30: return {}
    
    # Tính RSI và BB bằng thư viện 'ta' (nhanh và chuẩn)
    from ta.momentum import RSIIndicator
    from ta.volatility import BollingerBands
    
    df['RSI_14'] = RSIIndicator(close=df['close'], window=14).rsi()
    
    bb = BollingerBands(close=df['close'], window=20, window_dev=2)
    df['BB_Upper'] = bb.bollinger_hband()
    df['BB_Lower'] = bb.bollinger_lband()
    
    # 1. BB Breakout Metrics
    bb_break_pcts = []
    if reversal_type == 'Đỉnh':
        breaks = df[df['high'] > df['BB_Upper']]
        for _, row in breaks.iterrows():
            pct = (row['high'] - row['BB_Upper']) / row['BB_Upper'] * 100
            bb_break_pcts.append(pct)
    else:
        breaks = df[df['low'] < df['BB_Lower']]
        for _, row in breaks.iterrows():
            pct = (row['BB_Lower'] - row['low']) / row['BB_Lower'] * 100
            bb_break_pcts.append(pct)
        
    # 2. Volume Spike Metrics (So với nến trước đó)
    vol_ratios = []
    for i in range(1, len(df)):
        curr_vol = df.iloc[i]['tick_volume']
        prev_vol = df.iloc[i-1]['tick_volume']
        if prev_vol > 0:
            ratio = curr_vol / prev_vol
            if ratio > 1.5: # Chỉ lấy các nến thực sự là spike
                vol_ratios.append(ratio)
    
    # 3. RSI Divergence Metrics
    div_metrics = []
    for i in range(20, len(df)):
        curr_rsi = df.iloc[i]['RSI_14']
        if reversal_type == 'Đỉnh' and curr_rsi > 60:
            prev_window = df.iloc[max(0, i-30):i]
            if not prev_window.empty:
                prev_high = prev_window['high'].max()
                prev_rsi = df.loc[prev_window['high'].idxmax(), 'RSI_14']
                if df.iloc[i]['high'] > prev_high and curr_rsi < prev_rsi:
                    div_metrics.append({
                        'price_diff': abs(df.iloc[i]['high'] - prev_high),
                        'rsi_diff': abs(prev_rsi - curr_rsi)
                    })
        elif reversal_type == 'Đáy' and curr_rsi < 40:
            prev_window = df.iloc[max(0, i-30):i]
            if not prev_window.empty:
                prev_low = prev_window['low'].min()
                prev_rsi = df.loc[prev_window['low'].idxmin(), 'RSI_14']
                if df.iloc[i]['low'] < prev_low and curr_rsi > prev_rsi:
                    div_metrics.append({
                        'price_diff': abs(prev_low - df.iloc[i]['low']),
                        'rsi_diff': abs(curr_rsi - prev_rsi)
                    })
                    
    return {
        'BB_Break_Pcts': bb_break_pcts,
        'Vol_Ratios': vol_ratios,
        'Div_Metrics': div_metrics
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
    # df_h1 = apply_indicators(df_h1) # Xóa để tránh lỗi pandas_ta
    
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
    
    # Khởi tạo kết quả tách riêng theo Đỉnh/Đáy
    def new_slot():
        return {'BB': [], 'Vol': [], 'Div_Price': [], 'Div_RSI': [],
                'Count_BB': 0, 'Count_Vol': 0, 'Count_Div': 0, 'Total': 0}

    results = {
        'M1':  {'Đỉnh': new_slot(), 'Đáy': new_slot()},
        'M5':  {'Đỉnh': new_slot(), 'Đáy': new_slot()},
        'M15': {'Đỉnh': new_slot(), 'Đáy': new_slot()}
    }
    
    count = 0
    for rev in reversals:
        count += 1
        if count % 20 == 0: print(f"Đã xử lý {count}/{len(reversals)} điểm...")
        
        rev_type = rev['type']  # 'Đỉnh' hoặc 'Đáy'
        
        for tf in ['M1', 'M5', 'M15']:
            df_tf = get_rates_for_window(symbol, tf, rev['time'], 60)
            signals = check_signals(df_tf, rev_type)
            
            if signals:
                slot = results[tf][rev_type]
                slot['Total'] += 1
                if signals['BB_Break_Pcts']:
                    slot['Count_BB'] += 1
                    slot['BB'].extend(signals['BB_Break_Pcts'])
                if signals['Vol_Ratios']:
                    slot['Count_Vol'] += 1
                    slot['Vol'].extend(signals['Vol_Ratios'])
                if signals['Div_Metrics']:
                    slot['Count_Div'] += 1
                    slot['Div_Price'].extend([m['price_diff'] for m in signals['Div_Metrics']])
                    slot['Div_RSI'].extend([m['rsi_diff'] for m in signals['Div_Metrics']])
                
    # 3. Xuất kết quả
    import numpy as np
    report = []
    report.append("=== PHÂN TÍCH CHI TIẾT DẤU VẾT ĐẢO CHIỀU - TÁCH RIÊNG ĐỈNH / ĐÁY ===")
    report.append(f"Dữ liệu: 3 năm H1. Tổng số điểm kiểm tra: {len(reversals)}")
    report.append("Phương pháp: Lấy 60 nến của khung nhỏ TRƯỚC thời điểm H1 đảo chiều.")
    
    def get_stats(data_list):
        if not data_list: return "N/A"
        return f"Min={round(np.min(data_list), 2)}, Max={round(np.max(data_list), 2)}, Avg={round(np.mean(data_list), 2)}"

    def get_distribution(data_list, bins, unit=""):
        """Tính phân phối tần suất theo các khoảng (bins), trả về top 3 khoảng phổ biến nhất."""
        if not data_list: return "     N/A"
        arr = np.array(data_list)
        counts, edges = np.histogram(arr, bins=bins)
        total = len(arr)
        # Sắp xếp theo số lần xuất hiện nhiều nhất
        sorted_idx = np.argsort(counts)[::-1]
        lines = []
        for rank, i in enumerate(sorted_idx[:3]):
            if counts[i] == 0: break
            lo, hi = round(edges[i], 3), round(edges[i+1], 3)
            pct = round(counts[i] / total * 100, 1)
            lines.append(f"     #{rank+1}: [{lo} – {hi}]{unit}  →  {counts[i]} lần ({pct}%)")
        return "\n".join(lines) if lines else "     N/A"

    for tf in ['M1', 'M5', 'M15']:
        report.append(f"\n{'='*55}")
        report.append(f"  KHUNG {tf}")
        report.append(f"{'='*55}")
        
        for rev_type in ['Đỉnh', 'Đáy']:
            data = results[tf][rev_type]
            total = data['Total']
            if total == 0:
                report.append(f"  [{rev_type}] Không có dữ liệu.")
                continue

            label = "📈 ĐỈNH (Bearish Reversal)" if rev_type == 'Đỉnh' else "📉 ĐÁY (Bullish Reversal)"
            report.append(f"\n  {label} — {total} điểm")

            div_count = data['Count_Div']
            report.append(f"  1. Phân kỳ RSI      : {div_count}/{total} = {round(div_count/total*100, 2)}%")
            report.append(f"     Khoảng cách giá  : {get_stats(data['Div_Price'])} points")
            report.append(f"     Tập trung (giá)  :")
            report.append(get_distribution(data['Div_Price'], bins=10, unit=" pts"))
            report.append(f"     Khoảng cách RSI  : {get_stats(data['Div_RSI'])} đơn vị")
            report.append(f"     Tập trung (RSI)  :")
            report.append(get_distribution(data['Div_RSI'], bins=10, unit=" đv"))

            bb_count = data['Count_BB']
            report.append(f"  2. Phá vỡ BB        : {bb_count}/{total} = {round(bb_count/total*100, 2)}%")
            report.append(f"     Mức phá vỡ       : {get_stats(data['BB'])} %")
            report.append(f"     Tập trung (%BB)  :")
            report.append(get_distribution(data['BB'], bins=10, unit="%"))

            vol_count = data['Count_Vol']
            report.append(f"  3. Volume đột biến  : {vol_count}/{total} = {round(vol_count/total*100, 2)}%")
            report.append(f"     Volume/nến trước : {get_stats(data['Vol'])} lần")
            report.append(f"     Tập trung (Vol)  :")
            report.append(get_distribution(data['Vol'], bins=10, unit="x"))
        
    final_report = "\n".join(report)
    print("\n" + final_report)
    
    with open("results/GOLD_Reversal_Signatures.txt", "w", encoding="utf-8") as f:
        f.write(final_report)
    
    # ====================================================
    # PHÂN TÍCH ĐỘ CHÍNH XÁC (PRECISION)
    # ====================================================
    print("\n[Đang tính Precision - quét toàn bộ M15 3 năm...]")
    precision_report = calc_precision_analysis(symbol, reversals)
    
    with open("results/GOLD_Reversal_Signatures.txt", "a", encoding="utf-8") as f:
        f.write("\n\n" + precision_report)
    print(precision_report)
        
    mt5.shutdown()

def calc_precision_analysis(symbol, reversals):
    """
    Quét toàn bộ M15 trong 3 năm, tìm mọi tín hiệu BB+Volume trong ngưỡng,
    kiểm tra xem bao nhiêu % có đảo chiều H1 xảy ra trong 15h tiếp theo.
    """
    import numpy as np
    from ta.momentum import RSIIndicator
    from ta.volatility import BollingerBands

    # ── Ngưỡng từ phân phối tập trung #1 ──
    THRESHOLDS = {
        'Đỉnh': {'bb_max': 0.185, 'vol_min': 1.5, 'vol_max': 2.26,
                  'div_price_max': 2.23, 'div_rsi_max': 2.19},
        'Đáy':  {'bb_max': 0.210, 'vol_min': 1.5, 'vol_max': 2.26,
                  'div_price_max': 10.13,'div_rsi_max': 2.41}
    }
    WINDOW_H = 15  # 60 nến M15 = 15 giờ

    # ── Tải toàn bộ M15 data ──
    rates_m15 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 3 * 250 * 24 * 4)
    df = pd.DataFrame(rates_m15)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)

    # ── Tính chỉ báo ──
    df['RSI'] = RSIIndicator(close=df['close'], window=14).rsi()
    bb_ind   = BollingerBands(close=df['close'], window=20, window_dev=2)
    df['BB_Upper'] = bb_ind.bollinger_hband()
    df['BB_Lower'] = bb_ind.bollinger_lband()
    df['Vol_Ratio'] = df['tick_volume'] / df['tick_volume'].shift(1)

    # BB breakout % (chỉ lấy nến thực sự phá ra ngoài)
    df['BB_Up_Pct']   = ((df['high']  - df['BB_Upper']) / df['BB_Upper'] * 100).clip(lower=0)
    df['BB_Down_Pct'] = ((df['BB_Lower'] - df['low'])   / df['BB_Lower'] * 100).clip(lower=0)

    # ── Tập hợp thời gian đảo chiều để tra cứu nhanh ──
    rev_df = pd.DataFrame(reversals)
    rev_df['time'] = pd.to_datetime(rev_df['time'])

    def get_rev_arr(rev_type):
        times = rev_df[rev_df['type'] == rev_type]['time'].sort_values()
        return np.array([t.value for t in times], dtype=np.int64)

    rev_top_arr = get_rev_arr('Đỉnh')
    rev_bot_arr = get_rev_arr('Đáy')
    window_ns   = int(pd.Timedelta(hours=WINDOW_H).value)

    def has_reversal(t_ns, rev_arr):
        """Binary search: có reversal nào trong [t, t+15h] không?"""
        lo = np.searchsorted(rev_arr, t_ns, side='left')
        return lo < len(rev_arr) and rev_arr[lo] <= t_ns + window_ns

    # ── Quét và tính precision ──
    report_lines = []
    report_lines.append("\n" + "="*60)
    report_lines.append("  PHÂN TÍCH ĐỘ CHÍNH XÁC TÍN HIỆU (SIGNAL PRECISION)")
    report_lines.append("  Khung phân tích: M15 | Cửa sổ kiểm tra: 15h tiếp theo")
    report_lines.append("  Nguồn ngưỡng: Phân phối tập trung #1 từ 3 năm dữ liệu")
    report_lines.append("="*60)

    for rev_type, thresh in THRESHOLDS.items():
        rev_arr = rev_top_arr if rev_type == 'Đỉnh' else rev_bot_arr
        label   = "📈 ĐỈNH (Bearish)" if rev_type == 'Đỉnh' else "📉 ĐÁY (Bullish)"

        # Tín hiệu BB trong ngưỡng
        if rev_type == 'Đỉnh':
            bb_mask = (df['BB_Up_Pct'] > 0) & (df['BB_Up_Pct'] <= thresh['bb_max'])
        else:
            bb_mask = (df['BB_Down_Pct'] > 0) & (df['BB_Down_Pct'] <= thresh['bb_max'])

        # Tín hiệu Volume trong ngưỡng
        vol_mask = (df['Vol_Ratio'] >= thresh['vol_min']) & (df['Vol_Ratio'] <= thresh['vol_max'])

        # RSI vùng cực trị (điều kiện để xem xét phân kỳ)
        if rev_type == 'Đỉnh':
            rsi_zone = df['RSI'] > 60
        else:
            rsi_zone = df['RSI'] < 40

        # Các tổ hợp tín hiệu
        combos = {
            'BB only'         : bb_mask,
            'Vol only'        : vol_mask,
            'BB + Vol'        : bb_mask & vol_mask,
            'BB + Vol + RSI'  : bb_mask & vol_mask & rsi_zone,
        }

        report_lines.append(f"\n  {label}")
        report_lines.append(f"  Ngưỡng BB  : 0% – {thresh['bb_max']}%")
        report_lines.append(f"  Ngưỡng Vol : {thresh['vol_min']}x – {thresh['vol_max']}x nến trước")
        report_lines.append(f"  {'Tổ hợp tín hiệu':<22} {'Số lần kích hoạt':>18} {'Có đảo chiều sau':>18} {'Precision':>10}")
        report_lines.append(f"  {'-'*70}")

        for combo_name, mask in combos.items():
            signal_times_ns = np.array([t.value for t in df[mask].index], dtype=np.int64)
            total = len(signal_times_ns)
            if total == 0:
                report_lines.append(f"  {combo_name:<22} {'0':>18} {'-':>18} {'N/A':>10}")
                continue
            tp = sum(1 for t_ns in signal_times_ns if has_reversal(t_ns, rev_arr))
            prec = round(tp / total * 100, 2)
            report_lines.append(f"  {combo_name:<22} {total:>18,} {tp:>18,} {prec:>9.2f}%")

    return "\n".join(report_lines)

if __name__ == "__main__":
    main()

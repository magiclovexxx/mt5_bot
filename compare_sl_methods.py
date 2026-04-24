"""
So sánh các phương pháp đặt SL cho chiến lược BB Breakout — GOLD
Các phương pháp test:
  1. ATR × 0.5   (hiện tại)
  2. ATR × 1.0
  3. ATR × 1.5
  4. ATR × 2.0
  5. Structural N=1  (SL = đỉnh/đáy của 1 nến tiếp theo)
  6. Structural N=2  (SL = đỉnh/đáy của 2 nến tiếp theo)
  7. Structural N=3  (SL = đỉnh/đáy của 3 nến tiếp theo)
  8. Fixed % 0.2%   (0.2% × entry price)
  9. Fixed % 0.3%   (0.3% × entry price)
  10. Fixed % 0.5%  (0.5% × entry price)
Output: results/GOLD_SL_Comparison.txt
"""

import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf8')

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands, AverageTrueRange
from src.fetch_data import initialize_mt5

# ══════════════════════════════════════════
# CẤU HÌNH
# ══════════════════════════════════════════
SYMBOL       = "GOLD"
BARS_1Y      = 250 * 24
BB_WINDOW    = 20
BB_STD       = 2
ATR_WINDOW   = 14
RR_RATIO     = 3
FORWARD_BARS = 60
BB_THRESHOLD_MIN = 0.0
OUTPUT_FILE  = "results/GOLD_SL_Comparison.txt"

SL_METHODS = [
    ("ATR×0.5",      "atr_mult", 0.5),
    ("ATR×1.0",      "atr_mult", 1.0),
    ("ATR×1.5",      "atr_mult", 1.5),
    ("ATR×2.0",      "atr_mult", 2.0),
    ("Struct N=1",   "struct",   1),
    ("Struct N=2",   "struct",   2),
    ("Struct N=3",   "struct",   3),
    ("Fixed 0.2%",   "pct",      0.2),
    ("Fixed 0.3%",   "pct",      0.3),
    ("Fixed 0.5%",   "pct",      0.5),
]


# ══════════════════════════════════════════
# DATA
# ══════════════════════════════════════════
def load_data(tf, bars):
    rates = mt5.copy_rates_from_pos(SYMBOL, tf, 0, bars)
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    return df

def apply_indicators(df):
    bb = BollingerBands(close=df['close'], window=BB_WINDOW, window_dev=BB_STD)
    df['BB_Upper'] = bb.bollinger_hband()
    df['BB_Lower'] = bb.bollinger_lband()
    df['BB_Mid']   = bb.bollinger_mavg()
    df['ATR']      = AverageTrueRange(
                         high=df['high'], low=df['low'],
                         close=df['close'], window=ATR_WINDOW).average_true_range()
    df['BB_Up_Pct']   = ((df['high']  - df['BB_Upper']) / df['BB_Upper']  * 100).clip(lower=0)
    df['BB_Down_Pct'] = ((df['BB_Lower'] - df['low'])   / df['BB_Lower']  * 100).clip(lower=0)
    df['BB_Width']    = ((df['BB_Upper'] - df['BB_Lower']) / df['BB_Mid']  * 100)
    df['Hour']        = df.index.hour
    return df.dropna()


# ══════════════════════════════════════════
# SL CALCULATOR
# ══════════════════════════════════════════
def calc_sl(df, idx, rev_type, sl_type, sl_param):
    row   = df.iloc[idx]
    atr   = row['ATR']
    entry = row['high'] if rev_type == 'Đỉnh' else row['low']
    future = df.iloc[idx+1 : idx+1+max(3, FORWARD_BARS)]

    if sl_type == "atr_mult":
        risk = atr * sl_param

    elif sl_type == "struct":
        n = int(sl_param)
        fn = df.iloc[idx+1 : idx+1+n]
        if len(fn) < n:
            risk = atr * 0.5  # fallback
        else:
            if rev_type == 'Đỉnh':   # SELL → SL = max high of next N candles
                sl_struct = fn['high'].max()
                risk = max(sl_struct - entry, atr * 0.1)
            else:                     # BUY → SL = min low of next N candles
                sl_struct = fn['low'].min()
                risk = max(entry - sl_struct, atr * 0.1)

    elif sl_type == "pct":
        risk = entry * (sl_param / 100.0)

    else:
        risk = atr * 0.5

    return risk


def simulate(df, idx, rev_type, sl_type, sl_param, rr=3, forward=60):
    row   = df.iloc[idx]
    entry = row['high'] if rev_type == 'Đỉnh' else row['low']
    risk  = calc_sl(df, idx, rev_type, sl_type, sl_param)

    if risk <= 0:
        return 'None', 0

    if rev_type == 'Đỉnh':
        sl = entry + risk
        tp = entry - risk * rr
        future = df.iloc[idx+1 : idx+1+forward]
        for _, fr in future.iterrows():
            if fr['high'] >= sl: return 'SL', risk
            if fr['low']  <= tp: return 'TP', risk
    else:
        sl = entry - risk
        tp = entry + risk * rr
        future = df.iloc[idx+1 : idx+1+forward]
        for _, fr in future.iterrows():
            if fr['low']  <= sl: return 'SL', risk
            if fr['high'] >= tp: return 'TP', risk

    return 'None', risk


# ══════════════════════════════════════════
# RUN ALL METHODS
# ══════════════════════════════════════════
def run_comparison(df, tf_label):
    signals = {'Đỉnh': [], 'Đáy': []}

    # Lấy tất cả tín hiệu BB breakout
    for i in range(BB_WINDOW, len(df) - FORWARD_BARS):
        row = df.iloc[i]
        for rev_type in ['Đỉnh', 'Đáy']:
            bb_pct = row['BB_Up_Pct'] if rev_type == 'Đỉnh' else row['BB_Down_Pct']
            if bb_pct <= BB_THRESHOLD_MIN:
                continue
            signals[rev_type].append(i)

    results = {}
    for method_name, sl_type, sl_param in SL_METHODS:
        results[method_name] = {}
        for rev_type in ['Đỉnh', 'Đáy']:
            tp_n, sl_n, none_n = 0, 0, 0
            risks = []
            for idx in signals[rev_type]:
                res, risk = simulate(df, idx, rev_type, sl_type, sl_param, rr=RR_RATIO, forward=FORWARD_BARS)
                if res == 'TP':   tp_n   += 1
                elif res == 'SL': sl_n   += 1
                else:             none_n += 1
                if risk > 0:
                    risks.append(risk)

            total = len(signals[rev_type])
            tp_r  = tp_n / total
            sl_r  = sl_n / total
            ev    = tp_r * RR_RATIO - sl_r
            results[method_name][rev_type] = {
                'total'    : total,
                'tp_n'     : tp_n,
                'sl_n'     : sl_n,
                'none_n'   : none_n,
                'tp_pct'   : round(tp_r * 100, 2),
                'sl_pct'   : round(sl_r * 100, 2),
                'ev'       : round(ev, 3),
                'avg_sl_d' : round(np.mean(risks), 2) if risks else 0,
                'avg_tp_d' : round(np.mean(risks) * RR_RATIO, 2) if risks else 0,
            }

    return results, {rt: len(v) for rt, v in signals.items()}


# ══════════════════════════════════════════
# REPORT
# ══════════════════════════════════════════
def fmt(v): return f"{v:>7.2f}"

def build_comparison_report(results, signal_counts, tf_label):
    lines = []
    SEP = "═" * 80

    lines.append(f"\n{SEP}")
    lines.append(f"  KHUNG {tf_label}  —  SO SÁNH PHƯƠNG PHÁP ĐẶT SL")
    lines.append(f"  Tổng tín hiệu: SELL={signal_counts['Đỉnh']:,} | BUY={signal_counts['Đáy']:,}")
    lines.append(f"  R:R = 1:{RR_RATIO} | Kiểm tra {FORWARD_BARS} nến | BB(20,2)")
    lines.append(SEP)

    for rev_type, label in [('Đỉnh', '📈 SELL (Bắt đỉnh)'), ('Đáy', '📉 BUY (Bắt đáy)')]:
        lines.append(f"\n  {label}\n")
        lines.append(f"  {'Phương pháp':<14} {'TP%':>7} {'SL%':>7} {'None%':>7} {'EV':>8} {'SL$ avg':>9} {'TP$ avg':>9}  Đánh giá")
        lines.append(f"  {'-'*78}")

        # Sắp xếp theo EV giảm dần
        sorted_methods = sorted(results.items(), key=lambda x: -x[1][rev_type]['ev'])

        for method_name, mres in sorted_methods:
            r     = mres[rev_type]
            none_pct = round(r['none_n'] / r['total'] * 100, 2)
            ev_str = f"{r['ev']:>6.3f}R"

            if r['ev'] >= 1.5:    tag = "🏆 TỐT NHẤT"
            elif r['ev'] >= 1.2:  tag = "✅ Tốt"
            elif r['ev'] >= 1.0:  tag = "✅ Chấp nhận"
            elif r['ev'] >= 0.7:  tag = "⚠️  Trung bình"
            else:                 tag = "❌ Kém"

            lines.append(
                f"  {method_name:<14} {r['tp_pct']:>7}% {r['sl_pct']:>7}% {none_pct:>7}% "
                f"{ev_str:>8} {r['avg_sl_d']:>9.1f}$ {r['avg_tp_d']:>9.1f}$  {tag}"
            )

    return "\n".join(lines)


# ══════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════
def main():
    print("Đang khởi tạo MT5...")
    initialize_mt5()

    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append("  SO SÁNH PHƯƠNG PHÁP ĐẶT SL — GOLD BB BREAKOUT")
    report_lines.append(f"  R:R 1:{RR_RATIO} | BB(20,2) | Dữ liệu 1 năm | FORWARD={FORWARD_BARS} nến")
    report_lines.append("=" * 80)
    report_lines.append("""
  CÁC PHƯƠNG PHÁP:
  ATR×0.5   : SL = entry ± ATR × 0.5  (cơ sở)
  ATR×1.0   : SL = entry ± ATR × 1.0
  ATR×1.5   : SL = entry ± ATR × 1.5
  ATR×2.0   : SL = entry ± ATR × 2.0
  Struct N=1: SL = đỉnh/đáy của 1 nến tiếp theo
  Struct N=2: SL = đỉnh/đáy của 2 nến tiếp theo (extremum)
  Struct N=3: SL = đỉnh/đáy của 3 nến tiếp theo (extremum)
  Fixed 0.2%: SL = entry × 0.2%
  Fixed 0.3%: SL = entry × 0.3%
  Fixed 0.5%: SL = entry × 0.5%
""")

    for tf_label, tf_mt5, bars in [
        ("M15", mt5.TIMEFRAME_M15, BARS_1Y * 4),
        ("H1",  mt5.TIMEFRAME_H1,  BARS_1Y),
    ]:
        print(f"\n[{tf_label}] Tải dữ liệu {bars:,} nến...")
        df = load_data(tf_mt5, bars)
        df = apply_indicators(df)
        print(f"[{tf_label}] Đang chạy {len(SL_METHODS)} phương pháp SL...")

        results, signal_counts = run_comparison(df, tf_label)
        report_lines.append(build_comparison_report(results, signal_counts, tf_label))
        print(f"[{tf_label}] Xong!")

    final = "\n".join(report_lines)
    print("\n" + final)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(final)
    print(f"\n✅ Đã lưu: {OUTPUT_FILE}")
    mt5.shutdown()


if __name__ == "__main__":
    main()

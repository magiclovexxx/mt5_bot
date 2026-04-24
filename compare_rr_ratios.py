"""
So sánh R:R kết hợp SL method — GOLD BB Breakout
Test: 10 mức R:R × 3 SL tốt nhất (Struct N=1, ATR×0.5, Fixed 0.2%)
Output: results/GOLD_RR_Comparison.txt
"""

import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf8')

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from ta.volatility import BollingerBands, AverageTrueRange
from src.fetch_data import initialize_mt5

SYMBOL       = "GOLD"
BARS_1Y      = 250 * 24
BB_WINDOW    = 20
BB_STD       = 2
ATR_WINDOW   = 14
FORWARD_BARS = 120          # nới rộng để đủ chỗ cho TP xa hơn
BB_THRESHOLD_MIN = 0.0
OUTPUT_FILE  = "results/GOLD_RR_Comparison.txt"

RR_LIST      = [1.5, 2, 2.5, 3, 3.5, 4, 5, 6, 7, 8]

SL_METHODS = [
    ("Struct N=1", "struct", 1),
    ("ATR×0.5",   "atr",    0.5),
    ("Fixed 0.2%","pct",    0.2),
]


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
    df['Hour']        = df.index.hour
    return df.dropna()

def calc_risk(df, idx, rev_type, sl_type, sl_param):
    row   = df.iloc[idx]
    atr   = row['ATR']
    entry = row['high'] if rev_type == 'Đỉnh' else row['low']

    if sl_type == "atr":
        return atr * sl_param

    elif sl_type == "struct":
        n  = int(sl_param)
        fn = df.iloc[idx+1 : idx+1+n]
        if len(fn) == 0:
            return atr * 0.5
        if rev_type == 'Đỉnh':
            return max(fn['high'].max() - entry, atr * 0.05)
        else:
            return max(entry - fn['low'].min(), atr * 0.05)

    elif sl_type == "pct":
        return entry * (sl_param / 100.0)

    return atr * 0.5

def simulate_rr(df, idx, rev_type, sl_type, sl_param, rr, forward):
    row   = df.iloc[idx]
    entry = row['high'] if rev_type == 'Đỉnh' else row['low']
    risk  = calc_risk(df, idx, rev_type, sl_type, sl_param)
    if risk <= 0:
        return 'None', risk

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


def run_rr_comparison(df, tf_label):
    # Lấy index tín hiệu BB breakout một lần
    signals = {'Đỉnh': [], 'Đáy': []}
    for i in range(BB_WINDOW, len(df) - FORWARD_BARS):
        row = df.iloc[i]
        for rev_type in ['Đỉnh', 'Đáy']:
            bb_pct = row['BB_Up_Pct'] if rev_type == 'Đỉnh' else row['BB_Down_Pct']
            if bb_pct > BB_THRESHOLD_MIN:
                signals[rev_type].append(i)

    # Build kết quả: [sl_name][rev_type][rr] = {tp%, sl%, ev, none%}
    all_results = {}
    for sl_name, sl_type, sl_param in SL_METHODS:
        all_results[sl_name] = {}
        for rev_type in ['Đỉnh', 'Đáy']:
            all_results[sl_name][rev_type] = {}
            for rr in RR_LIST:
                tp_n = sl_n = none_n = 0
                risks = []
                for idx in signals[rev_type]:
                    res, risk = simulate_rr(df, idx, rev_type, sl_type, sl_param, rr, FORWARD_BARS)
                    if res == 'TP':   tp_n   += 1
                    elif res == 'SL': sl_n   += 1
                    else:             none_n += 1
                    if risk > 0: risks.append(risk)
                total = len(signals[rev_type])
                tp_r  = tp_n / total
                sl_r  = sl_n / total
                ev    = tp_r * rr - sl_r
                all_results[sl_name][rev_type][rr] = {
                    'tp_pct'  : round(tp_r * 100, 2),
                    'sl_pct'  : round(sl_r * 100, 2),
                    'none_pct': round(none_n / total * 100, 2),
                    'ev'      : round(ev, 3),
                    'avg_sl'  : round(np.mean(risks), 1) if risks else 0,
                }

    return all_results, {rt: len(v) for rt, v in signals.items()}


def fmt_ev(ev):
    if ev >= 2.0:   return f"{ev:.3f}R 🏆"
    elif ev >= 1.5: return f"{ev:.3f}R ✅"
    elif ev >= 1.0: return f"{ev:.3f}R  ·"
    elif ev >= 0.5: return f"{ev:.3f}R ⚠"
    else:           return f"{ev:.3f}R ❌"

def build_rr_report(all_results, signal_counts, tf_label):
    lines = []
    SEP = "═" * 90
    lines.append(f"\n{SEP}")
    lines.append(f"  KHUNG {tf_label}  —  SO SÁNH R:R RATIO × SL METHOD")
    lines.append(f"  SELL={signal_counts['Đỉnh']:,} tín hiệu | BUY={signal_counts['Đáy']:,} tín hiệu")
    lines.append(f"  FORWARD={FORWARD_BARS} nến | BB(20,2)")
    lines.append(SEP)

    for rev_type, direction in [('Đỉnh', '📈 SELL (Bắt đỉnh)'), ('Đáy', '📉 BUY (Bắt đáy)')]:
        lines.append(f"\n  {direction}\n")

        # Header
        rr_header = "".join(f"{'1:'+str(rr) if rr==int(rr) else '1:'+str(rr):>13}" for rr in RR_LIST)
        lines.append(f"  {'SL Method':<14}{rr_header}")
        lines.append(f"  {'-'*14}" + "─────────────" * len(RR_LIST))

        for sl_name, _, _ in SL_METHODS:
            row_ev = ""
            for rr in RR_LIST:
                r = all_results[sl_name][rev_type][rr]
                ev_str = f"{r['ev']:.3f}R"
                # Thêm icon
                if r['ev'] >= 2.0:   ev_str += "🏆"
                elif r['ev'] >= 1.5: ev_str += "✅"
                elif r['ev'] >= 1.0: ev_str += " ·"
                elif r['ev'] < 0:    ev_str += "❌"
                row_ev += f"{ev_str:>13}"
            lines.append(f"  {sl_name:<14}{row_ev}")

        # Tìm best EV cho từng method
        lines.append(f"\n  BEST R:R cho từng SL method (EV cao nhất):")
        for sl_name, _, _ in SL_METHODS:
            best_rr  = max(RR_LIST, key=lambda rr: all_results[sl_name][rev_type][rr]['ev'])
            best_res = all_results[sl_name][rev_type][best_rr]
            lines.append(
                f"  {sl_name:<14}  Best R:R = 1:{best_rr:<5} "
                f"EV={best_res['ev']:.3f}R  "
                f"TP={best_res['tp_pct']}%  SL={best_res['sl_pct']}%  SL$avg={best_res['avg_sl']}$"
            )

        # Chi tiết TP%/SL% cho Struct N=1 (winner)
        lines.append(f"\n  Chi tiết Struct N=1 theo từng R:R:")
        lines.append(f"  {'R:R':<8} {'TP%':>8} {'SL%':>8} {'None%':>8} {'EV':>10} {'SL$avg':>8}")
        lines.append(f"  {'-'*54}")
        for rr in RR_LIST:
            r = all_results['Struct N=1'][rev_type][rr]
            rr_str = f"1:{rr}" if rr == int(rr) else f"1:{rr}"
            lines.append(
                f"  {rr_str:<8} {r['tp_pct']:>8}% {r['sl_pct']:>8}% {r['none_pct']:>8}% "
                f"{r['ev']:>10.3f}R {r['avg_sl']:>8}$"
            )

    return "\n".join(lines)


def main():
    print("Đang khởi tạo MT5...")
    initialize_mt5()

    report_lines = []
    report_lines.append("=" * 90)
    report_lines.append("  SO SÁNH R:R RATIO — GOLD BB BREAKOUT")
    report_lines.append(f"  SL methods: Struct N=1 | ATR×0.5 | Fixed 0.2%")
    report_lines.append(f"  R:R test: {' | '.join(['1:'+str(r) if r==int(r) else '1:'+str(r) for r in RR_LIST])}")
    report_lines.append(f"  FORWARD={FORWARD_BARS} nến (nới rộng để cho TP xa)")
    report_lines.append("=" * 90)

    for tf_label, tf_mt5, bars in [
        ("M15", mt5.TIMEFRAME_M15, BARS_1Y * 4),
        ("H1",  mt5.TIMEFRAME_H1,  BARS_1Y),
    ]:
        print(f"\n[{tf_label}] Tải {bars:,} nến...")
        df = load_data(tf_mt5, bars)
        df = apply_indicators(df)
        print(f"[{tf_label}] Đang tính {len(SL_METHODS)} SL × {len(RR_LIST)} R:R...")
        results, counts = run_rr_comparison(df, tf_label)
        report_lines.append(build_rr_report(results, counts, tf_label))
        print(f"[{tf_label}] Xong!")

    final = "\n".join(report_lines)
    print("\n" + final)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(final)
    print(f"\n✅ Đã lưu: {OUTPUT_FILE}")
    mt5.shutdown()


if __name__ == "__main__":
    main()

"""
Phân tích BB Breakout — GOLD (XAUUSD)
Strategy: Pending order NGOÀI BB tại ngưỡng x% phá vỡ đã tính

Logic:
  1. Nến [idx] phá vỡ BB với bb_pct% (high > BB_Upper + bb_pct% hoặc low < BB_Lower - bb_pct%).
  2. Đặt PENDING ORDER tại chính mức giá đó (BB_Upper × (1 + bb_pct/100) cho sell,
     BB_Lower × (1 - bb_pct/100) cho buy) — tức là entry = đỉnh/đáy nến breakout.
  3. SL: entry + ATR×0.5 (sell) | entry - ATR×0.5 (buy)
  4. TP: entry - risk × 3  (sell) | entry + risk × 3  (buy)
  5. Kiểm tra trong FORWARD_BARS nến tiếp theo:
       - Nếu giá quay lại chạm mức entry (high >= entry cho sell, low <= entry cho buy) → khớp lệnh
       - Sau khi khớp: theo dõi TP/SL
       - Nếu giá không bao giờ quay lại → NOT_FILLED
Dữ liệu: 1 năm | Khung: M15 và H1 | Tách Đỉnh / Đáy | R:R 1:3
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
RR_RATIO     = 5           # R:R = 1:5
FORWARD_BARS = 120         # Nới rộng để đủ chỗ cho TP xa hơn
SL_METHOD    = "struct"    # "struct" | "atr_mult" | "pct"
SL_STRUCT_N  = 1           # Structural SL: dùng đỉnh/đáy của N nến tiếp theo
ATR_SL_MULT  = 0.5        # Chỉ dùng khi SL_METHOD="atr_mult"

# Ngưỡng BB tối thiểu để xét
BB_THRESHOLD_MIN = 0.0
GOLD_PIP        = 0.10   # GOLD: 1 pip = $0.10 (quote 2 thập phân)

# Khoảng phân tích chi tiết
BB_BUCKETS = [0, 0.05, 0.10, 0.15, 0.20, 0.30, 0.50, 1.0, 999]

OUTPUT_FILE = "results/GOLD_BB_Breakout_Analysis.txt"


# ══════════════════════════════════════════
# HÀM TIỆN ÍCH
# ══════════════════════════════════════════
def load_data(tf, bars):
    rates = mt5.copy_rates_from_pos(SYMBOL, tf, 0, bars)
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    return df

def apply_indicators(df):
    df['RSI']  = RSIIndicator(close=df['close'], window=14).rsi()
    bb = BollingerBands(close=df['close'], window=BB_WINDOW, window_dev=BB_STD)
    df['BB_Upper'] = bb.bollinger_hband()
    df['BB_Lower'] = bb.bollinger_lband()
    df['BB_Mid']   = bb.bollinger_mavg()
    df['ATR']      = AverageTrueRange(
                         high=df['high'], low=df['low'],
                         close=df['close'], window=ATR_WINDOW).average_true_range()
    # bb_pct = % nến vượt ngoài BB so với BB band
    df['BB_Up_Pct']   = ((df['high']  - df['BB_Upper']) / df['BB_Upper']  * 100).clip(lower=0)
    df['BB_Down_Pct'] = ((df['BB_Lower'] - df['low'])   / df['BB_Lower']  * 100).clip(lower=0)
    # BB Width% = khoảng cách 2 band so với giá giữa (BB_Mid)
    df['BB_Width']    = ((df['BB_Upper'] - df['BB_Lower']) / df['BB_Mid']  * 100)
    df['Hour']        = df.index.hour
    return df.dropna()

def get_daily_reversals(df_h1):
    df = df_h1.copy()
    df['Date'] = df.index.date
    rev_set = {}
    for date, grp in df.groupby('Date'):
        if len(grp) < 12: continue
        rev_set[grp['high'].idxmax()] = 'Đỉnh'
        rev_set[grp['low'].idxmin()]  = 'Đáy'
    top_ns = np.sort(np.array([t.value for t, v in rev_set.items() if v == 'Đỉnh'], dtype=np.int64))
    bot_ns = np.sort(np.array([t.value for t, v in rev_set.items() if v == 'Đáy'],  dtype=np.int64))
    return top_ns, bot_ns

def has_reversal_after(t_ns, rev_arr, window_ns):
    lo = np.searchsorted(rev_arr, t_ns, side='left')
    return lo < len(rev_arr) and rev_arr[lo] <= t_ns + window_ns


def calc_risk(df, idx, rev_type):
    """Tính risk (SL distance) theo SL_METHOD được cấu hình."""
    row   = df.iloc[idx]
    atr   = row['ATR']
    entry = row['high'] if rev_type == 'Đỉnh' else row['low']

    if SL_METHOD == "struct":
        n  = SL_STRUCT_N
        fn = df.iloc[idx+1 : idx+1+n]
        if len(fn) == 0:
            return atr * 0.5
        if rev_type == 'Đỉnh':    # SELL → SL = max high của N nến tiếp theo
            sl_price = fn['high'].max()
            return max(sl_price - entry, atr * 0.05)
        else:                      # BUY → SL = min low của N nến tiếp theo
            sl_price = fn['low'].min()
            return max(entry - sl_price, atr * 0.05)

    elif SL_METHOD == "atr_mult":
        return atr * ATR_SL_MULT

    elif SL_METHOD == "pct":
        return entry * (ATR_SL_MULT / 100.0)   # ATR_SL_MULT dùng làm % ở đây

    return atr * 0.5


def simulate_pending_outside_bb(df, idx, rev_type, rr=5, forward=120):
    """
    Mô phỏng PENDING ORDER đặt NGOÀI BB.

    Entry  : high (SELL) / low (BUY) của nến breakout
    SL     : theo SL_METHOD — mặc định Structural N=1
             (đỉnh/đáy của nến kế tiếp ngay sau breakout)
    TP     : entry ∓ risk × rr

    Trả về: dict {'result': 'TP'|'SL'|'None', 'entry', 'sl', 'tp', 'risk', 'atr'}
    """
    row   = df.iloc[idx]
    atr   = row['ATR']
    risk  = calc_risk(df, idx, rev_type)
    if risk <= 0:
        entry = row['high'] if rev_type == 'Đỉnh' else row['low']
        return {'result': 'None', 'entry': entry, 'sl': entry, 'tp': entry, 'risk': 0, 'atr': atr}

    if rev_type == 'Đỉnh':        # SELL
        entry = row['high']
        sl    = entry + risk
        tp    = entry - risk * rr
        future = df.iloc[idx+1 : idx+1+forward]
        res = 'None'
        for _, fr in future.iterrows():
            if fr['high'] >= sl: res = 'SL'; break
            if fr['low']  <= tp: res = 'TP'; break
        return {'result': res, 'entry': entry, 'sl': sl, 'tp': tp, 'risk': risk, 'atr': atr}

    else:                          # BUY
        entry = row['low']
        sl    = entry - risk
        tp    = entry + risk * rr
        future = df.iloc[idx+1 : idx+1+forward]
        res = 'None'
        for _, fr in future.iterrows():
            if fr['low']  <= sl: res = 'SL'; break
            if fr['high'] >= tp: res = 'TP'; break
        return {'result': res, 'entry': entry, 'sl': sl, 'tp': tp, 'risk': risk, 'atr': atr}


def fmt_pct(n, d):
    return f"{round(n/d*100, 2)}%" if d > 0 else "N/A"

def bucket_label(lo, hi):
    return f"> {lo}%" if hi >= 999 else f"{lo}% – {hi}%"


# ══════════════════════════════════════════
# CORE ANALYSIS
# ══════════════════════════════════════════
def analyze_tf(df, rev_arr_top, rev_arr_bot, window_h):
    window_ns = int(pd.Timedelta(hours=window_h).value)
    records   = {'Đỉnh': [], 'Đáy': []}

    for i in range(BB_WINDOW, len(df) - FORWARD_BARS):
        row  = df.iloc[i]
        t_ns = df.index[i].value

        for rev_type in ['Đỉnh', 'Đáy']:
            bb_pct  = row['BB_Up_Pct']  if rev_type == 'Đỉnh' else row['BB_Down_Pct']
            rev_arr = rev_arr_top       if rev_type == 'Đỉnh' else rev_arr_bot

            if bb_pct <= BB_THRESHOLD_MIN:
                continue

            reversal  = has_reversal_after(t_ns, rev_arr, window_ns)
            rr_info   = simulate_pending_outside_bb(df, i, rev_type, rr=RR_RATIO, forward=FORWARD_BARS)

            records[rev_type].append({
                'hour'        : int(row['Hour']),
                'bb_pct'      : round(bb_pct, 4),
                'bb_width'    : round(float(row['BB_Width']), 4),
                'bb_mid'      : round(float(row['BB_Mid']), 2),
                'entry'       : round(rr_info['entry'], 2),
                'sl'          : round(rr_info['sl'], 2),
                'tp'          : round(rr_info['tp'], 2),
                'risk'        : round(rr_info['risk'], 2),
                'atr'         : round(rr_info['atr'], 2),
                'reversal'    : reversal,
                'result'      : rr_info['result'],
            })

    return records


# ══════════════════════════════════════════
# REPORT BUILDER
# ══════════════════════════════════════════
def build_report(records, tf_label):
    lines = []
    SEP   = "═" * 65
    lines.append(f"\n{SEP}")
    lines.append(f"  KHUNG {tf_label}  —  BB PENDING ORDER ANALYSIS (NGOÀI BB)")
    lines.append(f"  Entry  : Pending tại đỉnh/đáy nến breakout (ngoài BB band)")
    lines.append(f"  SL     : Structural N={SL_STRUCT_N} (đỉnh/đáy của {SL_STRUCT_N} nến tiếp theo)")
    lines.append(f"  TP     : entry ∓ risk × {RR_RATIO} | R:R 1:{RR_RATIO}")
    lines.append(f"  Check  : {FORWARD_BARS} nến tiếp theo")

    lines.append(SEP)

    for rev_type in ['Đỉnh', 'Đáy']:
        recs  = records[rev_type]
        label = "📈 ĐỈNH (SELL — entry tại high nến ngoài BB_Upper)" if rev_type == 'Đỉnh' \
                else "📉 ĐÁY (BUY — entry tại low nến ngoài BB_Lower)"
        lines.append(f"\n  {label}  —  {len(recs):,} tín hiệu\n")

        if not recs:
            lines.append("  Không có dữ liệu.")
            continue

        total  = len(recs)
        prec   = sum(1 for r in recs if r['reversal'])
        tp_n   = sum(1 for r in recs if r['result'] == 'TP')
        sl_n   = sum(1 for r in recs if r['result'] == 'SL')
        none_n = sum(1 for r in recs if r['result'] == 'None')
        bb_vals = [r['bb_pct'] for r in recs]

        # ── Tổng quan ──
        lines.append(f"  TỔNG QUAN")
        lines.append(f"  {'Tổng tín hiệu:':<32} {total:>10,}")
        lines.append(f"  {'Precision (→ đảo chiều):':<32} {fmt_pct(prec, total):>10}")
        lines.append(f"  {'TP hit (R:R 1:{}):':<32}".format(RR_RATIO) + f" {fmt_pct(tp_n, total):>10}")
        lines.append(f"  {'SL hit:':<32} {fmt_pct(sl_n, total):>10}")
        lines.append(f"  {'Chưa kết thúc (None):':<32} {fmt_pct(none_n, total):>10}")
        lines.append(f"  {'BB% phá vỡ  Avg / Max:':<32} {round(np.mean(bb_vals),4):>7} / {round(np.max(bb_vals),4):>7}")

        # ── Kỳ vọng toán học ──
        tp_rate_total = tp_n / total
        sl_rate_total = sl_n / total
        ev = tp_rate_total * RR_RATIO - sl_rate_total * 1
        lines.append(f"  {'Kỳ vọng (EV per trade):':<32} {round(ev, 4):>10}R")

        PIP = GOLD_PIP
        # ── Phân tích theo khoảng BB% ──
        lines.append(f"\n  PHÂN TÍCH THEO KHOẢNG % PHÁ V᩠ BB (kèm giá & pip):")
        lines.append(f"  Note: GOLD 1 pip = ${PIP} | SLpip = SL$/{PIP} | TPpip = TP$/{PIP}")
        lines.append(f"  {'Khoảng BB%':<16} {'Số TH':>6} {'TP%':>7} {'SL%':>7} {'EV':>7} {'Vượt$':>7} {'SL$':>6} {'SLpip':>7} {'TP$':>7} {'TPpip':>7} {'ATR$':>6}")
        lines.append(f"  {'-'*90}")

        for lo, hi in zip(BB_BUCKETS[:-1], BB_BUCKETS[1:]):
            br = [r for r in recs if lo < r['bb_pct'] <= hi]
            if not br: continue
            n          = len(br)
            tp_b       = sum(1 for r in br if r['result'] == 'TP')
            sl_b       = sum(1 for r in br if r['result'] == 'SL')
            prec_b     = sum(1 for r in br if r['reversal'])
            tp_r       = tp_b / n
            sl_r       = sl_b / n
            ev_b       = tp_r * RR_RATIO - sl_r
            # Giá thực tế trung bình
            avg_entry  = np.mean([r['entry'] for r in br])
            avg_bb_mid = np.mean([r['bb_mid'] for r in br])
            avg_vuot   = round(avg_entry - avg_bb_mid, 2) if rev_type == 'Đỉnh' \
                         else round(avg_bb_mid - avg_entry, 2)
            avg_sl_d   = round(np.mean([r['risk'] for r in br]), 2)
            avg_tp_d   = round(avg_sl_d * RR_RATIO, 2)
            avg_atr    = round(np.mean([r['atr'] for r in br]), 2)
            sl_pip     = round(avg_sl_d / PIP)
            tp_pip     = round(avg_tp_d / PIP)
            lines.append(
                f"  {bucket_label(lo,hi):<16} {n:>6,} {fmt_pct(tp_b,n):>7} "
                f"{fmt_pct(sl_b,n):>7} {round(ev_b,3):>7}R"
                f" {avg_vuot:>7.1f}$ {avg_sl_d:>6.1f}$ {sl_pip:>7} {avg_tp_d:>7.1f}$ {tp_pip:>7} {avg_atr:>6.1f}$"
            )

        # ── Phân tích theo BB Width% (khoảng cách 2 band / giá giữa) ──
        width_vals = [r['bb_width'] for r in recs]
        w_min, w_max = min(width_vals), max(width_vals)
        # Tự động chia thành 6 khoảng đều dựa trên phân phối thực tế
        w_pcts = [np.percentile(width_vals, p) for p in [0, 20, 40, 60, 80, 100]]
        w_pcts = sorted(set(round(v, 3) for v in w_pcts))

        lines.append(f"\n  PHÂN TÍCH THEO BB WIDTH% (khoảng cách 2 band / giá giữa):")
        lines.append(f"  BB Width Avg={round(np.mean(width_vals),3)}%  Min={round(w_min,3)}%  Max={round(w_max,3)}%")
        lines.append(f"  {'Khoảng Width%':<18} {'Số TH':>8} {'TP%':>8} {'SL%':>8} {'EV':>8} {'WidthAvg':>10}")
        lines.append(f"  {'-'*62}")

        for i in range(len(w_pcts) - 1):
            wlo, whi = w_pcts[i], w_pcts[i+1]
            if i == len(w_pcts) - 2:
                bw = [r for r in recs if r['bb_width'] >= wlo]
                lbl = f"{wlo}% – {whi}%"
            else:
                bw = [r for r in recs if wlo <= r['bb_width'] < whi]
                lbl = f"{wlo}% – {whi}%"
            if not bw: continue
            n     = len(bw)
            tp_w  = sum(1 for r in bw if r['result'] == 'TP')
            sl_w  = sum(1 for r in bw if r['result'] == 'SL')
            tp_r  = tp_w / n
            sl_r  = sl_w / n
            ev_w  = tp_r * RR_RATIO - sl_r
            w_avg = round(np.mean([r['bb_width'] for r in bw]), 3)
            lines.append(
                f"  {lbl:<18} {n:>8,} {fmt_pct(tp_w,n):>8} "
                f"{fmt_pct(sl_w,n):>8} {round(ev_w,3):>8}R {w_avg:>9}%"
            )

        # ── Phân tích theo khung giờ (UTC+7) ──
        lines.append(f"\n  PHÂN BỐ THEO KHUNG GIỜ (UTC+7) — sắp xếp theo TP%:")
        lines.append(f"  {'Giờ':<16} {'Số TH':>8} {'Prec':>8} {'TP%':>8} {'SL%':>8} {'EV':>8} {'WidthAvg':>10}")
        lines.append(f"  {'-'*72}")

        hour_data = {}
        for r in recs:
            h = int((r['hour'] + 7) % 24)
            hour_data.setdefault(h, []).append(r)

        def tp_rate_h(h):
            hr   = hour_data[h]
            tp_h = sum(1 for r in hr if r['result'] == 'TP')
            return tp_h / len(hr) if hr else 0

        for h in sorted(hour_data, key=lambda x: -tp_rate_h(x)):
            hr      = hour_data[h]
            n       = len(hr)
            tp_h    = sum(1 for r in hr if r['result'] == 'TP')
            sl_h    = sum(1 for r in hr if r['result'] == 'SL')
            prec_h  = sum(1 for r in hr if r['reversal'])
            tp_r    = tp_h / n
            sl_r    = sl_h / n
            ev_h    = tp_r * RR_RATIO - sl_r
            w_avg_h = round(np.mean([r['bb_width'] for r in hr]), 3)
            h_next  = int((h + 1) % 24)
            lines.append(
                f"  {h:02d}:00 – {h_next:02d}:00    "
                f"{n:>8,} {fmt_pct(prec_h,n):>8} "
                f"{fmt_pct(tp_h,n):>8} {fmt_pct(sl_h,n):>8} {round(ev_h,3):>8}R {w_avg_h:>9}%"
            )

    return "\n".join(lines)


# ══════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════
def main():
    print("Đang khởi tạo MT5...")
    initialize_mt5()

    report_lines = []
    report_lines.append("=" * 65)
    report_lines.append("  PHÂN TÍCH BB BREAKOUT — PENDING ORDER NGOÀI BB — GOLD")
    report_lines.append(f"  Dữ liệu: 1 năm | BB({BB_WINDOW},{BB_STD}) | R:R 1:{RR_RATIO}")
    report_lines.append(f"  Entry  : Pending tại đỉnh/đáy nến breakout (ngoài BB {ATR_SL_MULT}×ATR buffer)")
    report_lines.append(f"  SL     : entry ± ATR×{ATR_SL_MULT}")
    report_lines.append(f"  TP     : entry ∓ risk × {RR_RATIO}")
    report_lines.append(f"  Check  : {FORWARD_BARS} nến tiếp theo")
    report_lines.append("=" * 65)

    for tf_label, tf_mt5, bars, window_h in [
        ("M15", mt5.TIMEFRAME_M15, BARS_1Y * 4, 15),
        ("H1",  mt5.TIMEFRAME_H1,  BARS_1Y,      24),
    ]:
        print(f"\n[{tf_label}] Đang tải dữ liệu {bars:,} nến...")
        df    = load_data(tf_mt5, bars)
        df    = apply_indicators(df)
        df_h1 = load_data(mt5.TIMEFRAME_H1, BARS_1Y)
        rev_arr_top, rev_arr_bot = get_daily_reversals(df_h1)

        print(f"[{tf_label}] Đang quét BB breakout + mô phỏng pending order ({len(df):,} nến)...")
        records = analyze_tf(df, rev_arr_top, rev_arr_bot, window_h)

        print(f"[{tf_label}] Đỉnh: {len(records['Đỉnh']):,} | Đáy: {len(records['Đáy']):,}")
        report_lines.append(build_report(records, tf_label))

    final = "\n".join(report_lines)
    print("\n" + final)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(final)

    print(f"\n✅ Báo cáo đã lưu: {OUTPUT_FILE}")
    mt5.shutdown()


if __name__ == "__main__":
    main()

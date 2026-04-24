"""
Vẽ charts minh họa chiến lược BB Breakout — GOLD
Output: results/charts/
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf8')

import os
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
from ta.volatility import BollingerBands, AverageTrueRange
from src.fetch_data import initialize_mt5

os.makedirs("results/charts", exist_ok=True)
GOLD_PIP = 0.10

# ── Dữ liệu EV từ phân tích ──────────────────────────────────────
h1_buy_bb = {
    '0–0.05%': (53.9, 46.1, 2.235, 55, 273),
    '0.05–0.1%': (60.0, 40.0, 2.600, 40, 199),
    '0.1–0.15%': (59.6, 40.4, 2.574, 65, 323),
    '0.15–0.2%': (62.7, 37.3, 2.761, 28, 142),
    '0.2–0.3%':  (72.3, 27.7, 3.340, 53, 268),
    '0.3–0.5%':  (67.7, 32.3, 3.063, 72, 359),
    '0.5–1.0%':  (63.1, 36.9, 2.786, 105, 526),
    '>1.0%':     (72.5, 27.5, 3.350, 150, 748),
}
h1_sell_bb = {
    '0–0.05%':   (54.8, 45.2, 2.310, 44, 222),
    '0.05–0.1%': (48.7, 51.3, 1.935, 41, 203),
    '0.1–0.15%': (46.5, 53.5, 1.789, 49, 246),
    '0.15–0.2%': (50.0, 50.0, 2.000, 50, 248),
    '0.2–0.3%':  (46.2, 53.8, 1.769, 45, 219),
    '0.3–0.5%':  (51.9, 48.1, 2.111, 65, 324),
    '0.5–1.0%':  (60.4, 39.6, 2.625, 95, 473),
    '>1.0%':     (70.0, 30.0, 3.200, 73, 365),
}
h1_buy_width = {
    '0.37–0.82%':  (54.0, 46.0, 2.237),
    '0.82–1.15%':  (66.9, 33.1, 3.014),
    '1.15–1.62%':  (74.1, 25.9, 3.446),
    '1.62–2.71%':  (60.1, 39.9, 2.609),
    '2.71–15%':    (60.0, 40.0, 2.600),
}
h1_buy_hour_ev = {
    '00–01': 4.000, '01–02': 3.385, '02–03': 2.818, '03–04': 3.667,
    '04–05': 2.500, '05–06': 3.364, '06–07': 2.500, '07–08': 3.000,
    '08–09': 3.000, '09–10': 2.913, '10–11': 3.345, '11–12': 3.080,
    '12–13': 3.320, '13–14': 2.200, '14–15': 1.640, '15–16': 1.909,
    '16–17': 2.000, '17–18': 3.263, '18–19': 2.310, '19–20': 2.643,
    '20–21': 1.400, '21–22': 2.231, '22–23': 2.474, '23–24': 2.125,
}
h1_sell_hour_ev = {
    '00–01': 1.951, '01–02': 2.714, '02–03': 1.727, '03–04': 2.405,
    '04–05': 1.308, '05–06': 2.310, '06–07': -0.700,'07–08': 2.000,
    '08–09': 2.600, '09–10': 1.615, '10–11': 2.733, '11–12': 2.673,
    '12–13': 1.923, '13–14': 2.000, '14–15': 1.897, '15–16': 2.310,
    '16–17': 1.750, '17–18': 2.652, '18–19': 2.429, '19–20': 3.250,
    '20–21': 2.462, '21–22': 1.690, '22–23': 0.756, '23–24': 1.483,
}

DARK  = '#1a1a2e'
CARD  = '#16213e'
BLUE  = '#0f3460'
GREEN = '#00d4aa'
RED   = '#ff6b6b'
GOLD  = '#ffd700'
WHITE = '#e0e0e0'
GRAY  = '#888888'
PURPLE= '#a855f7'

def style_ax(ax, title=''):
    ax.set_facecolor(CARD)
    ax.tick_params(colors=WHITE, labelsize=8)
    for spine in ax.spines.values():
        spine.set_edgecolor('#333355')
    if title:
        ax.set_title(title, color=GOLD, fontsize=10, fontweight='bold', pad=8)
    ax.grid(axis='y', color='#333355', linewidth=0.5, alpha=0.7)
    ax.grid(axis='x', visible=False)

# ══════════════════════════════════════════════════════════════════
# CHART 1 — EV theo BB% & Width (H1)
# ══════════════════════════════════════════════════════════════════
fig = plt.figure(figsize=(16, 10), facecolor=DARK)
fig.suptitle('GOLD BB Breakout — EV Analysis (Struct N=1 | R:R 1:5 | H1)',
             color=GOLD, fontsize=14, fontweight='bold', y=0.98)
gs = GridSpec(2, 2, figure=fig, hspace=0.45, wspace=0.35)

# 1a — EV by BB% (BUY)
ax1 = fig.add_subplot(gs[0, 0])
labels = list(h1_buy_bb.keys())
evs    = [v[2] for v in h1_buy_bb.values()]
colors = [GREEN if e >= 3.0 else (GOLD if e >= 2.5 else GRAY) for e in evs]
bars = ax1.bar(range(len(labels)), evs, color=colors, width=0.65, zorder=3)
ax1.axhline(2.5, color=GOLD, linestyle='--', linewidth=1, alpha=0.6, label='EV=2.5R')
ax1.axhline(3.0, color=GREEN, linestyle='--', linewidth=1, alpha=0.6, label='EV=3.0R')
for bar, ev in zip(bars, evs):
    ax1.text(bar.get_x()+bar.get_width()/2, ev+0.05, f'{ev:.2f}R',
             ha='center', va='bottom', color=WHITE, fontsize=7.5, fontweight='bold')
ax1.set_xticks(range(len(labels)))
ax1.set_xticklabels(labels, rotation=35, ha='right', fontsize=7.5)
ax1.set_ylabel('EV (R)', color=WHITE, fontsize=9)
ax1.legend(fontsize=7, labelcolor=WHITE, facecolor=BLUE, edgecolor='none')
style_ax(ax1, '📈 BUY H1 — EV theo BB% phá vỡ')

# 1b — EV by BB% (SELL)
ax2 = fig.add_subplot(gs[0, 1])
evs2   = [v[2] for v in h1_sell_bb.values()]
colors2= [GREEN if e >= 3.0 else (GOLD if e >= 2.5 else (GRAY if e >= 1.5 else RED)) for e in evs2]
bars2  = ax2.bar(range(len(labels)), evs2, color=colors2, width=0.65, zorder=3)
ax2.axhline(2.5, color=GOLD, linestyle='--', linewidth=1, alpha=0.6)
for bar, ev in zip(bars2, evs2):
    ax2.text(bar.get_x()+bar.get_width()/2, ev+0.05, f'{ev:.2f}R',
             ha='center', va='bottom', color=WHITE, fontsize=7.5, fontweight='bold')
ax2.set_xticks(range(len(labels)))
ax2.set_xticklabels(labels, rotation=35, ha='right', fontsize=7.5)
ax2.set_ylabel('EV (R)', color=WHITE, fontsize=9)
style_ax(ax2, '📉 SELL H1 — EV theo BB% phá vỡ')

# 1c — EV by Width (BUY)
ax3 = fig.add_subplot(gs[1, 0])
wlabels = list(h1_buy_width.keys())
wevs    = [v[2] for v in h1_buy_width.values()]
wcolors = [GREEN if e >= 3.0 else (GOLD if e >= 2.5 else GRAY) for e in wevs]
wbars   = ax3.bar(range(len(wlabels)), wevs, color=wcolors, width=0.6, zorder=3)
ax3.axhline(2.5, color=GOLD, linestyle='--', linewidth=1, alpha=0.6)
for bar, ev in zip(wbars, wevs):
    ax3.text(bar.get_x()+bar.get_width()/2, ev+0.05, f'{ev:.2f}R',
             ha='center', va='bottom', color=WHITE, fontsize=8, fontweight='bold')
ax3.set_xticks(range(len(wlabels)))
ax3.set_xticklabels(wlabels, rotation=25, ha='right', fontsize=8)
ax3.set_ylabel('EV (R)', color=WHITE, fontsize=9)
# Highlight sweet spot
ax3.axvspan(1.7, 2.3, alpha=0.12, color=GREEN, label='Sweet spot\n1.15–1.62%')
ax3.legend(fontsize=7, labelcolor=WHITE, facecolor=BLUE, edgecolor='none')
style_ax(ax3, '🎯 BUY H1 — EV theo BB Width%')

# 1d — TP pip by BB%
ax4 = fig.add_subplot(gs[1, 1])
tp_pips  = [v[4] for v in h1_buy_bb.values()]
sl_pips  = [v[3] for v in h1_buy_bb.values()]
x = np.arange(len(labels))
b1 = ax4.bar(x - 0.2, sl_pips, width=0.35, color=RED,   label='SL pip', zorder=3, alpha=0.85)
b2 = ax4.bar(x + 0.2, tp_pips, width=0.35, color=GREEN, label='TP pip', zorder=3, alpha=0.85)
for bar, v in zip(b1, sl_pips):
    ax4.text(bar.get_x()+bar.get_width()/2, v+5, str(v), ha='center', fontsize=6.5, color=WHITE)
for bar, v in zip(b2, tp_pips):
    ax4.text(bar.get_x()+bar.get_width()/2, v+5, str(v), ha='center', fontsize=6.5, color=WHITE)
ax4.set_xticks(x)
ax4.set_xticklabels(labels, rotation=35, ha='right', fontsize=7.5)
ax4.set_ylabel('Pip', color=WHITE, fontsize=9)
ax4.legend(fontsize=8, labelcolor=WHITE, facecolor=BLUE, edgecolor='none')
style_ax(ax4, '📏 BUY H1 — SL pip vs TP pip theo BB%')

plt.savefig('results/charts/chart1_ev_analysis.png', dpi=150, bbox_inches='tight', facecolor=DARK)
plt.close()
print("✅ Chart 1 saved")

# ══════════════════════════════════════════════════════════════════
# CHART 2 — EV heatmap theo giờ (BUY vs SELL H1)
# ══════════════════════════════════════════════════════════════════
fig2, (ax_b, ax_s) = plt.subplots(2, 1, figsize=(16, 7), facecolor=DARK)
fig2.suptitle('GOLD H1 — EV theo Khung Giờ UTC+7 (Struct N=1 | R:R 1:5)',
              color=GOLD, fontsize=13, fontweight='bold')

hours = list(h1_buy_hour_ev.keys())
buy_ev  = list(h1_buy_hour_ev.values())
sell_ev = list(h1_sell_hour_ev.values())

def ev_color(ev):
    if ev >= 3.5:  return '#00ff88'
    if ev >= 3.0:  return '#00d4aa'
    if ev >= 2.5:  return '#ffd700'
    if ev >= 2.0:  return '#f0a030'
    if ev >= 1.5:  return '#cc8800'
    if ev >= 1.0:  return '#888888'
    return '#cc2222'

for ax, evs, title, direction in [
    (ax_b, buy_ev,  '📉 BUY — EV per trade by Hour', 'BUY'),
    (ax_s, sell_ev, '📈 SELL — EV per trade by Hour', 'SELL'),
]:
    ax.set_facecolor(CARD)
    bars = ax.bar(range(24), evs, color=[ev_color(e) for e in evs], width=0.75, zorder=3)
    ax.axhline(3.0, color='#00ff88', linestyle='--', linewidth=1, alpha=0.5, label='EV=3.0R')
    ax.axhline(2.5, color=GOLD,      linestyle='--', linewidth=1, alpha=0.5, label='EV=2.5R')
    ax.axhline(0,   color=WHITE,     linewidth=0.5, alpha=0.3)
    for bar, ev in zip(bars, evs):
        ypos = ev + 0.05 if ev >= 0 else ev - 0.18
        ax.text(bar.get_x()+bar.get_width()/2, ypos, f'{ev:.2f}',
                ha='center', va='bottom', color=WHITE, fontsize=6.5, fontweight='bold')
    ax.set_xticks(range(24))
    ax.set_xticklabels([h.split('–')[0] for h in hours], fontsize=7.5, color=WHITE)
    ax.set_ylabel('EV (R)', color=WHITE, fontsize=9)
    ax.set_title(title, color=GOLD, fontsize=10, fontweight='bold', pad=6)
    ax.legend(fontsize=7, labelcolor=WHITE, facecolor=BLUE, edgecolor='none', loc='upper right')
    ax.grid(axis='y', color='#333355', linewidth=0.5, alpha=0.7)
    for spine in ax.spines.values():
        spine.set_edgecolor('#333355')
    ax.tick_params(colors=WHITE)

# Shade best hours
for h_idx in [0,1,2,3,5,7,8,9,10,11,12,17]:
    ax_b.axvspan(h_idx-0.4, h_idx+0.4, alpha=0.08, color=GREEN)
for h_idx in [1,5,8,10,11,17,19,20]:
    ax_s.axvspan(h_idx-0.4, h_idx+0.4, alpha=0.08, color=RED)

plt.tight_layout(rect=[0, 0, 1, 0.95])
plt.savefig('results/charts/chart2_hourly_ev.png', dpi=150, bbox_inches='tight', facecolor=DARK)
plt.close()
print("✅ Chart 2 saved")

# ══════════════════════════════════════════════════════════════════
# CHART 3 — Ví dụ thực tế: nến H1 + BB + entry/SL/TP
# ══════════════════════════════════════════════════════════════════
initialize_mt5()
rates = mt5.copy_rates_from_pos("GOLD", mt5.TIMEFRAME_H1, 0, 500)
df = pd.DataFrame(rates)
df['time'] = pd.to_datetime(df['time'], unit='s')
df.set_index('time', inplace=True)

bb = BollingerBands(close=df['close'], window=20, window_dev=2)
df['BB_U'] = bb.bollinger_hband()
df['BB_L'] = bb.bollinger_lband()
df['BB_M'] = bb.bollinger_mavg()
df['ATR']  = AverageTrueRange(df['high'], df['low'], df['close'], window=14).average_true_range()
df['BB_Down'] = ((df['BB_L'] - df['low']) / df['BB_L'] * 100).clip(lower=0)

# Tìm BUY signal tốt: BB% 0.2–0.3%, có nến kế tiếp
buy_signals = df[(df['BB_Down'] >= 0.2) & (df['BB_Down'] <= 0.3)].index
chosen = None
for sig in reversed(buy_signals[-30:]):
    loc = df.index.get_loc(sig)
    if loc + 30 < len(df):
        chosen = loc
        break

if chosen is not None:
    window = 40
    start  = max(0, chosen - 15)
    end    = min(len(df), chosen + window)
    sub    = df.iloc[start:end].copy()
    sig_i  = chosen - start

    entry  = sub.iloc[sig_i]['low']
    sl_raw = sub.iloc[sig_i+1]['low'] if sig_i+1 < len(sub) else entry - sub.iloc[sig_i]['ATR']*0.5
    risk   = max(entry - sl_raw, sub.iloc[sig_i]['ATR'] * 0.05)
    sl     = entry - risk
    tp     = entry + risk * 5

    fig3, ax = plt.subplots(figsize=(16, 8), facecolor=DARK)
    ax.set_facecolor(CARD)

    # Vẽ nến
    for j, (t, row) in enumerate(sub.iterrows()):
        color = GREEN if row['close'] >= row['open'] else RED
        ax.plot([j, j], [row['low'], row['high']], color=color, linewidth=0.8)
        ax.add_patch(plt.Rectangle(
            (j-0.35, min(row['open'], row['close'])),
            0.7, abs(row['close']-row['open']),
            color=color, zorder=3
        ))

    x = np.arange(len(sub))
    ax.plot(x, sub['BB_U'].values, color='#5599ff', linewidth=1.2, label='BB Upper', alpha=0.8)
    ax.plot(x, sub['BB_L'].values, color='#ff9944', linewidth=1.2, label='BB Lower', alpha=0.8)
    ax.plot(x, sub['BB_M'].values, color=GRAY,      linewidth=0.8, linestyle='--', label='BB Mid', alpha=0.6)
    ax.fill_between(x, sub['BB_L'].values, sub['BB_U'].values, alpha=0.04, color='#5599ff')

    # Entry / SL / TP lines
    x_sig = sig_i
    ax.axhline(entry, color=GOLD,  linewidth=1.5, linestyle='-',  alpha=0.9, label=f'Entry={entry:.1f}')
    ax.axhline(sl,    color=RED,   linewidth=1.5, linestyle='--', alpha=0.9, label=f'SL={sl:.1f}  ({round(risk/GOLD_PIP)}pip)')
    ax.axhline(tp,    color=GREEN, linewidth=1.5, linestyle='--', alpha=0.9, label=f'TP={tp:.1f}  ({round(risk*5/GOLD_PIP)}pip)')

    # Risk/TP zone shading
    ax.fill_between(range(x_sig, min(x_sig+30, len(sub))),
                    entry, sl, alpha=0.12, color=RED)
    ax.fill_between(range(x_sig, min(x_sig+30, len(sub))),
                    entry, tp, alpha=0.10, color=GREEN)

    # Signal marker
    ax.annotate('🎯 ENTRY\n(BB breakout)', xy=(x_sig, entry),
                xytext=(x_sig+3, entry - risk*2.5),
                color=GOLD, fontsize=9, fontweight='bold',
                arrowprops=dict(arrowstyle='->', color=GOLD, lw=1.5))

    # Struct SL nến kế tiếp
    if sig_i+1 < len(sub):
        ax.annotate(f'SL = Low[+1]\n= {sl:.1f}', xy=(x_sig+1, sl),
                    xytext=(x_sig+4, sl - risk*1.2),
                    color=RED, fontsize=8,
                    arrowprops=dict(arrowstyle='->', color=RED, lw=1.2))

    # Labels
    xticks = range(0, len(sub), 4)
    ax.set_xticks(xticks)
    ax.set_xticklabels([sub.index[i].strftime('%m/%d %H:%M') for i in xticks],
                       rotation=30, ha='right', fontsize=7, color=WHITE)
    ax.tick_params(colors=WHITE)
    for spine in ax.spines.values():
        spine.set_edgecolor('#333355')
    ax.set_ylabel('GOLD Price ($)', color=WHITE, fontsize=10)
    ax.set_title(f'GOLD H1 — Ví dụ BUY Setup: BB% = {sub.iloc[sig_i]["BB_Down"]:.2f}%  |  Struct N=1  |  R:R 1:5',
                 color=GOLD, fontsize=11, fontweight='bold', pad=10)
    ax.legend(loc='upper left', fontsize=8, labelcolor=WHITE, facecolor=BLUE,
              edgecolor='#333366', framealpha=0.9)
    ax.grid(axis='y', color='#333355', linewidth=0.5, alpha=0.6)

    plt.tight_layout()
    plt.savefig('results/charts/chart3_example_trade.png', dpi=150, bbox_inches='tight', facecolor=DARK)
    plt.close()
    print("✅ Chart 3 saved")
else:
    print("⚠️  Không tìm thấy signal phù hợp cho chart 3")

mt5.shutdown()
print("\n✅ Tất cả charts đã lưu vào results/charts/")

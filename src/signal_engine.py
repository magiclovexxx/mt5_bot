import MetaTrader5 as mt5
import pandas as pd
from src.indicators import apply_indicators
import pandas_ta as ta

class SignalEngine:
    def __init__(self, symbol="GOLD"):
        self.symbol = symbol

    def get_latest_data(self, timeframe, count=100):
        rates = mt5.copy_rates_from_pos(self.symbol, timeframe, 0, count)
        if rates is None: return None
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)
        return df

    def check_divergence(self, df, reversal_type):
        if df is None or len(df) < 30: return False, 0, 0
        df['RSI_14'] = ta.rsi(df['close'], length=14)
        
        i = len(df) - 1
        curr_rsi = df.iloc[i]['RSI_14']
        curr_high = df.iloc[i]['high']
        curr_low = df.iloc[i]['low']
        
        if reversal_type == 'Đỉnh' and curr_rsi > 60:
            prev_window = df.iloc[-30:-1]
            prev_high = prev_window['high'].max()
            prev_rsi = df.loc[prev_window['high'].idxmax(), 'RSI_14']
            if curr_high > prev_high and curr_rsi < prev_rsi:
                return True, round(curr_high - prev_high, 2), round(prev_rsi - curr_rsi, 2)
        elif reversal_type == 'Đáy' and curr_rsi < 40:
            prev_window = df.iloc[-30:-1]
            prev_low = prev_window['low'].min()
            prev_rsi = df.loc[prev_window['low'].idxmin(), 'RSI_14']
            if curr_low < prev_low and curr_rsi > prev_rsi:
                return True, round(prev_low - curr_low, 2), round(curr_rsi - prev_rsi, 2)
        return False, 0, 0

    def scan_for_signals(self):
        # 1. Check H1 Context
        df_h1 = self.get_latest_data(mt5.TIMEFRAME_H1, 100)
        if df_h1 is None: return None
        df_h1 = apply_indicators(df_h1)
        
        last_h1 = df_h1.iloc[-1]
        h1_reversal_zone = None
        if last_h1['high'] >= last_h1['BB_Upper']: h1_reversal_zone = 'Đỉnh'
        elif last_h1['low'] <= last_h1['BB_Lower']: h1_reversal_zone = 'Đáy'
        
        if not h1_reversal_zone: return None # H1 chưa vào vùng cực trị
        
        # 2. Check M5/M15 Confirmation
        df_m5 = self.get_latest_data(mt5.TIMEFRAME_M5, 60)
        has_div_m5, p_diff, r_diff = self.check_divergence(df_m5, h1_reversal_zone)
        
        # 3. Check Volume Climax (M15)
        df_m15 = self.get_latest_data(mt5.TIMEFRAME_M15, 60)
        vol_avg = df_m15['tick_volume'].tail(20).mean()
        vol_spike = df_m15.iloc[-1]['tick_volume'] > 1.5 * vol_avg
        
        if has_div_m5 or vol_spike:
            entry_price = last_h1['close']
            h1_high = last_h1['high']
            h1_low = last_h1['low']
            
            # Tính toán SL: Cách Đỉnh/Đáy nến H1 khoảng 1 giá (buffer)
            if h1_reversal_zone == 'Đỉnh':
                sl_price = round(h1_high + 1.5, 2)
                risk = round(sl_price - entry_price, 2)
                tp_price = round(entry_price - (risk * 2), 2)
                action = "SELL (BẮT ĐỈNH)"
            else:
                sl_price = round(h1_low - 1.5, 2)
                risk = round(entry_price - sl_price, 2)
                tp_price = round(entry_price + (risk * 2), 2)
                action = "BUY (BẮT ĐÁY)"
            
            return {
                'type': action,
                'time': datetime.now().strftime("%H:%M"),
                'price': entry_price,
                'h1_status': f"Vùng cực trị H1 ({h1_reversal_zone})",
                'm5_status': f"Phân kỳ M5 (P-Diff: {p_diff})" if has_div_m5 else "Hội tụ giá",
                'vol_status': "Đột biến (Climax)" if vol_spike else "Bình thường",
                'action': f"Vào lệnh {action} ngay hoặc đợi RSI M1 cực trị.",
                'entry': entry_price,
                'sl': sl_price,
                'tp': tp_price,
                'rr': "1:2",
                'prob': "55-60% (Hội tụ đa khung)"
            }
        
        return None
from datetime import datetime

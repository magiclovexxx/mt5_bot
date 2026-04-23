import pandas as pd
import numpy as np

class BacktestEngine:
    def __init__(self, df_m5, df_m15, df_h1, initial_balance=10000):
        self.df_m5 = df_m5
        self.df_m15 = df_m15
        self.df_h1 = df_h1
        self.balance = initial_balance
        self.trades = []

    def run(self):
        print(f"Bắt đầu backtest trên {len(self.df_m5)} nến M5...")
        
        # Merge hoặc mapping dữ liệu H1, M15 vào M5 để check bối cảnh
        # Để đơn giản, ta sẽ dùng index thời gian để tra cứu
        
        for i in range(100, len(self.df_m5)):
            current_time = self.df_m5.index[i]
            
            # 1. Tìm bối cảnh H1 tại thời điểm này
            h1_idx = self.df_h1.index.asof(current_time)
            if pd.isna(h1_idx): continue
            h1_row = self.df_h1.loc[h1_idx]
            
            h1_zone = None
            if h1_row['high'] >= h1_row['BB_Upper']: h1_zone = 'Đỉnh'
            elif h1_row['low'] <= h1_row['BB_Lower']: h1_zone = 'Đáy'
            
            if not h1_zone: continue
            
            # 2. Check M5 Divergence (Logic nhanh)
            m5_window = self.df_m5.iloc[i-30:i+1]
            has_div = self._check_m5_div(m5_window, h1_zone)
            
            if has_div:
                # 3. Vào lệnh
                entry_price = self.df_m5.iloc[i]['close']
                if h1_zone == 'Đỉnh':
                    sl = h1_row['high'] + 1.5
                    tp = entry_price - (sl - entry_price) * 2
                else:
                    sl = h1_row['low'] - 1.5
                    tp = entry_price + (entry_price - sl) * 2
                
                self._process_trade(i, entry_price, sl, tp, h1_zone)
                
        return self._summarize()

    def _check_m5_div(self, df, zone):
        # Logic phân kỳ đơn giản cho backtest
        if len(df) < 20: return False
        # Sử dụng RSI đã tính sẵn nếu có, hoặc tính nhanh
        # Giả định RSI đã có trong df_m5
        curr_rsi = df.iloc[-1]['RSI_14']
        curr_price = df.iloc[-1]['high'] if zone == 'Đỉnh' else df.iloc[-1]['low']
        
        if zone == 'Đỉnh' and curr_rsi > 60:
            prev_peak = df.iloc[:-1]['high'].max()
            prev_rsi = df.loc[df.iloc[:-1]['high'].idxmax(), 'RSI_14']
            return curr_price > prev_peak and curr_rsi < prev_rsi
        elif zone == 'Đáy' and curr_rsi < 40:
            prev_valley = df.iloc[:-1]['low'].min()
            prev_rsi = df.loc[df.iloc[:-1]['low'].idxmin(), 'RSI_14']
            return curr_price < prev_valley and curr_rsi > prev_rsi
        return False

    def _process_trade(self, start_idx, entry, sl, tp, zone):
        # Theo dõi các nến M5 tiếp theo để check SL/TP
        for j in range(start_idx + 1, len(self.df_m5)):
            high = self.df_m5.iloc[j]['high']
            low = self.df_m5.iloc[j]['low']
            
            if zone == 'Đỉnh': # Lệnh SELL
                if high >= sl:
                    self.trades.append({'res': 'Loss', 'profit': -100, 'time': self.df_m5.index[j]})
                    return
                if low <= tp:
                    self.trades.append({'res': 'Win', 'profit': 200, 'time': self.df_m5.index[j]})
                    return
            else: # Lệnh BUY
                if low <= sl:
                    self.trades.append({'res': 'Loss', 'profit': -100, 'time': self.df_m5.index[j]})
                    return
                if high >= tp:
                    self.trades.append({'res': 'Win', 'profit': 200, 'time': self.df_m5.index[j]})
                    return

    def _summarize(self):
        if not self.trades: return "Không có lệnh nào được thực hiện."
        df_trades = pd.DataFrame(self.trades)
        win_rate = (df_trades['res'] == 'Win').mean() * 100
        total_profit = df_trades['profit'].sum()
        
        report = []
        report.append(f"=== KẾT QUẢ BACKTEST HỆ THỐNG ===")
        report.append(f"Tổng số lệnh: {len(df_trades)}")
        report.append(f"Tỉ lệ Win Rate: {round(win_rate, 2)}%")
        report.append(f"Tổng lợi nhuận (giả định rủi ro 100$/lệnh): {total_profit}$")
        report.append(f"Profit Factor: {round(df_trades[df_trades['profit']>0]['profit'].sum() / abs(df_trades[df_trades['profit']<0]['profit'].sum()), 2)}")
        
        return "\n".join(report)

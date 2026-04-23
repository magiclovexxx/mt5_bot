import pandas as pd
import numpy as np

def analyze_volatility_and_reversals(df):
    """
    Phân tích độ biến động, nến đảo chiều, khối lượng, RSI Divergence, S/R và tỉ lệ R:R.
    """
    df = df.dropna().copy()
    
    # 1. Indicators
    df['ATR_MA_50'] = df['ATR_14'].rolling(window=50).mean()
    df['High_Volatility'] = df['ATR_14'] > (1.5 * df['ATR_MA_50'])
    df['Vol_MA_20'] = df['tick_volume'].rolling(window=20).mean()
    df['Volume_Spike'] = df['tick_volume'] > (1.5 * df['Vol_MA_20'])

    # 2. Price Action
    body = abs(df['close'] - df['open'])
    candle_range = df['high'] - df['low']
    df['Is_PinBar'] = (candle_range > 3 * body) & (candle_range > 0)
    df['Is_Bullish_Engulfing'] = (df['close'] > df['open']) & (df['close'].shift(1) < df['open'].shift(1)) & \
                                 (df['close'] > df['open'].shift(1)) & (df['open'] < df['close'].shift(1))
    df['Is_Bearish_Engulfing'] = (df['close'] < df['open']) & (df['close'].shift(1) > df['open'].shift(1)) & \
                                 (df['close'] < df['open'].shift(1)) & (df['open'] > df['close'].shift(1))

    # 3. Pivot Points
    df['Date'] = df.index.date
    daily_ohlc = df.resample('D').agg({'high': 'max', 'low': 'min', 'close': 'last'})
    daily_ohlc['Prev_H'] = daily_ohlc['high'].shift(1)
    daily_ohlc['Prev_L'] = daily_ohlc['low'].shift(1)
    daily_ohlc['Prev_C'] = daily_ohlc['close'].shift(1)
    daily_ohlc['P'] = (daily_ohlc['Prev_H'] + daily_ohlc['Prev_L'] + daily_ohlc['Prev_C']) / 3
    daily_ohlc['R1'] = 2 * daily_ohlc['P'] - daily_ohlc['Prev_L']
    daily_ohlc['S1'] = 2 * daily_ohlc['P'] - daily_ohlc['Prev_H']
    daily_ohlc['R2'] = daily_ohlc['P'] + (daily_ohlc['Prev_H'] - daily_ohlc['Prev_L'])
    daily_ohlc['S2'] = daily_ohlc['P'] - (daily_ohlc['Prev_H'] - daily_ohlc['Prev_L'])
    df['Pivot_P'] = df['Date'].map(daily_ohlc['P'])
    df['Pivot_R1'] = df['Date'].map(daily_ohlc['R1'])
    df['Pivot_S1'] = df['Date'].map(daily_ohlc['S1'])
    df['Pivot_R2'] = df['Date'].map(daily_ohlc['R2'])
    df['Pivot_S2'] = df['Date'].map(daily_ohlc['S2'])

    # 4. Reversal Detection
    df['Reversal_Type'] = 'None'
    for date, group in df.groupby('Date'):
        if not group.empty:
            df.loc[group['high'].idxmax(), 'Reversal_Type'] = 'Đỉnh'
            df.loc[group['low'].idxmin(), 'Reversal_Type'] = 'Đáy'

    # 5. RSI Divergence
    df['RSI_Div'] = 'None'
    for i in range(30, len(df)):
        current_idx = df.index[i]
        if df.iloc[i]['Reversal_Type'] == 'Đỉnh':
            prev_window = df.iloc[i-30:i]
            prev_peak_idx = prev_window['high'].idxmax()
            if df.iloc[i]['high'] > df.loc[prev_peak_idx, 'high'] and df.iloc[i]['RSI_14'] < df.loc[prev_peak_idx, 'RSI_14']:
                df.loc[current_idx, 'RSI_Div'] = 'Bearish Divergence'
        elif df.iloc[i]['Reversal_Type'] == 'Đáy':
            prev_window = df.iloc[i-30:i]
            prev_valley_idx = prev_window['low'].idxmin()
            if df.iloc[i]['low'] < df.loc[prev_valley_idx, 'low'] and df.iloc[i]['RSI_14'] > df.loc[prev_valley_idx, 'RSI_14']:
                df.loc[current_idx, 'RSI_Div'] = 'Bullish Divergence'

    # 6. Tỉ lệ R:R (Backtest mô phỏng)
    summary = []
    reversals_df = df[df['Reversal_Type'] != 'None'].copy()
    
    for idx, row in reversals_df.iterrows():
        entry_price = row['close']
        reversal_type = row['Reversal_Type']
        atr = row['ATR_14']
        
        # Stop Loss: Đặt cách Đỉnh/Đáy một khoảng ATR * 0.5 (Tối thiểu 100 points)
        sl_buffer = max(atr * 0.5, 1.0)
        sl_price = (row['high'] + sl_buffer) if reversal_type == 'Đỉnh' else (row['low'] - sl_buffer)
        risk = abs(entry_price - sl_price)
        
        # Tìm Reward tối đa trong vòng 24 nến tiếp theo (1 ngày H1 hoặc 6h M15)
        # Lấy slice dữ liệu sau nến hiện tại
        current_pos = df.index.get_loc(idx)
        future_data = df.iloc[current_pos + 1 : current_pos + 25]
        
        max_reward = 0
        if not future_data.empty:
            if reversal_type == 'Đỉnh':
                # Tìm giá thấp nhất trước khi chạm SL
                for f_idx, f_row in future_data.iterrows():
                    if f_row['high'] >= sl_price: break # Hit SL
                    move = entry_price - f_row['low']
                    max_reward = max(max_reward, move)
            else:
                # Tìm giá cao nhất trước khi chạm SL
                for f_idx, f_row in future_data.iterrows():
                    if f_row['low'] <= sl_price: break # Hit SL
                    move = f_row['high'] - entry_price
                    max_reward = max(max_reward, move)
        
        rr_ratio = max_reward / risk if risk > 0 else 0
        
        pattern = "None"
        if row['Is_PinBar']: pattern = "Pin Bar"
        elif row['Is_Bullish_Engulfing'] or row['Is_Bearish_Engulfing']: pattern = "Engulfing"
        
        near_sr = "None"
        price = row['high'] if reversal_type == 'Đỉnh' else row['low']
        sr_levels = [row['Pivot_P'], row['Pivot_R1'], row['Pivot_S1'], row['Pivot_R2'], row['Pivot_S2']]
        sr_names = ['Pivot', 'R1', 'S1', 'R2', 'S2']
        for val, name in zip(sr_levels, sr_names):
            if pd.notnull(val) and abs(price - val) < 1.0:
                near_sr = name
                break
        
        summary.append({
            'Time': idx,
            'Type': reversal_type,
            'Close_Price': entry_price,
            'high': row['high'],
            'low': row['low'],
            'RSI': round(row['RSI_14'], 2),
            'STOCH_K': round(row['STOCH_K'], 2),
            'Risk': round(risk, 2),
            'Max_Reward': round(max_reward, 2),
            'RR_Ratio': round(rr_ratio, 2),
            'Pattern': pattern,
            'Divergence': row['RSI_Div'],
            'Near_SR': near_sr,
            'Volume_Spike': row['Volume_Spike'],
            'BB_Lower': row['BB_Lower'],
            'BB_Upper': row['BB_Upper']
        })
        
    return df, pd.DataFrame(summary)

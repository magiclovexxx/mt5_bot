import pandas as pd
import numpy as np
from scipy.signal import find_peaks

def analyze_volatility_and_reversals(df):
    """
    Finds points of high volatility and trend reversals.
    - High Volatility: ATR is significantly higher than its average.
    - Bullish Reversal: Price reaches a valley (local minimum) during a downtrend (Price < EMA 50)
    - Bearish Reversal: Price reaches a peak (local maximum) during an uptrend (Price > EMA 50)
    """
    df = df.dropna().copy()
    
    # 1. High Volatility calculation using ATR
    # High volatility is when ATR is 1.5x higher than its 50-period moving average
    df['ATR_MA_50'] = df['ATR_14'].rolling(window=50).mean()
    df['High_Volatility'] = df['ATR_14'] > (1.5 * df['ATR_MA_50'])

    # 2. Find Trend Reversals (Daily High and Low)
    df['Date'] = df.index.date
    daily_groups = df.groupby('Date')
    
    df['Reversal_Type'] = 'None'
    
    for date, group in daily_groups:
        # Lấy index của nến có giá cao nhất và thấp nhất trong ngày
        idx_max = group['high'].idxmax()
        idx_min = group['low'].idxmin()
        
        df.loc[idx_max, 'Reversal_Type'] = 'Bearish Reversal (Daily Peak)'
        df.loc[idx_min, 'Reversal_Type'] = 'Bullish Reversal (Daily Valley)'

    # 3. Extract conditions at Reversals
    reversals_df = df[df['Reversal_Type'] != 'None'].copy()
    
    summary = []
    for idx, row in reversals_df.iterrows():
        summary.append({
            'Time': idx,
            'Type': row['Reversal_Type'],
            'Close_Price': row['close'],
            'RSI': round(row['RSI_14'], 2),
            'ATR': round(row['ATR_14'], 5),
            'BB_Lower': round(row['BB_Lower'], 5) if 'BB_Lower' in row else None,
            'BB_Upper': round(row['BB_Upper'], 5) if 'BB_Upper' in row else None,
            'Distance_to_EMA50': round(row['close'] - row['EMA_50'], 5),
            'High_Volatility': row['High_Volatility']
        })
        
    return df, pd.DataFrame(summary)

import pandas as pd
import pandas_ta as ta

def apply_indicators(df):
    """
    Applies Bollinger Bands, RSI, EMA 10/50/200, and ATR.
    """
    if df.empty:
        return df
        
    # Bollinger Bands (20, 2)
    bb = df.ta.bbands(length=20, std=2)
    if bb is not None:
        df = pd.concat([df, bb], axis=1)
        # Rename columns for easier access
        df.rename(columns={
            'BBL_20_2.0': 'BB_Lower',
            'BBM_20_2.0': 'BB_Middle',
            'BBU_20_2.0': 'BB_Upper',
            'BBB_20_2.0': 'BB_Bandwidth',
            'BBP_20_2.0': 'BB_Percent'
        }, inplace=True)

    # RSI (14)
    df['RSI_14'] = df.ta.rsi(length=14)

    # EMAs
    df['EMA_10'] = df.ta.ema(length=10)
    df['EMA_50'] = df.ta.ema(length=50)
    df['EMA_200'] = df.ta.ema(length=200)

    # ATR (14) for volatility measurement
    df['ATR_14'] = df.ta.atr(length=14)

    return df

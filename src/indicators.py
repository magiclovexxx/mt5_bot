import pandas as pd
try:
    import pandas_ta as ta
except ImportError:
    ta = None

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
        # Rename columns dynamically to handle different pandas_ta naming conventions
        for col in bb.columns:
            if col.startswith('BBL_'): df.rename(columns={col: 'BB_Lower'}, inplace=True)
            if col.startswith('BBM_'): df.rename(columns={col: 'BB_Middle'}, inplace=True)
            if col.startswith('BBU_'): df.rename(columns={col: 'BB_Upper'}, inplace=True)
            if col.startswith('BBB_'): df.rename(columns={col: 'BB_Bandwidth'}, inplace=True)
            if col.startswith('BBP_'): df.rename(columns={col: 'BB_Percent'}, inplace=True)

    # RSI (14)
    df['RSI_14'] = df.ta.rsi(length=14)

    # EMAs
    df['EMA_10'] = df.ta.ema(length=10)
    df['EMA_50'] = df.ta.ema(length=50)
    df['EMA_200'] = df.ta.ema(length=200)

    # ATR (14) for volatility measurement
    df['ATR_14'] = df.ta.atr(length=14)

    # Stochastic (9, 3, 3)
    stoch = df.ta.stoch(k=9, d=3, smooth_k=3)
    if stoch is not None:
        df = pd.concat([df, stoch], axis=1)
        # Rename stochastic columns for clarity
        for col in stoch.columns:
            if col.startswith('STOCHk_'): df.rename(columns={col: 'STOCH_K'}, inplace=True)
            if col.startswith('STOCHd_'): df.rename(columns={col: 'STOCH_D'}, inplace=True)

    return df

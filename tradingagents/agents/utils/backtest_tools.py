import json
import logging
import traceback
from typing import Optional

import pandas as pd
import yfinance as yf
from langchain_core.tools import tool

from tradingagents.dataflows.symbol_utils import normalize_symbol

logger = logging.getLogger(__name__)

@tool
def run_historical_backtest(ticker: str, condition_query: str, forward_days: int = 5) -> str:
    """
    Run a historical backtest to calculate probabilities of a scenario using 10 years of data.
    You MUST provide the condition_query as a valid Pandas string query.
    Available columns:
        - Open, High, Low, Close, Volume
        - SMA_20, SMA_50, SMA_200
        - RSI_14
        - MACD, MACD_Signal, MACD_Hist
    
    Example query string: "SMA_50 < SMA_200 and RSI_14 > 60"
    
    Args:
        ticker: The stock or asset ticker (e.g. 'AAPL', 'SI=F').
        condition_query: The boolean condition string to evaluate.
        forward_days: Number of days forward to evaluate the price movement (default 5).
        
    Returns:
        A string describing the number of occurrences, probability of increase/decrease, and average return.
    """
    try:
        norm_ticker = normalize_symbol(ticker)
        # Fetch 10 years of data
        df = yf.Ticker(norm_ticker).history(period="10y")
        if df.empty or len(df) < 200:
            return f"Not enough historical data for {ticker}."

        # Calculate Indicators
        df['SMA_20'] = df['Close'].rolling(window=20).mean()
        df['SMA_50'] = df['Close'].rolling(window=50).mean()
        df['SMA_200'] = df['Close'].rolling(window=200).mean()

        # RSI 14
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI_14'] = 100 - (100 / (1 + rs))

        # MACD
        ema12 = df['Close'].ewm(span=12, adjust=False).mean()
        ema26 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = ema12 - ema26
        df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']

        # Forward return
        df[f'Return_{forward_days}d'] = df['Close'].shift(-forward_days) / df['Close'] - 1.0

        # Drop NaNs before querying
        df_clean = df.dropna()

        # Query the condition
        matches = df_clean.query(condition_query)
        total_matches = len(matches)

        if total_matches == 0:
            return f"Backtest found 0 occurrences matching condition: '{condition_query}' over the last 10 years."

        positive_returns = len(matches[matches[f'Return_{forward_days}d'] > 0])
        negative_returns = len(matches[matches[f'Return_{forward_days}d'] < 0])

        prob_up = (positive_returns / total_matches) * 100
        prob_down = (negative_returns / total_matches) * 100
        avg_return = matches[f'Return_{forward_days}d'].mean() * 100

        result = (
            f"Backtest Results for {ticker} over the last 10 years:\n"
            f"Condition: {condition_query}\n"
            f"Occurrences found: {total_matches}\n"
            f"Probability of price increase after {forward_days} days: {prob_up:.2f}%\n"
            f"Probability of price decrease after {forward_days} days: {prob_down:.2f}%\n"
            f"Average {forward_days}-day return: {avg_return:.2f}%\n"
        )
        return result

    except Exception as e:
        logger.error(f"Backtest error: {e}")
        return f"Failed to run backtest with query '{condition_query}'. Ensure the query is valid pandas syntax. Error: {str(e)}"

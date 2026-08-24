import sys
import os
from dotenv import load_dotenv

load_dotenv("d:/TradingAgents/.env")

from tradingagents.dataflows.stocktwits import fetch_stocktwits_messages
from tradingagents.dataflows.polymarket import get_prediction_markets
from tradingagents.dataflows.fred import get_macro_data

print("--- STOCKTWITS ---")
try:
    print(fetch_stocktwits_messages("XAGUSD"))
except Exception as e:
    print("Error:", e)

print("\n--- POLYMARKET ---")
try:
    print(get_prediction_markets("Silver", 5))
except Exception as e:
    print("Error:", e)

print("\n--- FRED ---")
try:
    print(get_macro_data("10y_treasury", "2026-08-24"))
except Exception as e:
    print("Error:", e)

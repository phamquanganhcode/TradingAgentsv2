from tradingagents.dataflows.stocktwits import fetch_stocktwits_messages
ticker = "SI=F"
print(f"Fetching StockTwits data for {ticker} (should map to SLV)...")
result = fetch_stocktwits_messages(ticker, limit=10)
print("\n=== RESULT ===")
print(result)

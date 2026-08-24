from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph.trading_graph import TradingAgentsGraph
import os
from datetime import datetime

# DEFAULT_CONFIG already applies TRADINGAGENTS_* env-var overrides
# (llm_provider, deep_think_llm, quick_think_llm, backend_url, etc.),
# so users can switch models or endpoints purely via .env without
# editing this script. Override individual keys here only when you
# want a hard-coded value that should ignore the environment.
config = DEFAULT_CONFIG.copy()

# Initialize with custom config
ta = TradingAgentsGraph(debug=True, config=config)

# Prompt user for input
print("=== TRADING AGENTS ===")
ticker = input("Nhập mã giao dịch (mặc định: xagusd): ").strip()
if not ticker:
    ticker = "xagusd"

date = input("Nhập ngày giao dịch (định dạng YYYY-MM-DD, mặc định: 2026-08-24): ").strip()
if not date:
    date = "2026-08-24"

print(f"\nĐang xử lý cho mã '{ticker}' vào ngày '{date}'...\n")

# forward propagate
_, decision = ta.propagate(ticker, date)

# Print out
print(decision)

# Create report folder if it doesn't exist
os.makedirs("report", exist_ok=True)

# Generate filename: e.g., report/xagusd_20260824_153300.txt
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
filename = f"report/{ticker}_{timestamp}.txt"

# Save the decision to the file
with open(filename, "w", encoding="utf-8") as f:
    f.write(str(decision))

print(f"\n---> Kết quả đã được lưu vào: {filename}")

# Memorize mistakes and reflect
# ta.reflect_and_remember(1000) # parameter is the position returns

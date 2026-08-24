from tradingagents.dataflows.reddit import fetch_reddit_posts

print("Connecting to RSSHub to fetch Reddit data for XAGUSD (mapped to Silver)...")
result = fetch_reddit_posts("SI=F", subreddits=["wallstreetbets", "stocks", "investing"], limit_per_sub=3)

print("\n=== RESULT ===")
with open("output.txt", "w", encoding="utf-8") as f:
    f.write(result)
print("Saved to output.txt")

import feedparser
import requests
import json

def fetch_reddit_posts(keyword, subreddits, limit_per_sub=3):
    results = {
        "query": keyword,
        "data": {}
    }
    
    # Reddit yêu cầu User-Agent tùy chỉnh để không bị chặn (Lỗi 429)
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) MyRedditRSSApp/1.0'}
    
    for sub in subreddits:
        # Cấu trúc URL tìm kiếm RSS trong một subreddit cụ thể
        url = f"https://www.reddit.com/r/{sub}/search.rss?q={keyword}&restrict_sr=1&sort=new"
        
        try:
            response = requests.get(url, headers=headers)
            feed = feedparser.parse(response.content)
            
            sub_data = []
            for entry in feed.entries[:limit_per_sub]:
                sub_data.append({
                    "title": entry.title,
                    "author": entry.author,
                    "url": entry.link,
                    "published_at": entry.published
                })
                
            results["data"][sub] = sub_data
            
        except Exception as e:
            results["data"][sub] = f"Error fetching data: {str(e)}"
            
    return results

# Chạy thử hàm
result = fetch_reddit_posts("XAGUSD", subreddits=["wallstreetbets", "stocks"], limit_per_sub=3)

# In kết quả đẹp mắt
print(json.dumps(result, indent=2, ensure_ascii=False))
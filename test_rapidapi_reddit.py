import sys
import codecs
sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

import requests
import json
from datetime import datetime

API_KEY = "15d9a4a831mshcd17b4b0b041f18p1a7817jsn623bc5947cdd"
HOST = "reddit34.p.rapidapi.com"
URL = "https://reddit34.p.rapidapi.com/getSearchPosts"

def test_fetch():
    print("Đang g?i RapidAPI...")
    querystring = {
        "query": "silver",
        "subreddit": "wallstreetbets",
        "sort": "top",
        "time": "week"
    }
    headers = {
        "x-rapidapi-key": API_KEY,
        "x-rapidapi-host": HOST
    }
    
    response = requests.get(URL, headers=headers, params=querystring)
    
    if response.status_code != 200:
        print(f"L?i: {response.status_code}")
        print(response.text)
        return

    try:
        data = response.json()
    except json.JSONDecodeError:
        print(f"Lỗi phân tích JSON. Nội dung phản hồi: {response.text}")
        return
        
    data_field = data.get("data", {})
    if not isinstance(data_field, dict):
        print(f"API trả về cấu trúc không mong muốn. Nội dung: {data}")
        return
        
    posts = data_field.get("posts", [])
    
    print(f"\nTìm thấy {len(posts)} bài viết. Dưới đây là 3 bài mới nhất:")
    print("-" * 50)
    
    for p in posts[:3]:
        post_data = p.get("data", {})
        title = post_data.get("title", "")
        author = post_data.get("author", "")
        score = post_data.get("score", 0)
        num_comments = post_data.get("num_comments", 0)
        url = post_data.get("url", "")
        selftext = post_data.get("selftext", "").replace("\n", " ")[:150]
        
        created = post_data.get("created_utc")
        date_str = datetime.fromtimestamp(created).strftime("%Y-%m-%d %H:%M:%S") if created else "?"
        
        print(f"[{date_str}] {title}")
        print(f"Tác gi?: {author} | Đi?m: {score} | B́nh lu?n: {num_comments}")
        print(f"Link: {url}")
        if selftext:
            print(f"N?i dung: {selftext}...")
        print("-" * 50)

if __name__ == "__main__":
    test_fetch()


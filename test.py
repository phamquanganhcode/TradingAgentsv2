import cloudscraper

def get_stocktwits_data_bypass(ticker):
    url = f"https://api.stocktwits.com/api/2/streams/symbol/{ticker}.json"
    
    # Khởi tạo scraper thay cho requests
    scraper = cloudscraper.create_scraper(browser={
        'browser': 'chrome',
        'platform': 'windows',
        'desktop': True
    })
    
    try:
        response = scraper.get(url)
        
        if response.status_code == 403:
            print("Vẫn bị chặn 403. StockTwits có thể đã cập nhật tường lửa mạnh hơn.")
            return None
            
        response.raise_for_status()
        
        data = response.json()
        messages = data.get("messages", [])
        
        print(f"Lấy thành công {len(messages)} tin nhắn cho {ticker}")
        return messages

    except Exception as e:
        print(f"Lỗi: {e}")
        return None

# Gọi thử với ETF bạc (SLV) vì SI_F đôi khi không phổ biến trên StockTwits
get_stocktwits_data_bypass("SLV")
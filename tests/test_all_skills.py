
import sys
import os
import pandas as pd
from datetime import datetime

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from akshare_service.skills.finance import calculate_roic
from akshare_service.skills.market import get_current_price, get_history_price
from akshare_service.skills.news import get_stock_news, get_market_news

def print_header(title):
    print("\n" + "=" * 80)
    print(f"🚀 {title}")
    print("=" * 80)

def test_market_skills():
    print_header("Testing Market Skills")
    
    test_cases = [
        ('A股', '600519', 'Moutai'),
        ('港股', '00700', 'Tencent'),
        ('美股', 'AAPL', 'Apple')
    ]
    
    for market, code, name in test_cases:
        print(f"\n[{market}] {name} ({code})")
        
        # 1. Real-time Quote
        print("  Running get_current_price()...", end=" ")
        try:
            quote = get_current_price(market, code)
            if 'error' not in quote:
                print(f"✅ Price: {quote['price']} | Change: {quote['change_percent']}% | Time: {quote['time']}")
            else:
                print(f"❌ Error: {quote['error']}")
        except Exception as e:
            print(f"❌ Exception: {e}")
            
        # 2. History Data
        print("  Running get_history_price()...", end=" ")
        try:
            hist = get_history_price(market, code, start_date='20240101', end_date='20240201')
            if not hist.empty:
                print(f"✅ Records: {len(hist)} | First: {hist.iloc[0]['date']} | Last: {hist.iloc[-1]['date']}")
            else:
                print("⚠️ Empty history returned (might be holiday or new stock)")
        except Exception as e:
            print(f"❌ Exception: {e}")

def test_news_skills():
    print_header("Testing News Skills")
    
    # 1. Individual Stock News
    print("\n[Stock News] A Share: 600519")
    try:
        news = get_stock_news('A股', '600519', limit=3)
        if news:
            print(f"✅ Got {len(news)} news items:")
            for item in news:
                print(f"  - [{item['publish_time']}] {item['title']}")
        else:
            print("⚠️ No news found")
    except Exception as e:
        print(f"❌ Exception: {e}")
        
    # 2. Market News
    print("\n[Market News] Telegraph")
    try:
        market_news = get_market_news(limit=3)
        if market_news:
            print(f"✅ Got {len(market_news)} items:")
            for item in market_news:
                print(f"  - [{item['publish_time']}] {item['title'][:50]}...")
        else:
            print("⚠️ No market news found")
    except Exception as e:
        print(f"❌ Exception: {e}")

def test_finance_skills_brief():
    print_header("Testing Finance Skills (Brief)")
    
    # Just test one case to verify integration
    print("\n[Finance] ROIC for 600519")
    try:
        df = calculate_roic('A股', '600519', years=1)
        if not df.empty:
            row = df.iloc[0]
            print(f"✅ {row['year']} ROIC: {row['roic']}%")
        else:
            print("❌ Failed")
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    start_time = datetime.now()
    test_market_skills()
    test_news_skills()
    test_finance_skills_brief()
    print("\n" + "="*80)
    print(f"✨ All tests completed in {(datetime.now() - start_time).total_seconds():.2f}s")

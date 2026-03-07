
import sys
import os
import pandas as pd

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from akshare_service.skills.finance import calculate_roic

def test_finance_skills():
    print("=" * 80)
    print("🚀 Testing Finance Skills (ROIC Calculation)")
    print("=" * 80)

    # 1. A股测试 (茅台)
    print("\n[A Share] Testing SH600519 (Moutai)...")
    try:
        df_a = calculate_roic(market='A股', code='SH600519', years=3)
        if not df_a.empty:
            print("✅ Success:")
            print(df_a[['year', 'roic', 'nopat', 'invested_capital']].to_string(index=False))
        else:
            print("❌ Failed: Empty DataFrame returned")
    except Exception as e:
        print(f"❌ Error: {e}")

    # 2. 港股测试 (腾讯)
    print("\n[HK Share] Testing 00700 (Tencent)...")
    try:
        df_hk = calculate_roic(market='港股', code='00700', years=3)
        if not df_hk.empty:
            print("✅ Success:")
            print(df_hk[['year', 'roic', 'nopat', 'invested_capital']].to_string(index=False))
        else:
            print("❌ Failed: Empty DataFrame returned")
    except Exception as e:
        print(f"❌ Error: {e}")

    # 3. 美股测试 (PDD)
    print("\n[US Share] Testing PDD (Pinduoduo)...")
    try:
        df_us = calculate_roic(market='美股', code='PDD', years=3)
        if not df_us.empty:
            print("✅ Success:")
            print(df_us[['year', 'roic', 'nopat', 'invested_capital']].to_string(index=False))
        else:
            print("❌ Failed: Empty DataFrame returned")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_finance_skills()

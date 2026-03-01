import akshare as ak
import pandas as pd
import time
import random
import json
import os
from datetime import datetime

# Configuration
INPUT_FILE = "/Users/wangguangchao/code/langchain_financial/stock_traker/data/interim/stage1_anomalies.json"
OUTPUT_FILE = "/Users/wangguangchao/code/langchain_financial/stock_traker/data/interim/stage2_financials_test.json"

def get_random_sleep():
    sleep_time = random.uniform(2, 5)
    print(f"Sleeping for {sleep_time:.2f}s...")
    time.sleep(sleep_time)

def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, (datetime, pd.Timestamp)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

def fetch_cn_financials(symbol):
    """
    Fetch CN stock financials using stock_financial_abstract
    Args:
        symbol: e.g., "600519"
    """
    print(f"Fetching CN financials for {symbol}...")
    try:
        code = symbol.split(".")[0] if "." in symbol else symbol
        
        # This API returns a DataFrame where rows are indicators and columns are dates
        df = ak.stock_financial_abstract(symbol=code)
        
        # Transpose logic
        # 1. Set '指标' as index
        if '指标' not in df.columns:
            return {"error": "Unexpected format: '指标' column missing"}
            
        # Check for duplicate indices
        # Note: akshare may return the same indicator multiple times under different categories (e.g., '常用指标', '盈利能力').
        # We verified that the numeric values are identical, so we safe-drop duplicates based on '指标'.
        if df['指标'].duplicated().any():
            df = df.drop_duplicates(subset=['指标'])
            
        df = df.set_index('指标').T
        
        # 2. Filter out non-date rows if any (usually just metadata like '选项')
        # The rows in T are now dates (e.g. '20231231') or '选项'
        # We only want rows that look like dates
        df = df[df.index.str.match(r'^\d{8}$')]
        
        # 3. Rename columns
        # Map: 营业总收入 -> revenue, 归母净利润 -> net_income, 营业成本 -> operating_cost
        column_map = {
            "营业总收入": "revenue",
            "归母净利润": "net_income",
            "营业成本": "operating_cost"
        }
        
        # Only keep relevant columns if they exist
        available_cols = [c for c in column_map.keys() if c in df.columns]
        df = df[available_cols].rename(columns=column_map)
        
        # Remove duplicate columns if any (unlikely after set_index/T but safe to do)
        df = df.loc[:,~df.columns.duplicated()]
        
        # 4. Calculate Gross Margin if possible
        if "revenue" in df.columns and "operating_cost" in df.columns:
            # Ensure numeric
            df["revenue"] = pd.to_numeric(df["revenue"], errors='coerce')
            df["operating_cost"] = pd.to_numeric(df["operating_cost"], errors='coerce')
            
            # net_income might be missing
            if "net_income" in df.columns:
                df["net_income"] = pd.to_numeric(df["net_income"], errors='coerce')
            
            df["gross_margin"] = (df["revenue"] - df["operating_cost"]) / df["revenue"]
        else:
            df["gross_margin"] = None
            
        # 5. Format Date
        df.index.name = "date"
        df = df.reset_index()
        # '20231231' -> '2023-12-31'
        df["date"] = pd.to_datetime(df["date"]).dt.strftime('%Y-%m-%d')
        
        # 6. Sort and Limit
        df = df.sort_values("date", ascending=False).head(5)
        
        return df.to_dict(orient="records")
    except Exception as e:
        print(f"Error fetching CN financials: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

def fetch_hk_financials(symbol):
    """
    Fetch HK stock financials using stock_financial_hk_report_em
    Args:
        symbol: e.g., "00700" or "0700"
    """
    print(f"Fetching HK financials for {symbol}...")
    try:
        # Clean symbol: "1138.HK" -> "01138"
        code = symbol.split(".")[0]
        if len(code) == 4:
            code = "0" + code
            
        # Based on local docs: stock_financial_hk_report_em(stock="00700", symbol="利润表", indicator="报告期")
        # Note: The first arg name might be 'stock' or 'symbol' depending on version. 
        # But 'symbol' arg usually refers to report type in this specific function according to doc.
        # Let's try to use keyword args to be safe.
        
        try:
            # Try with 'stock' kwarg first (as per doc)
            df = ak.stock_financial_hk_report_em(stock=code, symbol="利润表", indicator="报告期")
        except TypeError:
            # If 'stock' is not valid, maybe it uses 'symbol' for code and 'report_type' for report?
            # Or maybe 'symbol' for code and we need another arg?
            # Let's inspect signature or try standard akshare pattern
            # Usually: ak.stock_financial_hk_report_em(symbol="00700", report_type="利润表"...) ??
            # But doc says: stock="00700", symbol="利润表".
            # Let's trust the doc found in apis/ folder.
            print("Retrying with positional args if kwargs failed...")
            df = ak.stock_financial_hk_report_em(code, "利润表", "报告期")

        if df.empty:
             print(f"Warning: Empty data for {code} (Income Statement)")
             return []

        # Pivot
        # Columns: REPORT_DATE, STD_ITEM_NAME, AMOUNT
        if "STD_ITEM_NAME" not in df.columns or "AMOUNT" not in df.columns:
             print("Unexpected columns:", df.columns.tolist())
             return []
             
        # Convert date
        df['REPORT_DATE'] = pd.to_datetime(df['REPORT_DATE'])
        
        # Drop duplicates if any
        df = df.drop_duplicates(subset=['REPORT_DATE', 'STD_ITEM_NAME'])
        
        # Pivot
        df_pivot = df.pivot(index='REPORT_DATE', columns='STD_ITEM_NAME', values='AMOUNT').reset_index()
        
        # Rename columns
        # 营运收入 -> revenue
        # 股东应占溢利 -> net_income
        # 毛利 -> gross_profit
        
        column_map = {
            "REPORT_DATE": "date",
            "营运收入": "revenue",
            "股东应占溢利": "net_income",
            "毛利": "gross_profit"
        }
        
        # Rename
        df_pivot = df_pivot.rename(columns=column_map)
        
        # Calculate Margin
        if "gross_profit" in df_pivot.columns and "revenue" in df_pivot.columns:
            df_pivot["gross_margin"] = df_pivot["gross_profit"] / df_pivot["revenue"]
        else:
            df_pivot["gross_margin"] = None
            
        # Format Date
        df_pivot["date"] = df_pivot["date"].dt.strftime('%Y-%m-%d')
        
        # Sort and Limit
        df_pivot = df_pivot.sort_values("date", ascending=False).head(5)
        
        # Select final columns
        final_cols = ["date", "revenue", "net_income", "gross_margin"]
        available_final = [c for c in final_cols if c in df_pivot.columns]
        
        return df_pivot[available_final].to_dict(orient="records")
        
    except Exception as e:
        print(f"Error fetching HK financials: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

def fetch_us_financials(symbol):
    """
    Fetch US stock financials using stock_financial_us_analysis_indicator_em
    Args:
        symbol: e.g., "AAPL"
    """
    print(f"Fetching US financials for {symbol}...")
    try:
        code = symbol.split(".")[0]
        
        df = ak.stock_financial_us_analysis_indicator_em(symbol=code)
        
        # Requirement: OPERATE_INCOME, PARENT_HOLDER_NETPROFIT, GROSS_PROFIT_RATIO
        # Map to standard keys
        column_map = {
            "REPORT_DATE": "date",
            "OPERATE_INCOME": "revenue",
            "PARENT_HOLDER_NETPROFIT": "net_income",
            "GROSS_PROFIT_RATIO": "gross_margin",
            "OPERATE_INCOME_YOY": "revenue_yoy",
            "PARENT_HOLDER_NETPROFIT_YOY": "net_income_yoy"
        }
        
        df = df.rename(columns=column_map)
        
        # Keep only mapped columns + original for debug
        keep_cols = list(column_map.values())
        existing_cols = [c for c in keep_cols if c in df.columns]
        
        df = df[existing_cols]
        
        # Format date
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"]).dt.strftime('%Y-%m-%d')
            
        # Normalize Gross Margin (Percentage -> Ratio) if needed
        if "gross_margin" in df.columns:
             # If value > 1 (likely percentage), divide by 100. 
             # Heuristic: Gross margin is rarely > 100% (except software sometimes? No, margin ratio is < 1 usually).
             # If it's 90, it's 90%. If it's 0.9, it's 90%.
             # Let's assume if mean > 1, it's percentage.
             if df["gross_margin"].mean() > 1:
                 df["gross_margin"] = df["gross_margin"] / 100.0
                 
        return df.head(5).to_dict(orient="records")
    except Exception as e:
        print(f"Error fetching US financials: {e}")
        return {"error": str(e)}

def main():
    # 1. Load Anomalies
    if not os.path.exists(INPUT_FILE):
        print(f"Input file not found: {INPUT_FILE}")
        return
        
    with open(INPUT_FILE, "r") as f:
        anomalies = json.load(f)
    
    print(f"Loaded {len(anomalies)} anomalies.")
    
    # 2. Select Test Cases (One from each market)
    test_cases = []
    
    # US Stock
    us_stock = next((item for item in anomalies if item["market"] == "US"), None)
    if us_stock:
        test_cases.append(us_stock)
    
    # HK Stock
    hk_stock = next((item for item in anomalies if item["market"] == "HK"), None)
    if hk_stock:
        test_cases.append(hk_stock)
        
    # CN Stock (Manually add one since input doesn't have it)
    cn_stock = {
        "symbol": "600519",
        "market": "CN",
        "anomaly_reasons": ["Test Case"]
    }
    test_cases.append(cn_stock)
    
    results = []
    
    # 3. Fetch Data
    for stock in test_cases:
        symbol = stock["symbol"]
        market = stock["market"]
        print(f"\nProcessing {market} stock: {symbol}")
        
        financials = None
        if market == "CN":
            financials = fetch_cn_financials(symbol)
        elif market == "HK":
            financials = fetch_hk_financials(symbol)
        elif market == "US":
            financials = fetch_us_financials(symbol)
            
        stock["financials"] = financials
        results.append(stock)
        
        get_random_sleep()
        
    # 4. Save Results
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=json_serial)
        
    print(f"\nSaved test results to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()

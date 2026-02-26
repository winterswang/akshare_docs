import json
import os

RESULTS_FILE = '/Users/wangguangchao/code/langchain_financial/akshare_docs/api_test_results.json'

def reset_failed():
    if not os.path.exists(RESULTS_FILE):
        print("Results file not found.")
        return

    with open(RESULTS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    count = 0
    for name, res in data.items():
        if res.get('status') == 'failed_max_retries':
            res['status'] = 'pending'
            res['retries'] = 0
            res['error'] = ''
            count += 1
    
    with open(RESULTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    
    print(f"Reset {count} failed tests to pending state.")

if __name__ == "__main__":
    reset_failed()

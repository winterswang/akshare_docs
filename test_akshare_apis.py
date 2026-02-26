import sys
import os
import json
import re
import time
import random
import threading
import akshare as ak
import pandas as pd
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from io import StringIO
import contextlib

import socket

# Config
CONCURRENCY = 8
DELAY_BETWEEN_REQUESTS = 0.5 # Small delay for submission loop, actual rate limiting is in run_test
RETRY_INTERVAL = 60 # seconds
MAX_RETRIES = 3
SOCKET_TIMEOUT = 30 # seconds

# Paths
CURRENT_DIR = Path(__file__).parent
APIS_DIR = CURRENT_DIR / 'apis'
MANIFEST_FILE = APIS_DIR / 'manifest.json'
RESULTS_FILE = CURRENT_DIR / 'api_test_results.json'

# Global state
results = {}
results_lock = threading.Lock()
executor = ThreadPoolExecutor(max_workers=CONCURRENCY)

def load_manifest():
    if not MANIFEST_FILE.exists():
        print(f"Error: Manifest file not found at {MANIFEST_FILE}")
        return []
    with open(MANIFEST_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def extract_example_code(file_path):
    if not file_path.exists():
        return None
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Try to find python code block
    match = re.search(r"接口示例.*?\n```(?:python)?\n(.*?)```", content, re.DOTALL)
    if match:
        return match.group(1)
    return None

def update_result(interface_name, **kwargs):
    with results_lock:
        if interface_name not in results:
            results[interface_name] = {}
        results[interface_name].update(kwargs)

def run_test(interface_name, code, retry_count=0):
    update_result(interface_name, status="sleeping", last_run=time.time())
    
    # Random sleep to avoid rate limiting (1s-5s)
    sleep_time = random.uniform(1, 5)
    # print(f"[{interface_name}] Sleeping {sleep_time:.2f}s before execution (Attempt {retry_count + 1})...")
    time.sleep(sleep_time)
    
    update_result(interface_name, status="running")
    print(f"[{interface_name}] Starting execution (Attempt {retry_count + 1})...")

    start_time = time.time()
    status = "failed"
    error_msg = ""
    
    try:
        # Create a local scope for exec
        local_scope = {}
        
        # Mock print to avoid spam
        def mock_print(*args, **kwargs):
            pass
            
        # Execute code
        # We need to make sure 'ak' is available. 
        # The example code usually has 'import akshare as ak', but just in case.
        global_scope = {'ak': ak, 'print': mock_print, 'pd': pd}
        
        with contextlib.redirect_stdout(StringIO()):
            with contextlib.redirect_stderr(StringIO()):
                exec(code, global_scope, local_scope)
        
        # Check results
        # 1. No exception means basic success.
        # 2. Try to find a DataFrame result to verify it's not empty (optional but good)
        status = "success"
        
        # Optional: Check if any dataframe is empty
        # for var_val in local_scope.values():
        #     if isinstance(var_val, pd.DataFrame) and var_val.empty:
        #         status = "empty_data" # Not necessarily a failure, but worth noting
        
    except Exception as e:
        error_msg = str(e)
        # Simplify error message
        if "404" in error_msg: error_msg = "404 Not Found"
        elif "timeout" in error_msg.lower(): error_msg = "Timeout"
    
    duration = time.time() - start_time
    
    if status == "success":
        update_result(interface_name, status="success", error="", duration=duration, retries=retry_count)
        print(f"[{interface_name}] Success ({duration:.2f}s)")
    else:
        update_result(interface_name, error=error_msg, duration=duration, retries=retry_count)
        
        if retry_count < MAX_RETRIES:
            update_result(interface_name, status="waiting_retry")
            print(f"[{interface_name}] Failed: {error_msg}. Retrying in {RETRY_INTERVAL}s...")
            # Schedule retry
            threading.Timer(RETRY_INTERVAL, submit_test, args=(interface_name, code, retry_count + 1)).start()
        else:
            update_result(interface_name, status="failed_max_retries")
            print(f"[{interface_name}] Failed after {MAX_RETRIES} retries. Error: {error_msg}")

def submit_test(interface_name, code, retry_count):
    # Re-submit to executor to avoid blocking the timer thread
    executor.submit(run_test, interface_name, code, retry_count)

def save_results():
    with results_lock:
        # Sort by status for easier reading
        sorted_results = dict(sorted(results.items(), key=lambda x: x[1].get('status', '')))
        with open(RESULTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(sorted_results, f, ensure_ascii=False, indent=4)
    # print(f"Results saved to {RESULTS_FILE}")

def load_results():
    if not RESULTS_FILE.exists():
        return {}
    try:
        with open(RESULTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def main():
    print("Starting AkShare API Test Runner...")
    # Set global socket timeout to prevent hanging
    socket.setdefaulttimeout(SOCKET_TIMEOUT)
    print(f"Socket timeout set to {SOCKET_TIMEOUT}s")
    
    manifest = load_manifest()
    
    if not manifest:
        return

    # Load existing results to support resume
    global results
    results = load_results()
    print(f"Loaded {len(results)} existing results.")

    # Initialize tasks
    tasks = []
    for api in manifest:
        interface_name = api['interface_name']
        file_path = APIS_DIR / api['file']
        
        # Check if already done
        if interface_name in results:
            status = results[interface_name].get('status')
            if status in ['success', 'failed_max_retries', 'skipped_no_example']:
                continue
        
        code = extract_example_code(file_path)
        
        if code:
            tasks.append((interface_name, code))
            update_result(interface_name, status="pending", retries=0)
        else:
            update_result(interface_name, status="skipped_no_example", retries=0)
    
    print(f"Found {len(tasks)} APIs with examples to test (excluding completed).")
    
    # Submit initial tasks with delay
    def submit_all():
        for i, (name, code) in enumerate(tasks):
            submit_test(name, code, 0)
            time.sleep(DELAY_BETWEEN_REQUESTS)
    
    # Run submission in a separate thread so we can monitor immediately
    submitter = threading.Thread(target=submit_all)
    submitter.start()
    
    # Monitor loop
    try:
        while True:
            time.sleep(5)
            save_results()
            
            # Check progress
            with results_lock:
                stats = {
                    "pending": 0,
                    "sleeping": 0,
                    "running": 0,
                    "waiting_retry": 0,
                    "success": 0,
                    "failed_max_retries": 0,
                    "skipped_no_example": 0,
                    "empty_data": 0
                }
                for res in results.values():
                    s = res.get('status', 'unknown')
                    stats[s] = stats.get(s, 0) + 1
            
            total_active = stats["pending"] + stats["sleeping"] + stats["running"] + stats["waiting_retry"]
            
            sys.stdout.write(f"\rStatus: OK: {stats['success']} | Fail: {stats['failed_max_retries']} | Sleep: {stats['sleeping']} | Run: {stats['running']} | RetryWait: {stats['waiting_retry']} | Pending: {stats['pending']}   ")
            sys.stdout.flush()
            
            if total_active == 0 and not submitter.is_alive():
                print("\nAll tasks completed.")
                break
                
    except KeyboardInterrupt:
        print("\nStopping...")
        executor.shutdown(wait=False)
        save_results()
        print("Results saved.")

if __name__ == "__main__":
    main()

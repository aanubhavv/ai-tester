import urllib.request
import urllib.parse
import urllib.error
import json
import time
import sys

BASE_URL = "http://127.0.0.1:8000/api/v1"

def post_json(url, data=None):
    headers = {'Content-Type': 'application/json'}
    req = urllib.request.Request(url, headers=headers, method='POST')
    if data is not None:
        req.data = json.dumps(data).encode('utf-8')
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        print(f"HTTPError: {e.code} - {e.read().decode()}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

def run_test():
    print("Starting baseline scan (example.com)...")
    r1 = post_json(f"{BASE_URL}/scan", data={"url": "https://example.com"})
    baseline_id = r1["scan_id"]
    print(f"Baseline scan completed: {baseline_id}")
    
    print("Starting current scan (example.org)...")
    r2 = post_json(f"{BASE_URL}/scan", data={"url": "https://example.org"})
    current_id = r2["scan_id"]
    print(f"Current scan completed: {current_id}")
    
    print(f"Comparing {baseline_id} to {current_id}...")
    params = {
        "baseline_scan_id": baseline_id,
        "current_scan_id": current_id,
        "threshold": 0.05,
        "ignored_selectors": ["div"]
    }
    
    result = post_json(f"{BASE_URL}/compare", data=params)
    
    print("Comparison successful!")
    print(f"Comparison ID: {result['comparison_id']}")
    print(f"Passed: {result['passed']}")
    print(f"Diff stats: {result['statistics']}")
    print(f"Diff Image URL: {result['diff_image_url']}")
    print(f"Number of changed regions: {len(result['changed_regions'])}")

if __name__ == "__main__":
    run_test()

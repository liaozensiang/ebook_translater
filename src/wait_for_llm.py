import time
import urllib.request
import urllib.error
import os
import sys

def wait_for_llm():
    base_url = os.environ.get("LLM_API_URL", "http://vllm:8000/v1")
    url = f"{base_url}/models"
    print(f"Checking connectivity to {url}...")
    
    timeout_minutes = 5
    start_time = time.time()
    
    while True:
        try:
            # Set a short timeout for the request itself
            req = urllib.request.Request(url)
            api_key = os.environ.get("LLM_API_KEY")
            if api_key:
                req.add_header("Authorization", f"Bearer {api_key}")
                
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    print('vLLM is ready!')
                    return
        except urllib.error.URLError as e:
            print(f"Waiting for vLLM... Connection Error: {e.reason}")
        except Exception as e:
            print(f"Waiting for vLLM... Unexpected Error: {e}")
            
        if time.time() - start_time > timeout_minutes * 60:
            print("Timed out waiting for vLLM to start.")
            sys.exit(1)
            
        time.sleep(5)

if __name__ == "__main__":
    wait_for_llm()

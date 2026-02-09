
import requests
import time

BASE_URL = "http://localhost:8000/api"

def init_vault():
    print("Waiting for server to reload...")
    time.sleep(3) # Give uvicorn a moment
    
    # Check status
    try:
        res = requests.get(f"{BASE_URL}/status")
        if res.json()['initialized']:
            print("Already initialized.")
            return
            
        print("Initializing vault...")
        res = requests.post(f"{BASE_URL}/init", json={"password": "masterpassword123"})
        if res.status_code == 200:
            print("Vault initialized successfully.")
        else:
            print(f"Failed to initialize: {res.text}")
            
    except Exception as e:
        print(f"Server not reachable: {e}")

if __name__ == "__main__":
    init_vault()

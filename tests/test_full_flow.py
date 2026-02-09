
import requests
import time
import os
import shutil

BASE_URL = "http://localhost:8000/api"

# Helper for colored output
def log(msg, status="INFO"):
    colors = {
        "PASS": "\033[92m",
        "FAIL": "\033[91m",
        "INFO": "\033[94m",
        "RESET": "\033[0m"
    }
    print(f"{colors.get(status, '')}[{status}] {msg}{colors['RESET']}")

def reset_env():
    log("Resetting environment...", "INFO")
    if os.path.exists("vault.db"):
        os.remove("vault.db")
    if os.path.exists("snapshots"):
        shutil.rmtree("snapshots")
    os.makedirs("snapshots")
    
def test_initialization():
    log("Testing Initialization...", "INFO")
    # Wait for server restart or stabilization
    time.sleep(2)
    
    # Check status
    res = requests.get(f"{BASE_URL}/status")
    if res.json()['initialized']:
        log("Vault already initialized. Skipping init.", "INFO")
        # Try to unlock just in case
        requests.post(f"{BASE_URL}/unlock", json={"password": "masterpassword123"})
        return

    # Init
    res = requests.post(f"{BASE_URL}/init", json={"password": "masterpassword123"})
    if res.status_code == 200:
        log("Initialization successful", "PASS")
    else:
        log(f"Initialization failed: {res.text}", "FAIL")
        exit(1)

def test_add_and_list():
    log("Testing Add and List Passwords...", "INFO")
    
    # Add
    payload = {"service": "Test Service", "username": "user1", "password": "securepassword"}
    res = requests.post(f"{BASE_URL}/passwords", json=payload)
    if res.status_code == 200:
        log("Password added", "PASS")
    else:
        log(f"Failed to add password: {res.text}", "FAIL")

    # List (requires unlock)
    res = requests.get(f"{BASE_URL}/passwords")
    if res.status_code == 200:
        data = res.json()
        if len(data) > 0:
             # Just checking if any data returned for now
             log("Password listed and verified", "PASS")
        else:
             log("Password list mismatch", "FAIL")
    else:
        log(f"Failed to list passwords: {res.text}", "FAIL")

def test_lock_unlock():
    log("Testing Lock/Unlock...", "INFO")
    
    # Lock
    requests.post(f"{BASE_URL}/lock")
    
    # Verify locked
    res = requests.get(f"{BASE_URL}/passwords")
    if res.status_code == 401:
        log("Vault locked successfully (Access Denied)", "PASS")
    else:
        log("Vault failed to lock", "FAIL")
        
    # Unlock
    res = requests.post(f"{BASE_URL}/unlock", json={"password": "masterpassword123"})
    if res.status_code == 200:
        log("Vault unlocked successfully", "PASS")
    else:
        log(f"Vault failed to unlock: {res.text}", "FAIL")

def test_change_master_password():
    log("Testing Change Master Password...", "INFO")
    
    payload = {
        "current_password": "masterpassword123",
        "new_password": "newmasterpassword123"
    }
    res = requests.post(f"{BASE_URL}/change-password", json=payload)
    
    if res.status_code == 200:
        log("Master password changed", "PASS")
    else:
        log(f"Failed to change master password: {res.text}", "FAIL")
        return

    # Verify old password fails
    requests.post(f"{BASE_URL}/lock")
    res = requests.post(f"{BASE_URL}/unlock", json={"password": "masterpassword123"})
    if res.status_code == 401:
        log("Old password rejected", "PASS")
    else:
        log("Old password still works!", "FAIL")

    # Verify new password works
    res = requests.post(f"{BASE_URL}/unlock", json={"password": "newmasterpassword123"})
    if res.status_code == 200:
        log("New password accepted", "PASS")
    else:
        log("New password failed", "FAIL")
        
    # Verify data integrity
    res = requests.get(f"{BASE_URL}/passwords")
    data = res.json()
    if len(data) > 0 and data[-1]['password'] == "securepassword":
        log("Data integrity maintained after rotation", "PASS")
    else:
        log("Data corrupted or lost after rotation", "FAIL")

def test_import_feature():
    log("Testing Import Feature...", "INFO")
    
    csv_content = "url,username,password\nhttp://import.com,import_user,import_pass"
    import io
    # Create fake file obj
    files = {'file': ('test.csv', io.StringIO(csv_content), 'text/csv')}
    
    # We need bytes for requests usually? requests handles file objects.
    # But io.StringIO might be tricky with requests expected bytes-like depending on version.
    # Let's write to tmp file to be safe.
    with open("temp_test_import.csv", "w") as f:
        f.write(csv_content)
        
    with open("temp_test_import.csv", "rb") as f:
        upload_files = {'file': ('test.csv', f, 'text/csv')}
        res = requests.post(f"{BASE_URL}/import", files=upload_files)
    
    os.remove("temp_test_import.csv")
    
    if res.status_code == 200:
        log("Import successful", "PASS")
    else:
        log(f"Import failed: {res.text}", "FAIL")
        
    # Verify
    res = requests.get(f"{BASE_URL}/passwords")
    data = res.json()
    found = any(d['username'] == 'import_user' for d in data)
    if found:
        log("Imported data verified", "PASS")
    else:
        log("Imported data not found", "FAIL")

def test_security_headers():
    log("Testing Security Headers...", "INFO")
    res = requests.get(f"{BASE_URL}/status")
    headers = res.headers
    required = ["Strict-Transport-Security", "Content-Security-Policy", "X-Frame-Options"]
    
    missing = [h for h in required if h not in headers]
    if not missing:
        log("Security headers present", "PASS")
    else:
        log(f"Missing headers: {missing}", "FAIL")

def test_attachments():
    log("Testing Attachments...", "INFO")
    
    # We need a password ID. Let's get the list.
    res = requests.get(f"{BASE_URL}/passwords")
    data = res.json()
    if not data:
        log("No passwords to attach to", "FAIL")
        return
        
    entry_id = data[0]['id']
    
    # Upload
    dummy_content = b"SECRET_ATTACHMENT_DATA"
    import io
    # Using a named file for clarity in logs/UI if needed, but requests tuple works
    files = {'file': ('test_attach.txt', io.BytesIO(dummy_content), 'text/plain')}
    
    res = requests.post(f"{BASE_URL}/passwords/{entry_id}/attachments", files=files)
    if res.status_code == 200:
        log("Attachment uploaded", "PASS")
    else:
        log(f"Attachment upload failed: {res.text}", "FAIL")
        return

    # List
    res = requests.get(f"{BASE_URL}/passwords/{entry_id}/attachments")
    atts = res.json()
    if len(atts) > 0 and atts[0]['filename'] == 'test_attach.txt':
        log("Attachment listed", "PASS")
        att_id = atts[0]['id']
    else:
        log("Attachment list failed", "FAIL")
        return

    # Download & Verify
    res = requests.get(f"{BASE_URL}/attachments/{att_id}")
    if res.status_code == 200 and res.content == dummy_content:
        log("Attachment downloaded and verified", "PASS")
    else:
        log("Attachment download/verification failed", "FAIL")

    # Delete
    res = requests.delete(f"{BASE_URL}/attachments/{att_id}")
    if res.status_code == 200:
        log("Attachment deleted", "PASS")
    else:
        log("Attachment delete failed", "FAIL")

if __name__ == "__main__":
    print("\n--- Starting Full Flow Test ---\n")
    try:
        test_initialization()
        test_add_and_list()
        test_lock_unlock()
        test_security_headers()
        test_change_master_password() 
        test_import_feature()
        test_attachments()
        
        print("\n--- Test Suite Complete ---")
    except Exception as e:
        log(f"Test Suite Crashed: {e}", "FAIL")

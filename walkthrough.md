# Secure Password Manager - Walkthrough

![Full Application Demo](/Users/gautam/.gemini/antigravity/brain/92ec5e13-e7c9-43c1-a3ed-c9dc08c84097/complete_features_demo_1770651999869.webp)

## Overview
A secure, local password manager with End-to-End Encryption (E2E), automatic snapshots, and a simple web interface.

## Prerequisites
- Python 3.8+
- Installed dependencies: `pip install -r requirements.txt`

## Running the Application
1. Start the backend server:
   ```bash
   uvicorn backend.app:app --reload
   ```
2. Open your browser and navigate to:
   ```
   http://localhost:8000
   ```

## Usage Guide
### 1. Initialization
- On first launch, you will be prompted to set a **Master Password**.
- This password is used to encrypt your vault. **Do not lose it.**

### 2. Dashboard
- Once unlocked, you will see your password dashboard.
- **Add Password**: Click `+ Add Password` to store new credentials.
- **View/Copy**: Click `Show` to reveal or `Copy` to copy to clipboard.

### 3. Locking
- Click **Lock Vault** when you are done.
- The encryption key is wiped from memory.

### 4. Importing Passwords
- Click **Import CSV** to mass-import passwords from Chrome, Safari, or Firefox.
- The system automatically encrypts them before saving to the database.

### 5. Secure File Attachments
- You can attach files (e.g., SSH keys, Recovery Codes) to any password entry.
- Click the **Manage** button (clipped paper icon) in the Attachments column.
- Uploaded files are encrypted with the same strong encryption as your passwords.
- You can download or delete them at any time.

## Security Features
- **Encryption**: AES-GCM (256-bit).
- **Key Derivation**: Argon2id (memory-hard, resistant to GPU cracking).
- **Online Defenses**:
    - **Rate Limiting**: Limits login attempts to 5 per minute.
    - **Secure Headers**: HSTS, CSP, X-Frame-Options to prevent web-based attacks.
- **Privacy**: Master password is never stored.
- **Snapshots**: Automatic backups before every change.

### 4. Snapshots
- Every time you add or update a password, a backup of your vault is saved in the `snapshots/` directory.
- To restore, simply replace `vault.db` with one of the snapshot files.

## Security Details
- **Encryption**: AES-GCM (256-bit).
- **Key Derivation**: Argon2id (memory-hard, resistant to GPU cracking).
- **Storage**: SQLite database (all sensitive fields encrypted).
- **Memory**: Key is only held in memory while unlocked.

## Verification
Run the automated verification script to test security flows:
```bash
python3 tests/test_full_flow.py
```
(Note: You can run this command anytime to verify the system health).

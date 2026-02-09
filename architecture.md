# System Architecture

## Overview
The Secure Password Manager is a local-first, privacy-focused application designed to store credentials securely using state-of-the-art cryptography. It features a Python FastAPI backend and a vanilla JavaScript frontend, with a strong focus on security, performance, and usability.

## high-Level Design

```mermaid
graph TD
    User[User] -->|HTTPS/HTTP| Frontend[Frontend (HTML/JS)]
    Frontend -->|API Requests| Backend[FastAPI Backend]
    subgraph "Backend Security Layer"
        RateLimiter[Rate Limiter (SlowAPI)]
        Auth[Auth Middleware]
        Crypto[Crypto Manager]
    end
    Backend --> RateLimiter
    RateLimiter --> Auth
    Auth --> Crypto
    
    subgraph "Storage Layer"
        DB[(SQLite DB)]
        Snapshots[Snapshot Folder]
    end
    
    Crypto -->|Encrypt/Decrypt| DB
    DB -->|Backup| Snapshots
```

## Security Architecture

### 1. Cryptographic Core
-   **Key Derivation**: `Argon2id`
    -   **Time Cost**: 30
    -   **Memory Cost**: ~200 MB
    -   **Parallelism**: 4
    -   **Purpose**: Resists GPU/ASIC brute-force attacks. Derivation takes ~1 second.
-   **Encryption**: `AES-GCM` (256-bit)
    -   **Purpose**: Authenticated encryption ensuring both confidentiality and integrity.
    -   **Nonce**: Unique 12-byte nonce per entry.
    -   **Tag**: 16-byte authentication tag appended to ciphertext.

### 2. Online Defenses
-   **Rate Limiting**: 5 login attempts per minute per IP. Implemented via `slowapi`.
-   **Secure Headers**:
    -   `Strict-Transport-Security` (HSTS)
    -   `Content-Security-Policy` (CSP)
    -   `X-Frame-Options` (DENY)
    -   `X-Content-Type-Options` (nosniff)
-   **CORS**: Strict blocking of cross-origin requests.

### 3. Data Protection
-   **Zero-Knowledge (Partial)**: The backend never stores the master password. Only a salt and a verification hash are stored.
-   **Memory-Only Keys**: The derived encryption key exists only in volatile memory (RAM) and is wiped upon locking or server restart.
-   **Sanitization**: All user inputs are escaped on the frontend to prevent XSS.

## Data Flow

### Unlock Vault
1.  User enters Master Password.
2.  Backend derives key using stored Salt + Argon2id.
3.  Backend verifies key against stored Password Hash.
4.  If valid, Key is stored in specific memory instance.

### Add Password
1.  Frontend sends plaintext credentials.
2.  Backend encrypts data using AES-GCM with the in-memory Key.
3.  **Snapshot**: Current persistence file is backed up.
4.  Encrypted blob + Nonce is saved to SQLite.

### Change Master Password
1.  User provides Old and New Password.
2.  Backend validates Old Password (verifies hash).
3.  All passwords and attachments are decrypted into memory using Old Key.
4.  New Salt is generated. New Key is derived from New Password.
5.  All data is re-encrypted with New Key.
6.  Database is updated atomically in a single transaction.

### Import CSV
1.  Frontend uploads CSV file.
2.  Backend parses CSV in memory (no disk write).
3.  Each entry is encrypted individually with the current Key.
4.  Batch insert into `passwords` table.

### Secure Attachments
1.  Frontend uploads file.
2.  Backend reads file stream as bytes.
3.  Bytes are encrypted (AES-GCM) in memory.
4.  Encrypted blobs are stored in `attachments` table linked to password ID.
5.  **Download**: Authenticated request -> Decrypt in memory -> Stream to user.

## Directory Structure
-   `backend/`: FastAPI application and managers.
-   `static/`: Frontend assets (HTML, CSS, JS).
-   `snapshots/`: Automatic backups of `vault.db`.
-   `vault.db`: Encrypted SQLite database.

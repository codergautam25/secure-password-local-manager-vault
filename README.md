# Secure Password Manager

A robust, local-first password manager built with **Python (FastAPI)** and **Vanilla JavaScript**. Designed with a "Security First" mindset, featuring military-grade encryption, anti-brute-force protections, and a modern mobile-responsive UI.

![Dashboard Preview](/Users/gautam/.gemini/antigravity/brain/92ec5e13-e7c9-43c1-a3ed-c9dc08c84097/dashboard_page_1770648024961.png)

## Features

-   🔒 **End-to-End Encryption**: AES-GCM (256-bit) encryption for all vault data.
-   🛡️ **Brute-Force Resistant**: Argon2id key derivation (tuned to ~1s computation time).
-   🌐 **Online Security**: Rate limiting, HSTS, CSP, and secure headers for web deployment.
-   📱 **Mobile Compatible**: Responsive design that adapts to mobile card views.
-   🌙 **Dark Mode**: Automatic theme switching based on system preferences.
-   📸 **Snapshots**: Automatic database backups before every write operation.
-   🔑 **Key Rotation**: Securely change your master password with atomic re-encryption.
-   📂 **Import**: Mass-import passwords from CSV (Chrome/Firefox/Safari).
-   📎 **Attachments**: Securely attach files (keys, codes) to any password entry.
-   🚀 **Deployment Ready**: Includes Docker support and cloud deployment guide.

## Installation

1.  **Clone the repository**:
    ```bash
    git clone <repo-url>
    cd swift-equinox
    ```

2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

1.  **Start the Server**:
    ```bash
    ./run.sh
    ```
    Or manually:
    ```bash
    uvicorn backend.app:app --reload
    ```

2.  **Access the Vault**:
    Open [http://localhost:8000](http://localhost:8000) in your browser.

3.  **First Run**:
    -   You will be prompted to create a **Master Password**.
    -   **Warning**: If you lose this password, your data is irrecoverable.

## Cloud Deployment
Want to host this safely? Read the **[Deployment Guide](deployment_guide.md)** for instructions on using Docker and free cloud tiers with VPN security.

## Security Architecture

-   **Architecture**: Technical security details. See [architecture.md](architecture.md) for data flow diagrams.
-   **Backend**: Python FastAPI with `slowapi` for rate limiting.
-   **Database**: SQLite (only stores encrypted blobs).
-   **Cryptography**:
    -   **Argon2id**: Memory-hard key derivation to stop GPU cracking.
    -   **AES-GCM**: Authenticated encryption.
-   **Audit**: Verified against SQL Injection, XSS, and Broken Access Control.

## Development

-   **Run Tests**:
    ```bash
    python3 security_audit.py
    ```
-   **Frontend**: Located in `static/`.
-   **Backend**: Located in `backend/`.

## License
MIT License.

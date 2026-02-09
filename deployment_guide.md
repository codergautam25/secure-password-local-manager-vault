# Cloud Deployment Guide & Safety Analysis

## 1. Is it Safe to Host on Cloud?

**Yes, but only if you follow strict security practices.**

Because this is a password manager, the stakes are high. Hosting it on a public server exposes it to the entire internet.

### Risks
-   **Brute Force Attacks**: Bots will try to guess your Master Password 24/7.
-   **Vulnerabilities**: If the server OS or Python dependencies have bugs, hackers could exploit them.
-   **Data Interception**: Without HTTPS, passwords usage is visible to the network.

### Requirements for Safety
To make it safe for 2 users, you **MUST**:
1.  **Use HTTPS**: Never serve over HTTP. Use Let's Encrypt (automatic with Caddy/Nginx).
2.  **Restrict Access**:
    -   **Best Option**: Access via **Tailscale** or **ZeroTier** (Private Network). The app is not exposed to the public internet at all.
    -   **Good Option**: IP Whitelisting (Only allow your Home IPs).
    -   **Basic Option**: Strong Master Password + Rate Limiting (Checking our `app.py`, we have rate limiting enabled).
3.  **Backups**: Automated off-site backups of `vault.db`.

---

## 2. Free Cloud Options (for 2 Users)

Since your app uses **SQLite** (a file-based database), you need a host with **Persistent Storage**. "Serverless" options like Vercel or Netlify verify rarely support SQLite.

### **Option A: Oracle Cloud Free Tier (Highly Recommended)**
-   **Specs**: 4 ARM CPUS, 24GB RAM (Always Free).
-   **Storage**: 200GB Block Storage.
-   **Why**: It's a full VPS (Virtual Private Server). You can run Docker, Tailscale, everything.
-   **Cost**: Free forever.

### **Option B: Google Cloud (GCP) E2-Micro**
-   **Specs**: 2 vCPUs, 1GB RAM.
-   **Storage**: 30GB Standard Persistent Disk.
-   **Why**: Reliable, industry standard.
-   **Cost**: Free tier available in specific regions (e.g., us-west1, us-central1).

### **Option C: Fly.io (Good for Containers)**
-   **Specs**: 3 x 256MB VMs.
-   **Storage**: 3GB Volume (Free allowance usually covers small usage).
-   **Why**: Very easy deployment (`fly launch`).
-   **Caveat**: Need to configure "Volumes" explicitly for SQLite, or data is lost on restart.

---

## 3. Recommended Architecture: Docker + Tailscale

Since you have 2 users, the safest zero-trust setup that costs $0 is:

**VPS (Oracle/GCP) running:**
1.  **Swift Equinox Container**: The app.
2.  **Tailscale**: VPN software.

**The Workflow:**
1.  Both users install Tailscale on their phones/laptops.
2.  Connect to the VPS IP (e.g., `100.x.x.x`).
3.  The app is NOT accessible to the public internet.

---

## 4. Deployment Steps (Docker)

I will create a `Dockerfile` for you.

### Step 1: Build Docker Image
```bash
docker build -t swift-equinox .
```

### Step 2: Run Container
```bash
# -v mounts the local DB file into the container for persistence
docker run -d \
  -p 8000:8000 \
  -v $(pwd)/vault.db:/app/vault.db \
  -v $(pwd)/snapshots:/app/snapshots \
  --name password-manager \
  swift-equinox
```

### Step 3: (Optional) Expose via Caddy (HTTPS)
If you must open it to the public internet (no Tailscale), use Caddy as a reverse proxy to handle HTTPS automatically.

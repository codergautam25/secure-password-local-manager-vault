
from fastapi import FastAPI, HTTPException, Depends, status, Request, UploadFile, File
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import os
import sqlite3
import csv
import io
import codecs

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

# Import our managers
# Note: assuming run from root directory
from backend.crypto_manager import CryptoManager
from backend import db_manager

app = FastAPI()

# 1. Rate Limiter Setup
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 2. Security Headers Middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

app.add_middleware(SecurityHeadersMiddleware)

# 3. Trusted Host Middleware (Prevents Host Header attacks)
# In production, add your domain. For local, localhost is fine.
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1"])

# 4. CORS (Restrict to frontend origin)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000"], # Adjust if frontend is served elsewhere
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Crypto Manager instance (stateful)
crypto = CryptoManager()

# Init DB on startup
@app.on_event("startup")
def startup_event():
    # Always run init to ensure all tables exist (attachments)
    db_manager.init_db()

# Models
class UnlockRequest(BaseModel):
    password: str

class InitRequest(BaseModel):
    password: str

class PasswordEntry(BaseModel):
    id: Optional[int] = None
    service: str
    username: str
    password: str
    
class PasswordResponse(BaseModel):
    id: int
    service: str
    username: str
    password: str # Decrypted

# Dependencies
def get_crypto():
    if not crypto.is_unlocked():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Vault is locked"
        )
    return crypto

# API Endpoints

@app.get("/api/status")
def get_status():
    """Check if vault is initialized and unlocked."""
    salt, _ = db_manager.get_master_config()
    is_initialized = salt is not None
    return {
        "initialized": is_initialized,
        "unlocked": crypto.is_unlocked()
    }

@app.post("/api/init")
@limiter.limit("5/minute")
def initialize_vault(req: InitRequest, request: Request):
    """Initialize the vault with a master password."""
    existing_salt, _ = db_manager.get_master_config()
    if existing_salt:
        raise HTTPException(status_code=400, detail="Vault already initialized")
        
    salt = crypto.generate_salt()
    # We verify the password by hashing it separately or just deriving again.
    # For now, let's just use the derived key logic.
    # Wait, we need to store a hash for verification so we know if unlock is correct 
    # WITHOUT trying to decrypt garbage.
    
    # Store salt and a hash of the password for verification
    # Using Argon2 hasher for verification storage
    pw_hash = crypto.ph.hash(req.password)
    
    db_manager.set_master_config(salt, pw_hash)
    
    # Auto-unlock
    crypto.unlock(req.password, salt)
    return {"message": "Vault initialized and unlocked"}

@app.post("/api/unlock")
@limiter.limit("5/minute")
def unlock_vault(req: UnlockRequest, request: Request):
    """Unlock the vault."""
    salt, stored_hash = db_manager.get_master_config()
    if not salt or not stored_hash:
        raise HTTPException(status_code=400, detail="Vault not initialized")
    
    # Verify password first
    try:
        crypto.ph.verify(stored_hash, req.password)
    except:
        raise HTTPException(status_code=401, detail="Invalid password")
        
    # Derive key
    success = crypto.unlock(req.password, salt)
    if not success:
        raise HTTPException(status_code=500, detail="Key derivation failed")
        
    return {"message": "Vault unlocked"}

@app.post("/api/lock")
def lock_vault():
    crypto.lock()
    return {"message": "Vault locked"}

@app.get("/api/passwords", response_model=List[PasswordResponse])
def list_passwords(c: CryptoManager = Depends(get_crypto)):
    rows = db_manager.get_passwords()
    results = []
    for row in rows:
        try:
            decrypted_pw = c.decrypt(row['nonce'], row['encrypted_data'])
            results.append({
                "id": row['id'],
                "service": row['service'],
                "username": row['username'],
                "password": decrypted_pw
            })
        except Exception as e:
            # Failed to decrypt? Metadata corruption or key issue?
            print(f"Failed to decrypt ID {row['id']}: {e}")
            continue
            
    return results

@app.post("/api/passwords", response_model=PasswordResponse)
def add_password(entry: PasswordEntry, c: CryptoManager = Depends(get_crypto)):
    encrypted = c.encrypt(entry.password)
    db_manager.store_password(
        entry.service, 
        entry.username, 
        encrypted['ciphertext'], 
        encrypted['nonce']
    )
    # Get ID? - a bit tricky with SQLite without returning it 
    # but let's just return what we have
    return {
        "id": 0, # Placeholder, in real app return strict ID
        "service": entry.service,
        "username": entry.username,
        "password": entry.password
    }

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

@app.post("/api/change-password")
@limiter.limit("5/minute")
def change_master_password(req: ChangePasswordRequest, request: Request, c: CryptoManager = Depends(get_crypto)):
    # 1. Verify current password hash from DB logic
    # (Though get_crypto implies we are unlocked, we double check 
    # to ensure the user knows the current password if we were unlocked for a while)
    _, stored_hash = db_manager.get_master_config()
    try:
        c.ph.verify(stored_hash, req.current_password)
    except:
        raise HTTPException(status_code=401, detail="Invalid current password")

    # 2. Get all existing passwords
    rows = db_manager.get_passwords()
    
    # 3. Decrypt everything into memory
    decrypted_entries = []
    for row in rows:
        try:
            pt = c.decrypt(row['nonce'], row['encrypted_data'])
            decrypted_entries.append({
                "id": row['id'], 
                "plaintext": pt
            })
        except Exception as e:
            # If we can't decrypt one, we shouldn't proceed with rotation
            # or we might lose that data forever.
            raise HTTPException(status_code=500, detail=f"Failed to decrypt password ID {row['id']}. Aborting rotation.")

    # 4. Generate new salt and verify hash for NEW password
    new_salt = c.generate_salt()
    new_pw_hash = c.ph.hash(req.new_password)
    
    # 5. Create a temporary CryptoManager to derive the NEW key
    # We don't want to mess up the global one until success
    temp_crypto = CryptoManager()
    if not temp_crypto.unlock(req.new_password, new_salt):
         raise HTTPException(status_code=500, detail="Failed to derive new key")

    # 6. Re-encrypt all entries with NEW key
    re_encrypted_entries = []
    for entry in decrypted_entries:
        enc = temp_crypto.encrypt(entry['plaintext'])
        re_encrypted_entries.append({
            "id": entry['id'],
            "encrypted_data": enc['ciphertext'],
            "nonce": enc['nonce']
        })
        
    # 7. Batch update DB
    try:
        db_manager.batch_update_passwords_and_config(re_encrypted_entries, new_salt, new_pw_hash)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database update failed: {e}")

    # 8. Update global crypto state
    # We must now unlock the global instance with the new password/salt
    # Actually simpler to just swap the instance key or call unlock again
    c.unlock(req.new_password, new_salt)
    
    return {"message": "Master password changed successfully"}

@app.post("/api/import")
@limiter.limit("5/minute")
def import_passwords(file: UploadFile = File(...), request: Request = None, c: CryptoManager = Depends(get_crypto)):
    try:
        content = file.file.read()
        # Decode bytes to string
        text = content.decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(text))
        
        # Normalize headers to lower case for easier matching
        # But DictReader uses the first line. We need to be careful.
        # Let's just inspect the fieldnames
        fieldnames = [f.lower() for f in csv_reader.fieldnames] if csv_reader.fieldnames else []
        
        # Mapping logic
        # We need: service (url/name/title), username, password
        
        candidates = {
            'service': ['url', 'name', 'title', 'location', 'website'],
            'username': ['username', 'user', 'email', 'login'],
            'password': ['password', 'pass', 'pword']
        }
        
        map_cols = {}
        for target, keys in candidates.items():
            for k in keys:
                if k in fieldnames:
                    # Find the actual original field name
                    idx = fieldnames.index(k)
                    map_cols[target] = csv_reader.fieldnames[idx]
                    break
        
        if 'password' not in map_cols:
             raise HTTPException(status_code=400, detail="Could not find a 'password' column in CSV.")
             
        # Prepare batch data
        batch_entries = []
        
        for row in csv_reader:
            # Extract data
            pwd = row.get(map_cols['password'], '')
            if not pwd: 
                continue # Skip empty passwords
                
            # Fallbacks for service/username
            svc = "Imported"
            if 'service' in map_cols:
                svc = row.get(map_cols['service'], '') or "Imported"
            
            usr = ""
            if 'username' in map_cols:
                usr = row.get(map_cols['username'], '')
                
            encrypt_res = c.encrypt(pwd)
            batch_entries.append({
                "service": svc,
                "username": usr,
                "encrypted_data": encrypt_res['ciphertext'],
                "nonce": encrypt_res['nonce']
            })
            
        # Batch insert into DB
        # We need a db_manager function for this or just loop store
        # db_manager.store_password does individual commits which is slow for bulk
        # Let's add a batch_store to db_manager? Or just loop for now, it's local SQLite.
        # Loop is fine for <1000 items. SQLite is fast.
        
        count = 0
        for entry in batch_entries:
            db_manager.store_password(entry['service'], entry['username'], entry['encrypted_data'], entry['nonce'])
            count += 1
            
        return {"message": f"Successfully imported {count} passwords."}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")

    
# Attachments API

@app.get("/api/passwords/{entry_id}/attachments")
def list_attachments(entry_id: int, c: CryptoManager = Depends(get_crypto)):
    rows = db_manager.get_attachments(entry_id)
    return [{"id": r["id"], "filename": r["filename"]} for r in rows]

@app.post("/api/passwords/{entry_id}/attachments")
@limiter.limit("10/minute")
def upload_attachment(entry_id: int, file: UploadFile = File(...), request: Request = None, c: CryptoManager = Depends(get_crypto)):
    try:
        content = file.file.read()
        filename = file.filename
        
        # Encrypt
        # Currently our encrypt method handle strings/bytes?
        # Let's check crypto_manager.
        # It expects data relative to bytes context. 
        # aesgcm.encrypt takes bytes.
        
        # We need to ensure content is bytes.
        if isinstance(content, str):
            content = content.encode()
            
        enc = c.encrypt_bytes(content)
        
        db_manager.add_attachment(entry_id, filename, enc['ciphertext'], enc['nonce'])
        return {"message": "Attachment uploaded"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from fastapi.responses import Response

@app.get("/api/attachments/{attachment_id}")
def download_attachment(attachment_id: int, c: CryptoManager = Depends(get_crypto)):
    row = db_manager.get_attachment(attachment_id)
    if not row:
        raise HTTPException(status_code=404, detail="Attachment not found")
        
    try:
        # Decrypt
        pt = c.decrypt_bytes(row['nonce'], row['encrypted_data'])
        
        # Return as downloadable file
        headers = {
            'Content-Disposition': f'attachment; filename="{row["filename"]}"'
        }
        return Response(content=pt, headers=headers, media_type="application/octet-stream")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Decryption failed: {e}")

@app.delete("/api/attachments/{attachment_id}")
def delete_attachment(attachment_id: int, c: CryptoManager = Depends(get_crypto)):
    db_manager.delete_attachment(attachment_id)
    return {"message": "Attachment deleted"}

# Serve static files
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Mount static directory
if not os.path.exists("static"):
    os.makedirs("static")
    
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_index():
    return FileResponse('static/index.html')

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

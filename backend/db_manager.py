
import sqlite3
import os
import time
import shutil
from backend.crypto_manager import CryptoManager

DB_FILE = "vault.db"
SNAPSHOT_DIR = "snapshots"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    if not os.path.exists(SNAPSHOT_DIR):
        os.makedirs(SNAPSHOT_DIR)
        
    conn = get_db_connection()
    c = conn.cursor()
    
    # Passwords table
    c.execute('''CREATE TABLE IF NOT EXISTS passwords (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    service TEXT NOT NULL,
                    username TEXT NOT NULL,
                    encrypted_data BLOB NOT NULL,
                    nonce BLOB NOT NULL
                )''')
                
    # Config table for salt and verification hash
    c.execute('''CREATE TABLE IF NOT EXISTS config (
                    key TEXT PRIMARY KEY,
                    value BLOB
                )''')

    # Attachments table
    c.execute('''CREATE TABLE IF NOT EXISTS attachments (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  password_id INTEGER,
                  filename TEXT,
                  encrypted_data BLOB,
                  nonce BLOB,
                  FOREIGN KEY(password_id) REFERENCES passwords(id))''')
    
    conn.commit()
    conn.close()

def create_snapshot():
    """Creates a backup of the database immediately before a write operation."""
    if os.path.exists(DB_FILE):
        timestamp = int(time.time())
        snapshot_name = os.path.join(SNAPSHOT_DIR, f"vault_{timestamp}.db")
        shutil.copy2(DB_FILE, snapshot_name)
        # Optional: Prune old snapshots - keeping simple for now

def store_password(service: str, username: str, encrypted_data: bytes, nonce: bytes):
    create_snapshot()
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT INTO passwords (service, username, encrypted_data, nonce) VALUES (?, ?, ?, ?)",
              (service, username, encrypted_data, nonce))
    conn.commit()
    conn.close()

def get_passwords():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM passwords")
    rows = c.fetchall()
    conn.close()
    return rows

def set_master_config(salt: bytes, password_hash: str):
    """Sets the master salt and verification hash."""
    # This is a critical initialization step.
    # We remove existing if any to reset.
    if os.path.exists(DB_FILE):
        # If resetting, we might want to wipe passwords too or handle migration.
        # For simplicity, assuming "first run" logic or overwrite.
        pass
        
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", ('salt', salt))
    c.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", ('password_hash', password_hash.encode()))
    conn.commit()
    conn.close()

def get_master_config():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT value FROM config WHERE key='salt'")
    salt_row = c.fetchone()
    c.execute("SELECT value FROM config WHERE key='password_hash'")
    hash_row = c.fetchone()
    conn.close()
    
    salt = salt_row['value'] if salt_row else None
    
    # decode hash if it exists
    pw_hash = hash_row['value'].decode() if hash_row else None
    
    return salt, pw_hash
    
def get_password_by_id(pw_id: int):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM passwords WHERE id=?", (pw_id,))
    row = c.fetchone()
    conn.close()
    return row

def update_password(pw_id: int, service: str, username: str, encrypted_data: bytes, nonce: bytes):
    create_snapshot()
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''UPDATE passwords 
                 SET service=?, username=?, encrypted_data=?, nonce=?
                 WHERE id=?''', 
              (service, username, encrypted_data, nonce, pw_id))
    conn.commit()
    conn.close()
    
def delete_password(pw_id: int):
    create_snapshot()
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM passwords WHERE id=?", (pw_id,))
    conn.commit()
    conn.close()

def batch_update_passwords_and_config(updated_entries, new_salt, new_pw_hash):
    """
    Updates multiple password entries and the master config in a single transaction.
    updated_entries: list of {id, encrypted_data, nonce} dicts
    """
    create_snapshot()
    conn = get_db_connection()
    c = conn.cursor()
    try:
        # 1. Update all passwords
        # We need to construct the list of tuples for executemany
        data = [(entry['encrypted_data'], entry['nonce'], entry['id']) for entry in updated_entries]
        c.executemany("UPDATE passwords SET encrypted_data=?, nonce=? WHERE id=?", data)
        
        # 2. Update config
        c.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", ('salt', new_salt))
        c.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", ('password_hash', new_pw_hash.encode()))
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

# Attachments
def add_attachment(password_id, filename, encrypted_data, nonce):
    create_snapshot()
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT INTO attachments (password_id, filename, encrypted_data, nonce) VALUES (?, ?, ?, ?)",
              (password_id, filename, encrypted_data, nonce))
    conn.commit()
    conn.close()

def get_attachments(password_id):
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT id, filename FROM attachments WHERE password_id=?", (password_id,))
    rows = c.fetchall()
    conn.close()
    return rows

def get_attachment(attachment_id):
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM attachments WHERE id=?", (attachment_id,))
    row = c.fetchone()
    conn.close()
    return row

def delete_attachment(attachment_id):
    create_snapshot()
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM attachments WHERE id=?", (attachment_id,))
    conn.commit()
    conn.close()

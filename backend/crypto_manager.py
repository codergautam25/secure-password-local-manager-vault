import os
import secrets
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from argon2 import PasswordHasher

class CryptoManager:
    def __init__(self):
        self.ph = PasswordHasher()
        self.master_key = None
        
    def derive_key(self, password: str, salt: bytes) -> bytes:
        """Derives a 32-byte key from the password using Argon2id."""
        # Using Argon2id implicitly via argon2-cffi which defaults to it.
        # However, to get a raw key for AES, we need a KDF.
        # Alternatively, we can use the hash parameters to derive a key, 
        # but a simpler approach with `argon2-cffi` for direct key derivation 
        # might be cleaner if we use the low-level API or just hash to a sufficient length.
        
        # Let's use the low-level `argon2.low_level.hash_secret_raw` 
        # to get raw bytes for the key.
        from argon2.low_level import hash_secret_raw, Type
        
        # Derive a 32-byte key (256 bits) for AES-256
        key = hash_secret_raw(
            secret=password.encode(),
            salt=salt,
            time_cost=30,    # Increased to 30
            memory_cost=204800, # Increased to ~200MB
            parallelism=4,
            hash_len=32,
            type=Type.ID
        )
        return key

    def generate_salt(self) -> bytes:
        return os.urandom(16)

    def unlock(self, password: str, stored_salt: bytes = None) -> bool:
        """
        Derives the master key from the password.
        If stored_salt is provided, it uses it.
        If not (first run), it generates a new salt (handled by caller typically).
        Returns True if successful (key derived).
        """
        if stored_salt is None:
            # This should only happen during initialization/reset
            # The caller handles salt generation and storage.
            return False
            
        try:
            self.master_key = self.derive_key(password, stored_salt)
            return True
        except Exception as e:
            print(f"Key derivation failed: {e}")
            return False

    def lock(self):
        """Clears the master key from memory."""
        self.master_key = None
        # In a real rigorous environment, we would zero out the memory,
        # but Python's GC makes this hard. Setting to None is a best effort.

    def is_unlocked(self) -> bool:
        return self.master_key is not None

    def encrypt(self, plaintext: str) -> dict:
        """Encrypts plaintext using AES-GCM. Returns nonce, ciphertext, and tag."""
        return self.encrypt_bytes(plaintext.encode())

    def encrypt_bytes(self, plaintext: bytes) -> dict:
        if not self.master_key:
            raise ValueError("Vault is locked.")
            
        aesgcm = AESGCM(self.master_key)
        nonce = os.urandom(12)
        # AESGCM.encrypt returns ciphertext + tag appended
        ciphertext_with_tag = aesgcm.encrypt(nonce, plaintext, None)
        
        return {
            "nonce": nonce,
            "ciphertext": ciphertext_with_tag
        }

    def decrypt(self, nonce: bytes, ciphertext_with_tag: bytes) -> str:
        """Decrypts ciphertext using AES-GCM."""
        return self.decrypt_bytes(nonce, ciphertext_with_tag).decode()
        
    def decrypt_bytes(self, nonce: bytes, ciphertext_with_tag: bytes) -> bytes:
        if not self.master_key:
            raise ValueError("Vault is locked.")
            
        aesgcm = AESGCM(self.master_key)
        plaintext = aesgcm.decrypt(nonce, ciphertext_with_tag, None)
        return plaintext

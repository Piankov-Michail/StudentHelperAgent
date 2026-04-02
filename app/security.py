from cryptography.fernet import Fernet
import os
from app.config import settings

class TokenEncryption:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # Ключ шифрования из env или генерируем новый
            key = os.getenv("ENCRYPTION_KEY")
            if not key:
                key = Fernet.generate_key().decode()
                print(f"⚠️  Сгенерирован новый ключ шифрования: {key}")
                print("⚠️  Добавьте его в .env как ENCRYPTION_KEY")
            cls._instance.cipher = Fernet(key.encode())
        return cls._instance
    
    def encrypt(self, token: str) -> str:
        return self.cipher.encrypt(token.encode()).decode()
    
    def decrypt(self, encrypted_token: str) -> str:
        return self.cipher.decrypt(encrypted_token.encode()).decode()

encryptor = TokenEncryption()
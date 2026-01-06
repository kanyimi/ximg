from cryptography.fernet import Fernet
from django.conf import settings

fernet = Fernet(settings.SECRET_NOTES_KEY.encode())


def encrypt_text(plain_text: str) -> str:
    return fernet.encrypt(plain_text.encode()).decode()


def decrypt_text(cipher_text: str) -> str:
    return fernet.decrypt(cipher_text.encode()).decode()

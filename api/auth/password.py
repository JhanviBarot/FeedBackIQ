from pwdlib import PasswordHash

_ph = PasswordHash.recommended()


def hash_password(plain: str) -> str:
    return _ph.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _ph.verify(plain, hashed)
    except Exception:
        return False

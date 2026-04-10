from datetime import datetime, timezone
import hashlib

import bcrypt
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.core.config import get_settings


settings = get_settings()
serializer = URLSafeTimedSerializer(settings.secret_key, salt="fastapi-admin")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    if not hashed_password:
        return False

    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(user_id: int) -> str:
    payload = {
        "uid": user_id,
        "ts": int(datetime.now(tz=timezone.utc).timestamp()),
    }
    return serializer.dumps(payload)


def decode_access_token(token: str) -> dict | None:
    try:
        return serializer.loads(token, max_age=settings.access_token_ttl_seconds)
    except (BadSignature, SignatureExpired):
        return None


def fingerprint_value(value: str | None) -> str | None:
    if not value:
        return None
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

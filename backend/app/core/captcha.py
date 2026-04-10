from datetime import datetime, timedelta
import random
import uuid

from app.core.config import get_settings


settings = get_settings()
_captcha_store: dict[str, tuple[str, datetime]] = {}
_captcha_chars = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"


def _purge_expired() -> None:
    now = datetime.utcnow()
    expired_keys = [key for key, (_, expires_at) in _captcha_store.items() if expires_at <= now]
    for key in expired_keys:
        _captcha_store.pop(key, None)


def _build_svg(code: str) -> str:
    line_elements = []
    for index in range(4):
        x1 = 10 + index * 28
        y1 = random.randint(8, 32)
        x2 = x1 + random.randint(12, 30)
        y2 = random.randint(8, 32)
        line_elements.append(
            f"<line x1='{x1}' y1='{y1}' x2='{x2}' y2='{y2}' "
            f"stroke='#d1d5db' stroke-width='1' />"
        )

    text_elements = []
    for index, char in enumerate(code):
        rotate = random.randint(-12, 12)
        x = 20 + index * 26
        y = random.randint(28, 34)
        text_elements.append(
            f"<text x='{x}' y='{y}' transform='rotate({rotate} {x} {y})' "
            f"font-size='24' font-weight='700' fill='#334155'>{char}</text>"
        )

    return (
        "<svg xmlns='http://www.w3.org/2000/svg' width='132' height='44' viewBox='0 0 132 44'>"
        "<rect width='132' height='44' rx='8' fill='#f8fafc' />"
        + "".join(line_elements)
        + "".join(text_elements)
        + "</svg>"
    )


def generate_captcha() -> tuple[str, str]:
    _purge_expired()
    captcha_id = uuid.uuid4().hex
    code = "".join(random.choice(_captcha_chars) for _ in range(4))
    expires_at = datetime.utcnow() + timedelta(seconds=settings.captcha_ttl_seconds)
    _captcha_store[captcha_id] = (code, expires_at)
    return captcha_id, _build_svg(code)


def verify_captcha(captcha_id: str, captcha_code: str) -> bool:
    _purge_expired()
    stored = _captcha_store.pop(captcha_id, None)
    if not stored:
        return False
    code, expires_at = stored
    if expires_at <= datetime.utcnow():
        return False
    return code.upper() == (captcha_code or "").strip().upper()

from datetime import timedelta
import random
import uuid

from app.core.config import get_settings
from app.core.redis_client import get_redis_client


settings = get_settings()
redis_client = get_redis_client()
_captcha_chars = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
_captcha_key_prefix = f"{settings.redis_key_prefix}:captcha"


def _build_captcha_code_key(captcha_id: str) -> str:
    return f"{_captcha_key_prefix}:code:{captcha_id}"


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
    captcha_id = uuid.uuid4().hex
    code = "".join(random.choice(_captcha_chars) for _ in range(4))
    captcha_svg = _build_svg(code)
    redis_client.setex(
        _build_captcha_code_key(captcha_id),
        timedelta(seconds=settings.captcha_ttl_seconds),
        code,
    )
    return captcha_id, captcha_svg


def verify_captcha(captcha_id: str, captcha_code: str) -> bool:
    code = redis_client.getdel(_build_captcha_code_key(captcha_id))
    if not code:
        return False
    return code.upper() == (captcha_code or "").strip().upper()

import base64
import html
import secrets
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.core.auth import ALGORITHM, JWT_SECRET

CAPTCHA_CODE_LENGTH = 5
CAPTCHA_EXPIRE_MINUTES = 5
CAPTCHA_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def generate_captcha_code() -> str:
    return "".join(secrets.choice(CAPTCHA_ALPHABET) for _ in range(CAPTCHA_CODE_LENGTH))


def create_captcha_token(code: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "purpose": "login_captcha",
        "code": code.upper(),
        "iat": now,
        "exp": now + timedelta(minutes=CAPTCHA_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)


def verify_captcha_token(token: str, user_input: str) -> bool:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
    except JWTError:
        return False

    return (
        payload.get("purpose") == "login_captcha"
        and payload.get("code") == user_input.strip().upper()
    )


def build_captcha_svg(code: str) -> str:
    escaped_code = html.escape(code)
    noise_lines = []
    for _ in range(6):
        x1 = secrets.randbelow(24)
        y1 = secrets.randbelow(56) + 8
        x2 = secrets.randbelow(180) + 20
        y2 = secrets.randbelow(56) + 8
        color = secrets.choice(["#d08a34", "#1f6f54", "#6f7169", "#b14d2f"])
        noise_lines.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="1.2" opacity="0.45" />'
        )

    noise_dots = []
    for _ in range(24):
        cx = secrets.randbelow(200)
        cy = secrets.randbelow(80)
        r = (secrets.randbelow(8) + 3) / 10
        color = secrets.choice(["#c9b08a", "#6d8f84", "#d9c6a3"])
        noise_dots.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{color}" opacity="0.75" />')

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="200" height="80" viewBox="0 0 200 80" role="img" aria-label="登录验证码">
  <defs>
    <linearGradient id="captchaBg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#fff8ee" />
      <stop offset="100%" stop-color="#f1e2c6" />
    </linearGradient>
  </defs>
  <rect width="200" height="80" rx="18" fill="url(#captchaBg)" />
  <rect x="1.5" y="1.5" width="197" height="77" rx="16.5" fill="none" stroke="#d5c19c" stroke-width="1.5" />
  {''.join(noise_lines)}
  {''.join(noise_dots)}
  <text x="100" y="50" text-anchor="middle" fill="#1d2724" font-size="32" font-family="'Trebuchet MS', 'Segoe UI', sans-serif" font-weight="700" letter-spacing="7" transform="rotate(-4 100 40)">{escaped_code}</text>
</svg>"""
    return svg


def build_captcha_data_url(svg: str) -> str:
    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"

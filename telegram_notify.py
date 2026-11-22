"""텔레그램 봇으로 알림 보내기.

설정은 telegram_token.json ({"bot_token": ..., "chat_id": ...}) 에 있습니다 (telegram_setup.py 가 생성).
환경변수 TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID 가 있으면 그것을 먼저 씁니다.
"""
import json
import os
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
TOKEN_FILE = ROOT / "telegram_token.json"


def _conf() -> tuple[str, str]:
    local = json.loads(TOKEN_FILE.read_text(encoding="utf-8")) if TOKEN_FILE.exists() else {}
    token = os.environ.get("TELEGRAM_BOT_TOKEN") or local.get("bot_token")
    chat = os.environ.get("TELEGRAM_CHAT_ID") or local.get("chat_id")
    if not token or not chat:
        raise RuntimeError("텔레그램 설정이 없습니다. telegram_setup.py 를 먼저 실행하세요.")
    return token, str(chat)


def api(token: str, method: str, **params) -> dict:
    r = requests.post(f"https://api.telegram.org/bot{token}/{method}", data=params, timeout=20)
    data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    if not data.get("ok"):
        # 오류 메시지에 토큰이 섞이지 않도록 설명만 남김
        raise RuntimeError(f"텔레그램 {method} 실패 {r.status_code}: {data.get('description', '')}")
    return data["result"]


def send(text: str, url: str | None = None) -> None:
    token, chat = _conf()
    params = {"chat_id": chat, "text": text[:4000]}
    if url:  # 메시지 아래 '게시글 보기' 버튼
        params["reply_markup"] = json.dumps({"inline_keyboard": [[{"text": "게시글 보기", "url": url}]]})
    api(token, "sendMessage", **params)

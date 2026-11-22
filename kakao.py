"""카카오톡 '나에게 보내기' (talk/memo/default/send).

키/토큰은 환경변수로 받습니다 (GitHub Actions 에서는 Secrets):
  KAKAO_REST_API_KEY, KAKAO_CLIENT_SECRET(선택), KAKAO_REFRESH_TOKEN
로컬에서는 환경변수가 없으면 kakao_token.json 을 사용합니다 (kakao_login.py 가 생성).

refresh token 은 약 2개월 유효하며, 만료 1개월 이내에 갱신하면 새 refresh token 이 발급됩니다.
새 토큰이 나오면 new_refresh_token.txt 에 적어두고, 워크플로가 이를 Secret 에 다시 저장합니다.
"""
import json
import os
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
TOKEN_FILE = ROOT / "kakao_token.json"
NEW_REFRESH_FILE = ROOT / "new_refresh_token.txt"
_access_token: str | None = None


def _local() -> dict:
    return json.loads(TOKEN_FILE.read_text(encoding="utf-8")) if TOKEN_FILE.exists() else {}


def rest_api_key() -> str:
    key = os.environ.get("KAKAO_REST_API_KEY") or _local().get("rest_api_key")
    if not key:
        raise RuntimeError("KAKAO_REST_API_KEY 가 없습니다.")
    return key


def client_secret() -> str | None:
    return os.environ.get("KAKAO_CLIENT_SECRET") or _local().get("client_secret") or None


def request_token(data: dict) -> dict:
    data = {**data, "client_id": rest_api_key()}
    if cs := client_secret():
        data["client_secret"] = cs
    r = requests.post("https://kauth.kakao.com/oauth/token", data=data, timeout=20)
    if r.status_code != 200:
        raise RuntimeError(f"토큰 요청 실패 {r.status_code}: {r.text}")
    return r.json()


def access_token() -> str:
    global _access_token
    if _access_token:
        return _access_token
    refresh = os.environ.get("KAKAO_REFRESH_TOKEN") or _local().get("refresh_token")
    if not refresh:
        raise RuntimeError("refresh token 이 없습니다. kakao_login.py 를 먼저 실행하세요.")
    tok = request_token({"grant_type": "refresh_token", "refresh_token": refresh})
    _access_token = tok["access_token"]
    if new := tok.get("refresh_token"):
        if os.environ.get("KAKAO_REFRESH_TOKEN"):
            NEW_REFRESH_FILE.write_text(new, encoding="utf-8")
        else:
            local = _local(); local["refresh_token"] = new
            TOKEN_FILE.write_text(json.dumps(local, indent=2), encoding="utf-8")
    return _access_token


def send_memo(text: str, url: str) -> None:
    if len(text) > 200:  # text 템플릿 최대 200자
        text = text[:197] + "..."
    template = {
        "object_type": "text",
        "text": text,
        "link": {"web_url": url, "mobile_web_url": url},
        "button_title": "게시글 보기",
    }
    r = requests.post(
        "https://kapi.kakao.com/v2/api/talk/memo/default/send",
        headers={"Authorization": f"Bearer {access_token()}"},
        data={"template_object": json.dumps(template, ensure_ascii=False)},
        timeout=20,
    )
    if r.status_code != 200 or r.json().get("result_code") != 0:
        raise RuntimeError(f"카톡 전송 실패 {r.status_code}: {r.text}")

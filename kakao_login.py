"""최초 1회 로컬에서 실행: 카카오 로그인 -> refresh token 발급 -> 테스트 메시지 전송.

python kakao_login.py <REST_API_KEY> [CLIENT_SECRET]

출력되는 refresh token 을 GitHub 저장소 Secret KAKAO_REFRESH_TOKEN 에 넣으세요.
"""
import json
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, quote, urlparse

import kakao

REDIRECT = "http://localhost:8765/callback"
result: dict = {}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        q = parse_qs(urlparse(self.path).query)
        result["code"] = (q.get("code") or [None])[0]
        result["error"] = (q.get("error_description") or [None])[0]
        msg = "로그인 완료! 이 창을 닫아도 됩니다." if result["code"] else f"실패: {result['error']}"
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(f"<h2 style='font-family:sans-serif'>{msg}</h2>".encode())

    def log_message(self, *a):
        pass


def main():
    if len(sys.argv) < 2:
        sys.exit("사용법: python kakao_login.py <REST_API_KEY> [CLIENT_SECRET]")
    local = {"rest_api_key": sys.argv[1], "client_secret": sys.argv[2] if len(sys.argv) > 2 else ""}
    kakao.TOKEN_FILE.write_text(json.dumps(local, indent=2), encoding="utf-8")

    url = ("https://kauth.kakao.com/oauth/authorize?response_type=code&scope=talk_message"
           f"&client_id={local['rest_api_key']}&redirect_uri={quote(REDIRECT, safe='')}")
    server = HTTPServer(("localhost", 8765), Handler)
    print("브라우저에서 카카오 로그인 후 '동의하고 계속하기'를 눌러주세요...")
    webbrowser.open(url)
    while "code" not in result:
        server.handle_request()
    if not result["code"]:
        sys.exit(f"인가 코드를 받지 못했습니다: {result['error']}")

    tok = kakao.request_token({"grant_type": "authorization_code", "code": result["code"], "redirect_uri": REDIRECT})
    local["refresh_token"] = tok["refresh_token"]
    kakao.TOKEN_FILE.write_text(json.dumps(local, indent=2), encoding="utf-8")

    kakao.send_memo("[핫딜 알리미] 카카오톡 연결 성공!", "https://www.fmkorea.com/hotdeal")
    print("\n카카오톡 '나와의 채팅'에 테스트 메시지를 보냈습니다.")
    print("\n아래 값을 GitHub Secret KAKAO_REFRESH_TOKEN 에 넣으세요:\n")
    print(tok["refresh_token"])


if __name__ == "__main__":
    main()

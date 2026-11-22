"""최초 1회: 텔레그램 봇 연결.

1) 텔레그램 @BotFather 에서 /newbot 으로 봇을 만들고 토큰을 받습니다.
2) 만든 봇과의 대화방을 열어 아무 메시지(예: 안녕)를 보냅니다.
3) python telegram_setup.py <봇_토큰>

봇에게 온 메시지에서 내 chat_id 를 찾아 telegram_token.json 에 저장하고 테스트 메시지를 보냅니다.
"""
import json
import sys

import telegram_notify as telegram


def main():
    if len(sys.argv) < 2:
        sys.exit("사용법: python telegram_setup.py <봇_토큰>")
    token = sys.argv[1].strip()

    me = telegram.api(token, "getMe")
    print(f"봇 확인: @{me['username']}")

    updates = telegram.api(token, "getUpdates")
    chats = {}
    for u in updates:
        msg = u.get("message") or u.get("edited_message") or {}
        chat = msg.get("chat") or {}
        if chat.get("type") == "private":
            chats[chat["id"]] = chat.get("first_name") or chat.get("username") or ""
    if not chats:
        sys.exit(f"봇에게 온 메시지가 없습니다. 텔레그램에서 @{me['username']} 에게 아무 메시지나 보낸 뒤 다시 실행하세요.")
    if len(chats) > 1:
        print("여러 사람이 봇에게 메시지를 보냈습니다. 가장 최근 사람으로 설정합니다:", chats)
    chat_id = list(chats)[-1]

    telegram.TOKEN_FILE.write_text(json.dumps({"bot_token": token, "chat_id": chat_id}, indent=2), encoding="utf-8")
    telegram.send("[핫딜 알리미] 텔레그램 연결 성공! 이제 이 대화방으로 알림이 옵니다.", "https://arca.live/b/hotdeal")
    print(f"연결 완료 ({chats[chat_id]}). 텔레그램에서 테스트 메시지를 확인하세요.")


if __name__ == "__main__":
    main()

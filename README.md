# 상품권 핫딜 알리미

아래 핫딜 게시판을 30분마다 확인해서,

- **아카라이브** 핫딜 — 상품권/쿠폰 카테고리 + 전체 최신글 1페이지
- **뽐뿌** 뽐뿌게시판 — 공식 RSS
- **루리웹** 유저 핫딜 — 공식 RSS
- **클리앙** 알뜰구매 — 목록 1페이지 (품절 표시된 글은 제외)
**구글 플레이 기프트카드 / 컬쳐랜드(문화상품권)** 글 중 **할인율 7% 이상**이면
**텔레그램 봇**으로 알려줍니다 (`config.json`의 `notify`에 `"kakao"`를 넣으면 카톡 "나와의 채팅"으로도 보냄).

할인율 판단 순서: 제목의 `%`/`퍼` 표기 → 제목의 액면가(예: 5만원권) 대비 가격 → 본문의 `%` 표기 → 가격 바로 위 권종으로 추정(27,900원 → 3만원권 7%).
설정(`config.json`): `minDiscount`, 제목 필터 정규식, 카테고리·검색어.

### 수집 원칙

- 요청은 브라우저로 위장하지 않고 `hotdeal-alert/1.0` 이라는 봇 이름을 그대로 밝힙니다.
- 펨코는 robots.txt에서 핫딜 게시판·검색의 자동 수집을 막고 있어 꺼 두었습니다 (`config.json`의 `fmkorea` 항목이 비어 있음).
- 아카라이브 검색 페이지는 봇에게 열려 있지 않아 쓰지 않습니다.
- 아카라이브는 데이터센터(GitHub Actions·클라우드 서버) IP의 봇 요청을 403으로 막습니다.
  그래서 **집 인터넷에 연결된 기기**(PC, 안드로이드 태블릿/폰, 라즈베리파이)에서 돌립니다.
- 뽐뿌·루리웹은 사이트가 자동 수집용으로 공식 제공하는 RSS를 씁니다 (robots.txt도 허용).
- 클리앙은 robots.txt가 게시판(`/service/board/`) 수집을 허용합니다.
- 퀘이사존·쿨엔조이는 robots.txt로 게시판 수집을 막고 있어 넣지 않았습니다.
- 한 사이트의 요청이 전부 거부(403/429/430)되면 그 사이트를 `blocked.json` 에 적고 알림을 보낸 뒤
  **그 사이트만 확인을 멈춥니다.** 우회하지 말고, 상황을 확인한 다음 `blocked.json` 에서 지우면 재개됩니다.
- 사이트를 새로 추가하면 그 사이트의 첫 실행은 이미 올라와 있던 글을 기록만 하고 알림을 보내지 않습니다.
- `seen.json` 에는 글 번호 대신 해시값만 저장합니다.

---

## 1. 텔레그램 봇 연결 (최초 1회)

1. 텔레그램에서 **@BotFather** 검색 → 대화 시작 → `/newbot`
2. 봇 이름(예: `핫딜 알리미`)과 사용자명(영문, `bot`으로 끝나야 함, 예: `my_giftcard_deal_bot`)을 입력
3. BotFather가 주는 **토큰**(`123456789:AA...` 형태)을 복사 — 비밀번호처럼 다루세요
4. BotFather 메시지의 `t.me/...` 링크로 내 봇 대화방을 열고 **시작(Start)** 을 누르거나 아무 메시지나 보내기
5. PC에서 실행
   ```powershell
   & "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" telegram_setup.py <봇_토큰>
   ```
   내 chat_id를 찾아 `telegram_token.json`에 저장하고, 봇 대화방으로 테스트 메시지를 보냅니다.

`telegram_token.json`은 git에 올라가지 않습니다(.gitignore). 기기를 옮길 때 이 파일도 같이 옮기세요.

## (선택) 카카오 앱 & 토큰

[developers.kakao.com](https://developers.kakao.com) → 내 애플리케이션 → 앱 추가 후:

1. **REST API 키**, **Client Secret** 복사 (앱 → 플랫폼 키)
2. **카카오 로그인** 사용 설정 ON, Redirect URI `http://localhost:8765/callback`
3. **동의항목** → 카카오톡 메시지 전송(talk_message) "선택 동의"
4. (선택) 웹 도메인에 `https://arca.live` 등록 — 카톡의 "게시글 보기" 버튼용

PC에서 한 번 로그인하면 `kakao_token.json` 이 만들어집니다 (refresh token은 실행할 때마다 자동 갱신).

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" kakao_login.py <REST_API_키> <Client_Secret>
```

`kakao_token.json` 은 비밀번호 같은 파일입니다. git에 올라가지 않으며(.gitignore), 채팅·메신저로 공유하지 마세요.

---

## 2. 윈도우 PC (현재 사용 중)

작업 스케줄러 작업 **HotdealAlert** 가 30분마다, 그리고 로그인할 때 `pythonw.exe hotdeal.py` 를 창 없이 실행합니다.
PC가 꺼져 있다가 켜지면 바로 한 번 실행되고, 상품권 카테고리 1페이지에 며칠치 글이 있어 꺼져 있던 동안의 딜도 대부분 잡힙니다.

- 로그 보기: `hotdeal.log`
- 일시정지 / 재개 / 삭제
  ```powershell
  Disable-ScheduledTask HotdealAlert
  ```
  ```powershell
  Enable-ScheduledTask HotdealAlert
  ```
  ```powershell
  Unregister-ScheduledTask HotdealAlert -Confirm:$false
  ```

---

## 3. 안드로이드 태블릿 / 폰 (Termux)

충전기에 꽂아 집 와이파이에 두면 24시간 돌릴 수 있습니다.

1. **Termux 설치** — [F-Droid](https://f-droid.org/packages/com.termux/) 또는 [GitHub 릴리스](https://github.com/termux/termux-app/releases)에서 받으세요
   (Play 스토어 버전은 오래돼서 패키지 설치가 안 될 수 있습니다). 같은 곳에서 **Termux:API** 도 설치하면 좋습니다.
2. **패키지 설치** (Termux에서)
   ```sh
   pkg update -y && pkg install -y python git cronie termux-services
   ```
   ```sh
   git clone https://github.com/hangeul970709-beep/hotdeal-alert ~/hotdeal-alert && cd ~/hotdeal-alert && pip install -r requirements.txt
   ```
3. **PC에서 `telegram_token.json`, `seen.json` 옮기기** — USB 케이블로 태블릿의 `Download` 폴더에 복사한 뒤:
   ```sh
   termux-setup-storage
   ```
   ```sh
   cp ~/storage/downloads/telegram_token.json ~/storage/downloads/seen.json ~/hotdeal-alert/ && rm ~/storage/downloads/telegram_token.json
   ```
4. **동작 확인**
   ```sh
   cd ~/hotdeal-alert && python hotdeal.py --test && python hotdeal.py --dry-run
   ```
5. **30분마다 실행 등록**
   ```sh
   sv-enable crond
   ```
   ```sh
   (crontab -l 2>/dev/null; echo '7,37 * * * * cd ~/hotdeal-alert && python hotdeal.py') | crontab -
   ```
   Termux를 한 번 껐다 켜서 `crond` 서비스가 뜨게 하세요.
6. **꺼지지 않게 하기**
   - 알림창의 Termux 알림에서 **Acquire wakelock** 누르기 (또는 `termux-wake-lock`)
   - 안드로이드 설정 → 앱 → Termux → 배터리 → **제한 없음(최적화 안 함)**
   - 삼성 기기는 설정 → 배터리 → 백그라운드 사용 제한에서 Termux를 **"절전 예외 앱"** 으로 추가
7. **PC 작업 끄기** (중복 알림 방지): PC에서 `Disable-ScheduledTask HotdealAlert`

---

## 4. 라즈베리파이 같은 소형 PC (리눅스)

1. **OS 설치** — [Raspberry Pi Imager](https://www.raspberrypi.com/software/)로 *Raspberry Pi OS Lite (64-bit)* 를 SD카드에 굽기.
   굽기 전 설정(톱니바퀴)에서 사용자 이름/비밀번호, 와이파이, **SSH 사용**을 켜두면 모니터 없이 설정할 수 있습니다.
2. **PC에서 접속** (사용자 이름이 `pi`, 호스트 이름이 `raspberrypi` 인 경우)
   ```powershell
   ssh pi@raspberrypi.local
   ```
3. **설치** (라즈베리파이에서)
   ```sh
   sudo apt update && sudo apt install -y git python3-venv
   ```
   ```sh
   git clone https://github.com/hangeul970709-beep/hotdeal-alert ~/hotdeal-alert && cd ~/hotdeal-alert && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
   ```
4. **PC에서 토큰·기록 파일 복사** (PC의 PowerShell에서)
   ```powershell
   scp C:\Users\LEE\.claude\hotdeal-alert\kakao_token.json C:\Users\LEE\.claude\hotdeal-alert\seen.json pi@raspberrypi.local:~/hotdeal-alert/
   ```
5. **동작 확인 & 30분마다 실행 등록** (라즈베리파이에서)
   ```sh
   cd ~/hotdeal-alert && .venv/bin/python hotdeal.py --test && .venv/bin/python hotdeal.py --dry-run
   ```
   ```sh
   (crontab -l 2>/dev/null; echo '7,37 * * * * cd ~/hotdeal-alert && .venv/bin/python hotdeal.py') | crontab -
   ```
6. **PC 작업 끄기**: PC에서 `Disable-ScheduledTask HotdealAlert`

---

## 기기를 옮길 때 체크리스트

- `telegram_token.json`(카톡도 쓰면 `kakao_token.json`)과 `seen.json` 을 **같이** 옮기기 (seen.json이 없으면 첫 실행은 기존 글을 기록만 하고 알림을 보내지 않습니다)
- 한 번에 **한 기기에서만** 돌리기 — 두 곳에서 돌리면 알림이 두 번 오고, refresh token이 갱신될 때 한쪽 토큰이 낡을 수 있습니다
- 카카오 refresh token은 약 2개월 동안 한 번도 안 쓰면 만료됩니다. 그러면 PC에서 `kakao_login.py` 를 다시 실행해 새 `kakao_token.json` 을 만드세요

## GitHub Actions 워크플로

`.github/workflows/hotdeal.yml` 은 남아 있지만, 아카라이브가 GitHub 서버 IP를 막기 때문에 **꺼 두었습니다**(disabled).
`--test` 카톡 전송 확인용으로만 수동 실행할 수 있습니다.

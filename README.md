# 상품권 핫딜 알리미

아카라이브 핫딜(상품권/쿠폰 카테고리 + 전체 최신글 1페이지)을
GitHub Actions에서 10분마다 확인해서, **구글 플레이 기프트카드 / 컬쳐랜드(문화상품권)** 글 중
**할인율 7% 이상**이면 카카오톡 "나와의 채팅"으로 알려줍니다. PC가 꺼져 있어도 돌아갑니다.

할인율 판단 순서: 제목의 `%`/`퍼` 표기 → 제목의 액면가(예: 5만원권) 대비 가격 → 본문의 `%` 표기 → 가격 바로 위 권종으로 추정(27,900원 → 3만원권 7%).
설정(`config.json`): `minDiscount`, 제목 필터 정규식, 카테고리·검색어.

> 펨코는 robots.txt에서 핫딜 게시판·검색의 자동 수집을 막고 있어 기본으로 꺼 두었습니다
> (`config.json`의 `fmkorea` 항목이 비어 있음). 코드는 남아 있어 값을 채우면 다시 켜집니다.
>
> 요청은 브라우저로 위장하지 않고 `hotdeal-alert/1.0` 이라는 봇 이름을 그대로 밝힙니다.
> 아카라이브 검색 페이지는 봇에게 열려 있지 않아 쓰지 않습니다. `seen.json`에는 글 번호 대신 해시값만 저장합니다.

---

## 1. 카카오 앱 만들기 (최초 1회)

[developers.kakao.com](https://developers.kakao.com) → 로그인 → **내 애플리케이션 → 애플리케이션 추가** (이름 아무거나)

1. **앱 키**에서 **REST API 키** 복사
2. **카카오 로그인** → 활성화 **ON**, **Redirect URI**에 `http://localhost:8765/callback` 등록
3. **카카오 로그인 → 동의항목** → **카카오톡 메시지 전송(talk_message)** 을 "선택 동의"로 설정
4. **플랫폼 → Web** → 사이트 도메인에 `https://www.fmkorea.com`, `https://arca.live` 등록 (카톡의 "게시글 보기" 버튼용)
5. **보안 → Client Secret** 이 "사용함"이면 코드값도 복사

(콘솔 메뉴 이름은 조금 다를 수 있습니다.)

## 2. 카카오 로그인 & 토큰 받기 (로컬, 최초 1회)

```powershell
cd C:\Users\LEE\.claude\hotdeal-alert
```
```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" kakao_login.py <REST_API_키> [<Client_Secret>]
```

브라우저에서 동의하면 카톡 "나와의 채팅"에 테스트 메시지가 오고, 터미널에 **refresh token** 이 출력됩니다.

## 3. GitHub에 올리기

1. GitHub에서 **Public** 저장소 생성 (예: `hotdeal-alert`, README 없이)
   - Public이어야 Actions 실행 시간이 무제한 무료입니다. 키는 코드가 아닌 Secrets에만 들어갑니다.
2. 이 폴더를 push
   ```powershell
   git init -b main; git add .; git commit -m "init"; git remote add origin https://github.com/<아이디>/hotdeal-alert.git; git push -u origin main
   ```
3. **Fine-grained Personal Access Token** 생성 (Settings → Developer settings → Fine-grained tokens)
   - Repository access: 이 저장소만 / Permissions: **Secrets: Read and write**
   - refresh token이 갱신될 때 워크플로가 Secret을 자동으로 바꾸는 데 씁니다.
4. 저장소 **Settings → Secrets and variables → Actions → New repository secret**
   | 이름 | 값 |
   |---|---|
   | `KAKAO_REST_API_KEY` | REST API 키 |
   | `KAKAO_CLIENT_SECRET` | Client Secret (안 쓰면 생략) |
   | `KAKAO_REFRESH_TOKEN` | 2단계에서 출력된 refresh token |
   | `GH_PAT` | 3번의 토큰 |
5. **Actions 탭 → hotdeal-alert → Run workflow** → `test` 체크 후 실행 → 카톡 수신 확인
6. 이후엔 10분마다 자동 실행. 첫 실행은 기존 글을 기록만 하고, 그 뒤 새로 올라오는 글만 알립니다.

## 참고

- 실행 기록: Actions 탭의 각 실행 로그 (`sent` / `skip` 줄)
- 목록 요청이 전부 실패하면 실행이 빨간색(실패)으로 표시됩니다 → 사이트가 GitHub 서버 IP를 차단한 것일 수 있습니다.
- 로컬 확인: `python hotdeal.py --dry-run` (전송·기록 없이 파싱 결과만 출력)

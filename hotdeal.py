"""상품권 핫딜 알리미: 펨코 / 아카라이브 핫딜 게시판 -> 카카오톡 '나에게 보내기'

python hotdeal.py            새 글 확인 후 조건 맞으면 카톡 전송, seen.json 갱신
python hotdeal.py --dry-run  전송/기록 없이 파싱 결과만 출력
python hotdeal.py --test     카톡 테스트 메시지 전송
"""
import argparse
import hashlib
import json
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

import kakao

ROOT = Path(__file__).resolve().parent
CFG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
SEEN_PATH = ROOT / "seen.json"
SESSION = requests.Session()
# 브라우저로 위장하지 않고 봇임을 그대로 밝힙니다. 사이트가 막으면(403) 그 의사를 따릅니다.
HEADERS = {
    "User-Agent": "hotdeal-alert/1.0 (personal gift card deal notifier)",
    "Accept-Language": "ko-KR,ko;q=0.9",
}


def seen_id(key: str) -> str:
    """글 번호를 그대로 저장하지 않도록 해시로 바꿉니다 (공개 저장소에 사이트 데이터가 남지 않게)."""
    return hashlib.sha256(f"hotdeal-alert:{key}".encode()).hexdigest()[:16]


LOG_PATH = ROOT / "hotdeal.log"
BLOCK_FLAG = ROOT / "blocked.flag"
WRITE_LOG = True  # --dry-run 이면 끔


def log(msg: str) -> None:
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S} {msg}"
    if sys.stdout:  # pythonw(창 없이 실행)에서는 stdout 이 없음
        print(line, flush=True)
    if WRITE_LOG:
        if LOG_PATH.exists() and LOG_PATH.stat().st_size > 1_000_000:  # 1MB 넘으면 뒤쪽 절반만 남김
            LOG_PATH.write_text(LOG_PATH.read_text(encoding="utf-8")[-500_000:], encoding="utf-8")
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(line + "\n")


@dataclass
class Deal:
    key: str
    site: str
    title: str
    mall: str
    price: int | None
    url: str


def get_html(url: str) -> BeautifulSoup:
    r = SESSION.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    r.encoding = "utf-8"
    return BeautifulSoup(r.text, "html.parser")


def to_won(s: str | None) -> int | None:
    d = re.sub(r"[^\d]", "", s or "")
    return int(d) if d and int(d) > 0 else None


def clean(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


# ---------- 게시판 파싱 ----------
def parse_fm(soup: BeautifulSoup) -> list[Deal]:
    deals = []
    for a in soup.select('h3.title a[class*="hotdeal_var8"]'):
        if "hotdeal_var8Y" in (a.get("class") or []):  # 종료된 딜
            continue
        href = a.get("href", "")
        m = re.search(r"document_srl=(\d+)", href) or re.match(r"/(\d+)", href)
        if not m:
            continue
        doc_id = m.group(1)
        t = a.select_one(".ellipsis-target")
        li = a.find_parent("li")
        info = clean(li.select_one(".hotdeal_info").get_text(" ")) if li and li.select_one(".hotdeal_info") else ""
        mall = re.search(r"쇼핑몰:\s*([^/]+)", info)
        price = re.search(r"가격:\s*([\d,]+)\s*원", info)
        deals.append(Deal(
            key=f"fm:{doc_id}", site="펨코",
            title=clean(t.get_text(" ") if t else a.get_text(" ")),
            mall=clean(mall.group(1)) if mall else "",
            price=to_won(price.group(1)) if price else None,
            url=f"https://www.fmkorea.com/{doc_id}",
        ))
    return deals


def parse_arca(soup: BeautifulSoup) -> list[Deal]:
    deals = []
    for row in soup.select("div.vrow.hybrid"):
        if row.select_one(".deal-close"):  # 종료된 딜
            continue
        a = row.select_one("a.title.hybrid-title")
        if not a:
            continue
        m = re.search(r"/b/hotdeal/(\d+)", a.get("href", ""))
        if not m:
            continue
        for junk in a.select(".info, .media-icon"):
            junk.decompose()
        store = row.select_one(".deal-store")
        price = row.select_one(".deal-price")
        deals.append(Deal(
            key=f"arca:{m.group(1)}", site="아카",
            title=clean(a.get_text(" ")),
            mall=clean(store.get_text()) if store else "",
            price=to_won(price.get_text()) if price else None,
            url=f"https://arca.live/b/hotdeal/{m.group(1)}",
        ))
    return deals


def list_urls() -> list[tuple[str, callable]]:
    urls = []
    for c in CFG["fmkorea"]["categories"]:
        urls.append((f"https://www.fmkorea.com/index.php?mid=hotdeal&category={c}", parse_fm))
    for kw in CFG["fmkorea"]["searchKeywords"]:
        urls.append((f"https://www.fmkorea.com/search.php?mid=hotdeal&search_target=title&search_keyword={quote(kw)}", parse_fm))
    for c in CFG["arca"]["categories"]:  # "" = 전체 최신글
        urls.append(("https://arca.live/b/hotdeal" + (f"?category={c}" if c else ""), parse_arca))
    for kw in CFG["arca"]["searchKeywords"]:
        urls.append((f"https://arca.live/b/hotdeal?target=title&keyword={quote(kw)}", parse_arca))
    return urls


def post_text(deal: Deal) -> str:
    soup = get_html(deal.url)
    node = soup.select_one("article") if deal.site == "펨코" else soup.select_one(".article-content")
    text = clean(node.get_text(" ")) if node else ""
    return text.split("유사한 최근")[0]


# ---------- 할인율 ----------
def percent_in(text: str) -> float | None:
    vals = [float(v) for v in re.findall(r"(\d{1,2}(?:\.\d+)?)\s*(?:%|퍼(?:센트)?|프로)", text)]
    vals = [v for v in vals if 1 <= v <= 30]
    return max(vals) if vals else None


def face_value(text: str) -> float | None:
    faces = [float(v) * 10000 for v in re.findall(r"(\d+(?:\.\d+)?)\s*만\s*원?", text)]
    faces += [float(v.replace(",", "")) for v in re.findall(r"(\d{1,3}(?:,\d{3})+)\s*원\s*권", text)]
    if not faces:
        return None
    face = max(faces)
    q = re.search(r"[x×X*]\s*(\d{1,2})(?!\d)|(\d{1,2})\s*(?:장|매)", text)
    if q:
        n = int(q.group(1) or q.group(2))
        if n > 1:
            face *= n
    return face


DENOMS = [10000, 20000, 30000, 50000, 100000, 150000, 200000, 300000, 500000, 1000000]


def discount(deal: Deal) -> tuple[float, str] | None:
    # 1) 제목의 % 표기
    if (p := percent_in(deal.title)) is not None:
        return p, "제목"
    # 2) 제목의 액면가 vs 가격
    face = face_value(deal.title)
    if face and deal.price and deal.price < face:
        r = round((1 - deal.price / face) * 100, 1)
        if 0 < r <= 30:
            return r, f"액면 {face:,.0f}원"
    # 3) 본문의 % 표기
    try:
        if (p := percent_in(post_text(deal))) is not None:
            return p, "본문"
    except Exception as e:
        log(f"본문 읽기 실패 {deal.url}: {e}")
    # 4) 가격 바로 위 일반 권종으로 추정 (27,900원 -> 3만원권 7%)
    if deal.price:
        d = next((d for d in DENOMS if d >= deal.price), None)
        if d:
            r = round((1 - deal.price / d) * 100, 1)
            if 0 < r <= 15:
                return r, f"추정 {d:,}원권"
    return None


# ---------- 메인 ----------
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--test", action="store_true")
    args = ap.parse_args()
    global WRITE_LOG
    WRITE_LOG = not args.dry_run

    if args.test:
        kakao.send_memo("[핫딜 알리미] 테스트 메시지입니다. 연결 성공!", "https://arca.live/b/hotdeal")
        log("테스트 메시지 전송 완료")
        return 0

    if BLOCK_FLAG.exists() and not args.dry_run:
        log("정지 중: 사이트 차단이 감지돼 멈춘 상태입니다. 확인 후 blocked.flag 를 지우면 재개됩니다.")
        return 0

    seen: list[str] = json.loads(SEEN_PATH.read_text(encoding="utf-8")) if SEEN_PATH.exists() else []
    seen_set = set(seen)
    first_run = not seen_set and not CFG.get("notifyOnFirstRun", False)

    deals: dict[str, Deal] = {}
    errors = forbidden = 0
    urls = list_urls()
    for url, parser in urls:
        try:
            for d in parser(get_html(url)):
                deals.setdefault(d.key, d)
        except Exception as e:
            errors += 1
            if isinstance(e, requests.HTTPError) and e.response is not None and e.response.status_code in (403, 429, 430):
                forbidden += 1
            log(f"목록 실패 {url}: {e}")
        time.sleep(1.5)

    # 모든 목록이 거부(403 등)되면 사이트가 이 봇을 막은 것으로 보고 스스로 멈춥니다 (우회하지 않음).
    if forbidden == len(urls) and not args.dry_run:
        BLOCK_FLAG.write_text(datetime.now().isoformat(), encoding="utf-8")
        log("사이트가 요청을 거부해 알리미를 멈췄습니다.")
        try:
            kakao.send_memo("[핫딜 알리미] 사이트가 요청을 거부해서 알리미를 멈췄어요. "
                            "확인 후 blocked.flag 파일을 지우면 다시 돌아갑니다.", "https://arca.live/b/hotdeal")
        except Exception as e:
            log(f"정지 알림 전송 실패: {e}")
        return 1

    title_re = re.compile(CFG["titleFilter"], re.I)
    sent = 0
    for d in deals.values():
        if not title_re.search(d.title):
            continue
        sid = seen_id(d.key)
        if sid in seen_set and not args.dry_run:
            continue
        if first_run and not args.dry_run:  # 첫 실행: 기존 글은 기록만 하고 알림 안 보냄
            seen.append(sid); seen_set.add(sid)
            continue

        disc = discount(d)
        rate_txt = f"{disc[0]}% ({disc[1]})" if disc else "할인율 미확인"
        price_txt = f"{d.price:,}원" if d.price else "-"
        ok = disc is not None and disc[0] >= CFG["minDiscount"]

        if args.dry_run:
            print(f"[{d.site}] {d.title} | {price_txt} | {rate_txt} | {'=> 알림 ' if ok else ''}{d.url}")
            continue

        if ok:
            text = f"🔥 상품권 핫딜 {disc[0]}%\n{d.title}\n가격: {price_txt} / {d.mall}\n할인율: {rate_txt}\n[{d.site}] {d.url}"
            try:
                kakao.send_memo(text, d.url)
                sent += 1
                log(f"sent {d.key} {rate_txt} {d.title}")
            except Exception as e:
                log(f"카톡 전송 실패 {d.key}: {e}")
                continue  # 다음 실행 때 재시도
        else:
            log(f"skip {d.key} {rate_txt} {d.title}")
        seen.append(sid); seen_set.add(sid)

    if not args.dry_run:
        SEEN_PATH.write_text(json.dumps(seen[-3000:], ensure_ascii=False, indent=0), encoding="utf-8")
        log(f"완료: 수집 {len(deals)}건, 전송 {sent}건, 목록 오류 {errors}건" + (" (첫 실행: 기존 글 기록)" if first_run else ""))
    # 모든 목록 요청이 실패하면 차단 가능성 -> Actions 실패로 표시해 알 수 있게
    return 1 if errors and not deals else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        import traceback
        log("오류:\n" + traceback.format_exc())
        sys.exit(1)

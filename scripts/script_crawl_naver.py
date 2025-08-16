import os
import re
import time
import html
import argparse
import requests
import pandas as pd
from difflib import SequenceMatcher
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from itertools import cycle
from threading import Lock

# ----- 환경 변수 로드 -----
load_dotenv()

RESULT_CACHE = {}
CACHE_LOCK = Lock() 

def norm_query(q: str) -> str:
    return re.sub(r"\s+", " ", (q or "").strip().lower())

CID_LIST  = [x.strip() for x in os.getenv("NAVER_CLIENT_IDS", "").split(",") if x.strip()]
CSEC_LIST = [x.strip() for x in os.getenv("NAVER_CLIENT_SECRETS", "").split(",") if x.strip()]

if len(CID_LIST) != len(CSEC_LIST):
    raise SystemExit("CID 개수와 CSEC 개수가 일치해야 합니다. (.env의 NAVER_CLIENT_IDS / NAVER_CLIENT_SECRETS 확인)")

if not CID_LIST:
    raise SystemExit("최소 1개의 키가 필요합니다. .env에 NAVER_CLIENT_IDS, NAVER_CLIENT_SECRETS를 설정하세요.")

API_URL = "https://openapi.naver.com/v1/search/shop.json"

# 라운드로빈 인덱스 관리 (멀티스레드 안전)
KEY_CYCLE = cycle(zip(CID_LIST, CSEC_LIST))
KEY_LOCK = Lock()

def get_next_headers():
    with KEY_LOCK:
        cid, csec = next(KEY_CYCLE)
    return {
        "X-Naver-Client-Id": cid,
        "X-Naver-Client-Secret": csec,
    }

# ----- 세션(재시도/타임아웃) -----
def make_session():
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    s = requests.Session()
    retry = Retry(
        total=5,
        connect=3, read=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=100, pool_maxsize=100)
    s.mount("https://", adapter)
    return s

SESSION = make_session()

# ----- 네이버 쇼핑 API 호출 (키 순환 + 가벼운 429 백오프) -----
def search_shop(query, display=3, sort="asc", exclude_used=False, max_retry=4):
    params = {"query": query, "display": display, "sort": sort}
    if exclude_used:
        params["exclude"] = "used:cbshop"

    backoff = 0.0
    for attempt in range(max_retry):
        headers = get_next_headers()  # 키 라운드로빈
        try:
            resp = SESSION.get(API_URL, headers=headers, params=params, timeout=(3, 6))
        except requests.Timeout:
            backoff = max(backoff * 2, 0.5)  # 0.5s, 1s, 2s ...
            time.sleep(backoff)
            continue

        if resp.status_code == 200:
            return resp.json().get("items", [])
        if resp.status_code == 429:
            # 한도 → 살짝 쉬고 다음 키 시도
            backoff = max(backoff * 2, 0.5)
            time.sleep(backoff)
            continue

        # 기타 에러는 재시도(완전 침묵하려면 출력 제거)
        # print(f"[DEBUG] {resp.status_code} {query} {(resp.text or '')[:100]}")
        time.sleep(0.3)
    resp.raise_for_status()

# ----- 유틸 -----
def strip_tags(text: str) -> str:
    if not isinstance(text, str):
        return ""
    return re.sub(r"</?b>", "", html.unescape(text))

def build_query(row):
    name = str(row.get("food_name", "") or "").strip()
    company = str(row.get("company_name", "") or "").strip()
    return f"{company} {name}".strip() if company else name

def similarity(a: str, b: str) -> float:
    a = (a or "").lower()
    b = (b or "").lower()
    return SequenceMatcher(None, a, b).ratio()

def choose_best_item(items, target_name: str):
    """
    1) 유사도 >= 0.6 후보 중 최저가
    2) 없으면 유사도 최댓값
    """
    if not items:
        return None
    cleaned = []
    for it in items:
        title = strip_tags(it.get("title", ""))
        lprice = it.get("lprice")
        try:
            lprice_num = int(lprice) if lprice and str(lprice).isdigit() else 10**12
        except Exception:
            lprice_num = 10**12
        cleaned.append((it, title, lprice_num, similarity(title, target_name)))

    good = [x for x in cleaned if x[3] >= 0.6]
    if good:
        good.sort(key=lambda x: (x[2], -x[3]))  # 가격↑, 유사도↓
        return good[0][0]

    cleaned.sort(key=lambda x: x[3], reverse=True)
    return cleaned[0][0]

def process_row(idx, row, exclude_used, throttle_sec):
    """단일 행 처리 함수 (병렬 실행 대상)"""
    q = build_query(row)
    if not q:
        return idx, None, "[SKIP] 빈 쿼리"

    nq = norm_query(q)

    # 1) 캐시 조회 (락)
    with CACHE_LOCK:
        cached = RESULT_CACHE.get(nq)

    if cached is not None or nq in RESULT_CACHE:
        # 캐시에 결과가 있거나, 과거에 '없음(None)'을 기록했다면 바로 사용
        best = cached
    else:
        # 2) API 호출
        try:
            items = search_shop(q, display=3, sort="asc", exclude_used=exclude_used)
            best = choose_best_item(items, str(row.get("food_name", "")))
        except (requests.ReadTimeout, requests.ConnectTimeout):
            return idx, None, "[TIMEOUT]"
        except requests.HTTPError as e:
            return idx, None, f"[HTTP {getattr(e.response,'status_code','???')}]"
        except Exception as e:
            return idx, None, f"[ERROR] {e}"

        # 3) 캐시에 저장 (락)
        with CACHE_LOCK:
            RESULT_CACHE[nq] = best  # best가 None이어도 저장 → 재호출 방지

    # 과호출 방지(안전장치). 이미 search_shop이 적응형 백오프라면 0~소폭으로 줄여도 됨.
    if throttle_sec:
        time.sleep(throttle_sec)

    if best:
        return idx, {
            "naver_title": strip_tags(best.get("title", "")),
            "lprice": best.get("lprice", ""),
            "hprice": best.get("hprice", ""),
            "image": best.get("image", ""),
            "product_link": best.get("link", ""),
            "mallName": best.get("mallName", "")
        }, None

    return idx, None, None

def is_empty(v):
    if v is None:
        return True
    s = str(v).strip()
    return s == "" or s.lower() in {"nan", "none"}

def enrich_parallel(df, throttle_sec=0.15, limit=None, exclude_used=False, resume=False, workers=5, checkpoint_every=2000, out_path=None):
    out_cols = ["naver_title", "lprice", "hprice", "image", "product_link", "mallName"]
    for col in out_cols:
        if col not in df.columns:
            df[col] = ""

    base = df.head(int(limit)) if limit else df

    if resume:
        has_lprice = base["lprice"].apply(lambda x: not is_empty(x)) if "lprice" in base.columns else pd.Series(False, index=base.index)
        has_image  = base["image"].apply(lambda x: not is_empty(x))  if "image"  in base.columns else pd.Series(False, index=base.index)
        todo_df = base[~(has_lprice & has_image)]
    else:
        todo_df = base

    rows = list(todo_df.iterrows())
    total = len(rows)
    if total == 0:
        return df

    processed_since_save = 0

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(process_row, idx, row, exclude_used, throttle_sec): idx
            for idx, row in rows
        }
        for fut in tqdm(as_completed(futures), total=total, desc="Processing", ncols=100, mininterval=0.5, leave=False):
            idx, result, _ = fut.result()
            if result:
                for k, v in result.items():
                    df.at[idx, k] = v

            processed_since_save += 1
            if out_path and checkpoint_every and processed_since_save >= checkpoint_every:
                df.to_csv(out_path, index=False, encoding="utf-8")
                processed_since_save = 0  # reset

    # 마지막 저장 보장
    if out_path:
        df.to_csv(out_path, index=False, encoding="utf-8")

    return df

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--in",  dest="in_path",  required=True)
    parser.add_argument("--out", dest="out_path", required=True)
    parser.add_argument("--sep", dest="sep", default=",", help="CSV delimiter, 탭이면 '\\t'")
    parser.add_argument("--sleep", dest="sleep", type=float, default=0.15, help="요청 간 딜레이(초)")
    parser.add_argument("--limit", dest="limit", type=int, default=None, help="상위 N행만 처리(테스트용)")
    parser.add_argument("--exclude-used", action="store_true", help="중고/중개 상품 제외")
    parser.add_argument("--resume", action="store_true", help="이미 처리한 행 건너뛰기")
    parser.add_argument("--workers", type=int, default=5, help="동시 실행 스레드 수")
    args = parser.parse_args()

    # 단일 키 검사 코드 제거 → 리스트 검사로 대체했으므로 불필요

    in_lower = args.in_path.lower()
    if in_lower.endswith((".xlsx", ".xls")):
        df = pd.read_excel(args.in_path, dtype=str, keep_default_na=False)
    else:
        df = pd.read_csv(args.in_path, sep=args.sep, dtype=str, keep_default_na=False, encoding="utf-8")

    df = enrich_parallel(
        df,
        throttle_sec=args.sleep,
        limit=args.limit,
        exclude_used=args.exclude_used,
        resume=args.resume,
        workers=args.workers,
        checkpoint_every=2000,
        out_path=args.out_path,
    )
    df.to_csv(args.out_path, index=False, encoding="utf-8")
    print(f"Saved: {args.out_path}")

if __name__ == "__main__":
    main()
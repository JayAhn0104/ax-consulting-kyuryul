"""네이버 쇼핑 검색 API로 상위 상품의 카테고리를 집계한다.

클라이언트의 기존 판단 방식(검색 상위 상품의 카테고리를 따름)을 재현.
검색 API 결과의 광고 포함 여부와 화면 순위 일치 여부는 미확인.

사용: uv run scripts/search_category.py "<검색어>" [--top 10]
출력: 카테고리 경로별 개수(JSON)
"""

import argparse
import json
import sys
from collections import Counter

import requests

from lib import secrets

URL = "https://openapi.naver.com/v1/search/shop.json"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("query")
    parser.add_argument("--top", type=int, default=10)
    args = parser.parse_args()

    keys = secrets()
    cid, csecret = keys.get("NAVER_SEARCH_CLIENT_ID"), keys.get("NAVER_SEARCH_CLIENT_SECRET")
    if not cid or not csecret:
        sys.exit("검색 API 키 미설정: config/secrets.env의 NAVER_SEARCH_CLIENT_ID / SECRET 필요")

    res = requests.get(
        URL,
        params={"query": args.query, "display": args.top, "sort": "sim"},
        headers={"X-Naver-Client-Id": cid, "X-Naver-Client-Secret": csecret},
        timeout=10,
    )
    res.raise_for_status()
    items = res.json().get("items", [])

    paths = Counter()
    samples = []
    for item in items:
        path = " > ".join(c for c in (item.get(f"category{i}") for i in range(1, 5)) if c)
        paths[path] += 1
        samples.append({"title": item.get("title", "").replace("<b>", "").replace("</b>", ""),
                        "mall": item.get("mallName"), "category": path})

    print(json.dumps({
        "query": args.query,
        "count": len(items),
        "categories": [{"path": p, "count": n} for p, n in paths.most_common()],
        "items": samples,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

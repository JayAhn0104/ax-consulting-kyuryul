"""네이버 쇼핑인사이트(NAVER API HUB)로 카테고리 수요와 키워드 클릭 추이를 비교한다.

- categories: 카테고리별 클릭량 비교. API는 요청당 3개까지만 받으므로 첫 카테고리를 기준(100)으로 환산해 여러 개를 비교
- keywords:   한 카테고리 안에서 키워드별 클릭량 비교 (요청당 최대 5개)
값은 상대값이며, 기간은 최근 3개월(지난달까지).

주의: 쇼핑 검색 API는 2026-07-31 종료되어 '검색 상위 상품의 카테고리'는 조회할 수 없음.

사용:
  uv run scripts/shopping_insight.py categories 50001783 50001782 50001787
  uv run scripts/shopping_insight.py keywords --category 50001783 송오브인디아 드라세나
"""

import argparse
import json
import sys
from datetime import date, timedelta

import requests

from lib import CONFIG, secrets

BASE = "https://naverapihub.apigw.ntruss.com/shopping/v1"


def headers():
    keys = secrets()
    cid, csecret = keys.get("NAVER_APIHUB_CLIENT_ID"), keys.get("NAVER_APIHUB_CLIENT_SECRET")
    if not cid or not csecret:
        sys.exit("API HUB 키 미설정: config/secrets.env의 NAVER_APIHUB_CLIENT_ID / SECRET 필요")
    return {"X-NCP-APIGW-API-KEY-ID": cid, "X-NCP-APIGW-API-KEY": csecret, "Content-Type": "application/json"}


def period():
    first_this_month = date.today().replace(day=1)
    end = first_this_month - timedelta(days=1)
    start = (end.replace(day=1) - timedelta(days=62)).replace(day=1)
    return {"startDate": start.isoformat(), "endDate": end.isoformat(), "timeUnit": "month"}


def post(path, body):
    res = requests.post(BASE + path, headers=headers(), data=json.dumps(body), timeout=15)
    if res.status_code != 200:
        sys.exit(f"쇼핑인사이트 오류 ({res.status_code}): {res.text[:300]}")
    return {r["title"]: sum(d["ratio"] for d in r["data"]) for r in res.json()["results"]}


def category_names():
    path = CONFIG / "codes" / "categories.json"
    if not path.exists():
        return {}
    return {str(c["id"]): c["wholeCategoryName"].split(">")[-1] for c in json.loads(path.read_text(encoding="utf-8"))}


def compare_categories(codes):
    names = category_names()
    label = {c: names.get(c, c) for c in codes}
    anchor, others = codes[0], codes[1:]
    scores = {anchor: 100.0}
    for i in range(0, max(len(others), 1), 2):
        batch = [anchor, *others[i:i + 2]]
        totals = post("/categories", {**period(), "category": [{"name": label[c], "param": [c]} for c in batch]})
        base = totals.get(label[anchor]) or 1
        for c in batch[1:]:
            scores[c] = round(totals.get(label[c], 0) / base * 100, 1)
    ranked = sorted(scores.items(), key=lambda kv: -kv[1])
    return [{"code": c, "name": label[c], "score": s} for c, s in ranked]


def compare_keywords(category, keywords):
    if len(keywords) > 5:
        sys.exit("키워드는 한 번에 5개까지 비교 가능")
    totals = post("/category/keywords", {**period(), "category": category,
                                         "keyword": [{"name": k, "param": [k]} for k in keywords]})
    top = max(totals.values()) or 1
    ranked = sorted(((k, round(totals.get(k, 0) / top * 100, 1)) for k in keywords), key=lambda kv: -kv[1])
    return [{"keyword": k, "score": s} for k, s in ranked]


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="command", required=True)
    c = sub.add_parser("categories")
    c.add_argument("codes", nargs="+", help="카테고리 코드 (첫 번째가 기준 100)")
    k = sub.add_parser("keywords")
    k.add_argument("--category", required=True)
    k.add_argument("keywords", nargs="+")
    args = ap.parse_args()

    p = period()
    if args.command == "categories":
        result = {"period": p, "basis": "카테고리 클릭량 합계, 첫 카테고리 = 100", "categories": compare_categories(args.codes)}
    else:
        result = {"period": p, "category": args.category, "basis": "카테고리 내 키워드 클릭량 합계, 최대 = 100",
                  "keywords": compare_keywords(args.category, args.keywords)}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

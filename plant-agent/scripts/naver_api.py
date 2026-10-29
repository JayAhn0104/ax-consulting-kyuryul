# /// script
# requires-python = ">=3.11"
# dependencies = ["requests", "bcrypt"]
# ///
"""네이버 커머스API 연동: 인증, 카테고리 조회, 이미지 업로드, 상품 등록·조회·공개 전환.

주의: 엔드포인트와 요청 필드는 공개 문서·공식 저장소 토론을 근거로 작성됨.
      실제 API 키로 시험하기 전까지는 'token', 'categories'로 연결만 확인할 것.

사용:
  uv run scripts/naver_api.py token                       # 인증 확인
  uv run scripts/naver_api.py categories [--find 관엽]     # 카테고리 코드표 다운로드·검색
  uv run scripts/naver_api.py payload  <상품폴더>          # 등록 요청 내용 생성만 (전송 안 함)
  uv run scripts/naver_api.py register <상품폴더>          # 비공개 상태로 등록
  uv run scripts/naver_api.py verify   <상품폴더>          # 등록 내용 재조회·비교
  uv run scripts/naver_api.py publish  <상품폴더>          # 판매 공개 전환
"""

import argparse
import base64
import json
import re
import sys
import time
from pathlib import Path

import bcrypt
import requests

from lib import CONFIG, load_product, product_dir, save_product, secrets, store_config

BASE = "https://api.commerce.naver.com/external"
IMG_SRC = re.compile(r'(<img\s[^>]*src\s*=\s*["\'])([^"\']+)(["\'])', re.I)


# ---------- 인증 ----------

def get_token():
    keys = secrets()
    cid, csecret = keys.get("NAVER_COMMERCE_CLIENT_ID"), keys.get("NAVER_COMMERCE_CLIENT_SECRET")
    if not cid or not csecret:
        sys.exit("커머스API 키 미설정: config/secrets.env의 NAVER_COMMERCE_CLIENT_ID / SECRET 필요")
    ts = str(int(time.time() * 1000))
    sign = base64.b64encode(bcrypt.hashpw(f"{cid}_{ts}".encode(), csecret.encode())).decode()
    res = requests.post(f"{BASE}/v1/oauth2/token", data={
        "client_id": cid, "timestamp": ts, "client_secret_sign": sign,
        "grant_type": "client_credentials", "type": "SELF",
    }, timeout=10)
    if res.status_code != 200:
        explain(res)
    return res.json()["access_token"]


def explain(res):
    """오류 응답을 클라이언트가 이해할 수 있는 문장으로 바꿔 종료."""
    text = res.text[:500]
    if res.status_code in (401, 403) and ("IP" in text or "ip" in text):
        sys.exit("API 접근 차단: 현재 인터넷 IP가 커머스API센터에 등록된 IP와 다름. IP 재등록 필요.\n" + text)
    sys.exit(f"API 오류 ({res.status_code}). 추적 ID: {res.headers.get('GNCP-GW-Trace-ID', '-')}\n{text}")


def call(method, path, token, **kwargs):
    res = requests.request(method, f"{BASE}{path}",
                           headers={"Authorization": f"Bearer {token}"}, timeout=30, **kwargs)
    if res.status_code >= 400:
        explain(res)
    return res.json() if res.content else {}


# ---------- 카테고리 ----------

def categories(token, find=None):
    path = CONFIG / "codes" / "categories.json"
    if not path.exists():
        data = call("GET", "/v1/categories", token)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    data = json.loads(path.read_text(encoding="utf-8"))
    if find:
        for c in data:
            if find in c.get("wholeCategoryName", "") and c.get("last"):
                print(c["id"], c["wholeCategoryName"])
    else:
        print(f"카테고리 {len(data)}개 저장: {path}")


# ---------- 등록 요청 생성 ----------

def upload_images(token, pdir, files):
    """로컬 이미지들을 네이버에 올리고 {로컬경로: URL} 반환. 결과는 product.json에 캐시."""
    data = load_product(pdir)
    cache = data.setdefault("naver", {}).setdefault("image_urls", {})
    todo = [f for f in dict.fromkeys(files) if f not in cache]
    for i in range(0, len(todo), 10):
        batch = todo[i:i + 10]
        handles = [("imageFiles", (Path(f).name, open(pdir / f, "rb"), "image/jpeg")) for f in batch]
        try:
            res = call("POST", "/v1/product-images/upload", token, files=handles)
        finally:
            for _, (_, fh, _) in handles:
                fh.close()
        for f, img in zip(batch, res["images"]):
            cache[f] = img["url"]
    save_product(pdir, data)
    return cache


def build_payload(pdir, data, urls=None):
    cfg = store_config()
    urls = urls or {}
    images = data["images"]
    detail = (pdir / data["detail"]["file"]).read_text(encoding="utf-8")
    detail = IMG_SRC.sub(lambda m: m.group(1) + urls.get(m.group(2), m.group(2)) + m.group(3), detail)
    d, notice = cfg["delivery"], cfg["notice"]

    origin = {
        "statusType": "SALE",
        "saleType": cfg["product"]["sale_type"],
        "leafCategoryId": data["category"]["code"],
        "name": data["name"]["value"],
        "detailContent": detail,
        "images": {
            "representativeImage": {"url": urls.get(images["representative"]["file"], images["representative"]["file"])},
            "optionalImages": [{"url": urls.get(o["file"], o["file"])} for o in images["optional"]],
        },
        "salePrice": data["price"]["list"],
        "stockQuantity": cfg["product"]["stock_quantity"],
        "deliveryInfo": {
            "deliveryType": "DELIVERY",
            "deliveryAttributeType": "NORMAL",
            "deliveryCompany": d["company"],
            "deliveryFee": {
                "deliveryFeeType": d["fee_type"],
                "baseFee": d["base_fee"],
                "freeConditionalAmount": d["free_conditional_amount"],
            },
            "claimDeliveryInfo": {
                "returnDeliveryFee": d["return_fee"],
                "exchangeDeliveryFee": d["exchange_fee"],
                "shippingAddressId": d["shipping_address_id"],
                "returnAddressId": d["return_address_id"],
            },
        },
        "detailAttribute": {
            "naverShoppingSearchInfo": {
                "brandName": cfg["product"]["brand"],
                "manufacturerName": cfg["product"]["manufacturer"],
            },
            "afterServiceInfo": {
                "afterServiceTelephoneNumber": cfg["after_service"]["phone"],
                "afterServiceGuideContent": cfg["after_service"]["guide"],
            },
            "originAreaInfo": {
                "originAreaCode": cfg["origin"]["area_code"],
                "content": cfg["origin"]["content"],
            },
            "minorPurchasable": cfg["product"]["minor_purchasable"],
            "taxType": cfg["product"]["tax_type"],
            "productInfoProvidedNotice": {
                "productInfoProvidedNoticeType": notice["type"],
                "etc": {
                    "itemName": data["notice"]["item_name"],
                    "modelName": data["notice"]["model_name"],
                    "manufacturer": notice["manufacturer"],
                    "customerServicePhoneNumber": notice["customer_service_phone"],
                },
            },
            "seoInfo": {
                "pageTitle": data["seo"]["page_title"],
                "metaDescription": data["seo"]["meta_description"],
                "sellerTags": [{"text": t} for t in data["tags"]],
            },
        },
        "customerBenefit": {
            "immediateDiscountPolicy": {
                "discountMethod": {"value": round(data["price"]["discount_rate"] * 100), "unitType": "PERCENT"},
            },
        },
    }
    channel = {"naverShoppingRegistration": True, "channelProductDisplayStatusType": "SUSPENSION"}
    return {"originProduct": origin, "smartstoreChannelProduct": channel}


def local_images(pdir, data):
    detail = (pdir / data["detail"]["file"]).read_text(encoding="utf-8")
    files = [data["images"]["representative"]["file"], *[o["file"] for o in data["images"]["optional"]]]
    files += [m[1] for m in IMG_SRC.findall(detail) if not m[1].startswith("http")]
    return files


# ---------- 명령 ----------

def require_ready(data, stage):
    if data.get("checks", {}).get("errors", 1):
        sys.exit("검증 오류가 남아 있음. validate.py 결과를 먼저 해결해야 함.")
    if data.get("status", {}).get("stage") != stage:
        sys.exit(f"현재 단계가 '{stage}'가 아님: {data.get('status', {}).get('stage')}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["token", "categories", "payload", "register", "verify", "publish"])
    ap.add_argument("product", nargs="?")
    ap.add_argument("--find")
    args = ap.parse_args()

    if args.command == "token":
        get_token()
        print("인증 성공")
        return
    if args.command == "categories":
        categories(get_token(), args.find)
        return

    pdir = product_dir(args.product)
    data = load_product(pdir)

    if args.command == "payload":
        out = pdir / "naver_payload.json"
        out.write_text(json.dumps(build_payload(pdir, data), ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"등록 요청 내용 생성 (전송 안 함): {out}")

    elif args.command == "register":
        require_ready(data, "approved")
        token = get_token()
        urls = upload_images(token, pdir, local_images(pdir, data))
        data = load_product(pdir)
        payload = build_payload(pdir, data, urls)
        res = call("POST", "/v2/products", token, json=payload)
        data["naver"].update({"origin_product_no": res.get("originProductNo"),
                              "channel_product_no": res.get("smartstoreChannelProductNo")})
        data["status"]["stage"] = "private"
        save_product(pdir, data)
        print(f"비공개 등록 완료. 상품번호 {res.get('originProductNo')}")

    elif args.command == "verify":
        token = get_token()
        no = data["naver"]["origin_product_no"]
        remote = call("GET", f"/v2/products/origin-products/{no}", token)["originProduct"]
        diffs = []
        if remote.get("name") != data["name"]["value"]:
            diffs.append(f"상품명: {remote.get('name')}")
        if remote.get("salePrice") != data["price"]["list"]:
            diffs.append(f"판매가: {remote.get('salePrice')}")
        if str(remote.get("leafCategoryId")) != str(data["category"]["code"]):
            diffs.append(f"카테고리: {remote.get('leafCategoryId')}")
        tags = [t.get("text") for t in remote.get("detailAttribute", {}).get("seoInfo", {}).get("sellerTags", [])]
        if sorted(tags) != sorted(data["tags"]):
            diffs.append(f"태그: {tags}")
        print("등록 내용 일치" if not diffs else "불일치 항목:\n- " + "\n- ".join(diffs))

    elif args.command == "publish":
        require_ready(data, "private")
        token = get_token()
        no = data["naver"]["origin_product_no"]
        current = call("GET", f"/v2/products/origin-products/{no}", token)
        current["smartstoreChannelProduct"]["channelProductDisplayStatusType"] = "ON"
        call("PUT", f"/v2/products/origin-products/{no}", token, json=current)
        data["status"]["stage"] = "public"
        save_product(pdir, data)
        print("판매 공개 완료")


if __name__ == "__main__":
    main()

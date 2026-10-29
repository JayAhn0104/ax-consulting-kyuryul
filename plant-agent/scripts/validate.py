"""product.json을 네이버 등록 규칙으로 검사하고 결과를 product.json의 checks에 기록한다.

결과 등급: pass / warning(확인 후 판단) / error(등록 불가)
종료 코드: error가 있으면 1

사용: uv run scripts/validate.py <상품폴더>
"""

import re
import sys
from datetime import datetime

from lib import load_product, naming_rules, product_dir, save_product, store_config

MAX_TAGS = 10
MAX_OPTIONAL_IMAGES = 9
BLOCKED_HTML = re.compile(r"<\s*(script|iframe|style|form|object|embed)\b|\son\w+\s*=", re.I)
EXTERNAL_LINK = re.compile(r"<a\s[^>]*href\s*=\s*[\"']https?://", re.I)
IMG_SRC = re.compile(r"<img\s[^>]*src\s*=\s*[\"']([^\"']+)[\"']", re.I)


class Checks:
    def __init__(self):
        self.items = []

    def add(self, section, rule, result, detail=""):
        self.items.append({"section": section, "rule": rule, "result": result, "detail": detail})

    def count(self, result):
        return sum(1 for i in self.items if i["result"] == result)


def check_name(c, name):
    rules = naming_rules()
    if not name:
        c.add("상품명", "필수 입력", "error", "상품명 없음")
        return
    length = len(name)
    if length > rules["max_length"]:
        c.add("상품명", "최대 글자수", "error", f"{length}자 / 최대 {rules['max_length']}자")
    elif length > rules["recommended_max_length"]:
        c.add("상품명", "권장 글자수", "warning", f"{length}자 / 권장 {rules['recommended_max_length']}자 이내")
    else:
        c.add("상품명", "글자수", "pass", f"{length}자")

    bad = [ch for ch in rules["forbidden_chars"] if ch in name]
    c.add("상품명", "금지 문자", "error" if bad else "pass", " ".join(bad))

    for rule in rules["rules"]:
        hits = [w for w in rule["words"] if w.lower() in name.lower()]
        c.add("상품명", rule["description"], rule["severity"] if hits else "pass", ", ".join(hits))

    tokens = [t.lower() for t in name.split()]
    repeated = sorted({t for t in tokens if tokens.count(t) > rules["repeat"]["max_occurrences"]})
    c.add("상품명", rules["repeat"]["description"], rules["repeat"]["severity"] if repeated else "pass",
          ", ".join(repeated))


def check_category(c, cat):
    if not cat.get("path"):
        c.add("카테고리", "카테고리 선택", "error", "카테고리 미정")
    else:
        c.add("카테고리", "카테고리 선택", "pass", cat["path"])
    if not cat.get("code"):
        c.add("카테고리", "카테고리 코드", "error", "코드 없음 (API 등록 전 필요)")


def check_price(c, price):
    if not price:
        c.add("판매가", "판매가 계산", "error", "price.py 미실행")
        return
    lp = price["list"]
    ok = 10 <= lp <= 999_999_990 and lp % 10 == 0
    c.add("판매가", "판매가 범위·단위", "pass" if ok else "error", f"{lp:,}원")
    rate = price["discount_rate"]
    c.add("판매가", "할인율 범위 (1~99%)", "pass" if 0 < rate < 1 else "error", f"{rate:.0%}")
    if price.get("provisional"):
        c.add("판매가", "가격 규칙", "warning", "임시 가격 규칙으로 계산된 정가. 확인 필요")


def check_images(c, images, pdir):
    rep = (images or {}).get("representative")
    c.add("상품이미지", "대표이미지", "pass" if rep and (pdir / rep["file"]).exists() else "error",
          rep["source"] if rep else "없음")
    optional = (images or {}).get("optional", [])
    c.add("상품이미지", "추가이미지 개수", "pass" if len(optional) <= MAX_OPTIONAL_IMAGES else "error",
          f"{len(optional)}장 / 최대 {MAX_OPTIONAL_IMAGES}장")
    for note in (images or {}).get("notes", []):
        c.add("상품이미지", "이미지 규격", "warning", note)


def check_detail(c, detail, pdir):
    path = pdir / (detail or {}).get("file", "detail.html")
    if not path.exists():
        c.add("상세설명", "필수 입력", "error", "detail.html 없음")
        return
    html = path.read_text(encoding="utf-8")
    c.add("상세설명", "필수 입력", "pass" if html.strip() else "error", f"{len(html):,}자")
    c.add("상세설명", "허용되지 않는 HTML", "error" if BLOCKED_HTML.search(html) else "pass",
          "script·iframe·style·이벤트 속성은 네이버에서 제거됨")
    c.add("상세설명", "외부 링크", "warning" if EXTERNAL_LINK.search(html) else "pass",
          "네이버 외부 연결 링크는 사용 제한")
    missing = [s for s in IMG_SRC.findall(html) if not s.startswith("http") and not (pdir / s).exists()]
    c.add("상세설명", "이미지 파일", "error" if missing else "pass", ", ".join(missing))


def check_tags(c, tags):
    rules = naming_rules()
    if not tags:
        c.add("검색설정", "태그", "warning", "태그 없음")
        return
    c.add("검색설정", "태그 개수", "pass" if len(tags) <= MAX_TAGS else "error", f"{len(tags)}개 / 최대 {MAX_TAGS}개")
    dup = sorted({t for t in tags if tags.count(t) > 1})
    c.add("검색설정", "태그 중복", "error" if dup else "pass", ", ".join(dup))
    bad = [t for t in tags if any(ch in t for ch in rules["forbidden_chars"]) or " " in t]
    c.add("검색설정", "태그 형식 (공백·특수문자)", "error" if bad else "pass", ", ".join(bad))


def check_store_config(c):
    """API 등록 전에 채워야 할 스토어 설정값 누락 여부."""
    cfg = store_config()
    required = {
        "원산지 코드": cfg["origin"]["area_code"],
        "A/S 전화번호": cfg["after_service"]["phone"],
        "A/S 안내": cfg["after_service"]["guide"],
        "배송비 유형": cfg["delivery"]["fee_type"],
        "출고지 주소록 ID": cfg["delivery"]["shipping_address_id"],
        "반품지 주소록 ID": cfg["delivery"]["return_address_id"],
    }
    missing = [k for k, v in required.items() if not v]
    c.add("스토어 설정", "API 등록용 설정값", "warning" if missing else "pass",
          ("미입력: " + ", ".join(missing)) if missing else "")


def main():
    pdir = product_dir(sys.argv[1])
    data = load_product(pdir)
    c = Checks()
    check_category(c, data.get("category", {}))
    check_name(c, data.get("name", {}).get("value", ""))
    check_price(c, data.get("price"))
    check_images(c, data.get("images"), pdir)
    check_detail(c, data.get("detail"), pdir)
    check_tags(c, data.get("tags", []))
    check_store_config(c)

    data["checks"] = {
        "checked_at": datetime.now().isoformat(timespec="seconds"),
        "errors": c.count("error"),
        "warnings": c.count("warning"),
        "items": c.items,
    }
    save_product(pdir, data)

    print(f"오류 {c.count('error')}건 · 확인 필요 {c.count('warning')}건 · 통과 {c.count('pass')}건")
    for item in c.items:
        if item["result"] != "pass":
            label = "오류" if item["result"] == "error" else "확인"
            print(f"[{label}] {item['section']} / {item['rule']}: {item['detail']}")
    sys.exit(1 if c.count("error") else 0)


if __name__ == "__main__":
    main()

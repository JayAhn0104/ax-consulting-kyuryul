"""product.json을 네이버 등록 규칙으로 검사하고 결과를 product.json의 checks에 기록한다.

결과 등급: pass / warning(확인 후 판단) / error(등록 불가)
종료 코드: error가 있으면 1

사용: uv run scripts/validate.py <상품폴더>
"""

import re
import sys
from datetime import datetime

from lib import load_product, load_toml, naming_rules, product_dir, save_product, store_config

MAX_TAGS = 10
MAX_OPTIONAL_IMAGES = 9
BLOCKED_HTML = re.compile(r"<\s*(script|iframe|style|form|object|embed)\b|\son\w+\s*=", re.I)
EXTERNAL_LINK = re.compile(r"<a\s[^>]*href\s*=\s*[\"']https?://", re.I)
IMG_SRC = re.compile(r"<img\s[^>]*src\s*=\s*[\"']([^\"']+)[\"']", re.I)


# 섹션별 검사 항목 → (짧은 이름, 확인 내용). 미리보기 '규칙 검사'와 작성 기준 페이지 '자동 검사'에 표시
LENGTH = ("글자수", "상품명이 100자 이하인가? (권장 50자 이내)")
QUESTIONS = {
    "카테고리": {
        "카테고리 선택": ("카테고리", "카테고리가 선택되었나?"),
        "카테고리 코드": ("카테고리 코드", "네이버 등록에 필요한 카테고리 코드가 있나?"),
    },
    "상품명": {
        "필수 입력": ("필수 입력", "내용이 입력되었나?"),
        "글자수": LENGTH, "최대 글자수": LENGTH, "권장 글자수": LENGTH,
        "금지 문자": ("금지 문자", "네이버가 허용하지 않는 특수문자( \\ * ? \" < > )가 없나?"),
        "혜택·홍보 문구 기재 금지": ("홍보 문구", "'무료배송·할인·특가' 같은 홍보 문구가 없나?"),
        "주관적 수식어 지양": ("과장 표현", "'추천·인기·베스트' 같은 과장 표현이 없나?"),
        "쇼핑몰명 기재 금지": ("스토어 이름", "스토어 이름이 들어가 있지 않나?"),
        "'1+1' 등 묶음 표기의 혜택 문구 해당 여부 확인 필요": ("묶음 표기", "'1+1' 같은 묶음 표기가 없나? (혜택 문구로 볼 수 있음)"),
        "동일 단어 반복 금지": ("단어 반복", "같은 단어를 두 번 이상 쓰지 않았나?"),
    },
    "판매가": {
        "판매가 계산": ("판매가", "판매가가 계산되었나?"),
        "판매가 범위·단위": ("가격 단위", "정가가 10원 단위이고 네이버 허용 범위 안인가?"),
        "할인율 범위 (1~99%)": ("할인율", "할인율이 1~99% 사이인가?"),
        "가격 규칙": ("가격 확정", "정가가 확정된 가격인가? (임시 규칙이면 확인 필요)"),
    },
    "상품이미지": {
        "대표이미지": ("대표이미지", "대표이미지가 있나?"),
        "추가이미지 개수": ("추가이미지", "추가이미지가 9장 이하인가?"),
        "이미지 규격": ("이미지 규격", "사진 크기·비율이 등록 규격에 맞나?"),
    },
    "상세설명": {
        "필수 입력": ("필수 입력", "내용이 입력되었나?"),
        "허용되지 않는 HTML": ("금지 코드", "네이버가 자동으로 지우는 코드(스크립트 등)가 없나?"),
        "외부 링크": ("외부 링크", "네이버 밖으로 연결되는 링크가 없나?"),
        "이미지 파일": ("사진 파일", "상세설명에 넣은 사진 파일이 모두 있나?"),
    },
    "입력 정보": {
        "상품 규격": ("상품 규격", "상세페이지에 쓸 높이·화분 지름 정보가 있나?"),
    },
    "검색설정": {
        "태그": ("태그", "태그가 입력되었나?"),
        "태그 개수": ("태그 개수", "태그가 10개 이하인가?"),
        "태그 중복": ("태그 중복", "같은 태그가 중복되지 않았나?"),
        "태그 형식 (공백·특수문자)": ("태그 형식", "태그에 띄어쓰기·특수문자가 없나?"),
        "네이버 등록 불가 태그": ("등록 불가 태그", "네이버가 등록을 거절한 적 있는 태그가 없나?"),
    },
    "스토어 설정": {
        "API 등록용 설정값": ("스토어 설정", "네이버 등록에 필요한 스토어 설정(주소·A/S 등)이 모두 있나?"),
    },
}
# 통과했는데 내용이 비어 있을 때 표시할 값
PASS_DETAIL = {"이미지 파일": "모두 있음", "API 등록용 설정값": "모두 있음", "상품 규격": "모두 있음"}


class Checks:
    def __init__(self):
        self.items = []

    def add(self, section, rule, result, detail="", decision=False):
        """decision=True: 클라이언트가 결정·확인해야 하는 항목 (미리보기 상단에 모아 표시)."""
        if result == "pass" and not detail:
            detail = PASS_DETAIL.get(rule, "없음")
        label, question = QUESTIONS.get(section, {}).get(rule, (rule, rule))
        self.items.append({"section": section, "rule": rule, "label": label, "question": question,
                           "result": result, "detail": detail, "decision": decision and result != "pass"})

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
    c.add("카테고리", "카테고리 코드", "pass" if cat.get("code") else "error",
          cat.get("code") or "코드 없음 (네이버 등록 전 필요)")


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
        c.add("판매가", "가격 규칙", "warning", f"정가 {price['list']:,}원은 임시 가격 규칙으로 계산한 값입니다. 이 가격으로 등록할지 정해 주세요.", decision=True)


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
          "script·iframe·style 등이 있어 네이버에서 제거됨" if BLOCKED_HTML.search(html) else "")
    c.add("상세설명", "외부 링크", "warning" if EXTERNAL_LINK.search(html) else "pass",
          "외부 링크가 있음 (네이버에서 사용 제한)" if EXTERNAL_LINK.search(html) else "")
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
    blocked = [t for t in tags if t in rules.get("tags", {}).get("forbidden", [])]
    c.add("검색설정", "네이버 등록 불가 태그", "error" if blocked else "pass", ", ".join(blocked))


def check_input(c, inp):
    """상세페이지 '상품 정보'에 쓰이는 입력값 누락 여부."""
    labels = {"height": "높이", "pot_diameter": "화분 지름"}
    missing = [label for key, label in labels.items() if not inp.get(key)]
    c.add("입력 정보", "상품 규격", "warning" if missing else "pass",
          (", ".join(missing) + " 정보가 없어 상세페이지에서 빠졌습니다. 알려 주시면 추가합니다.") if missing else "", decision=True)


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
          ("미입력: " + ", ".join(missing) + " (컨설턴트 설정 필요)") if missing else "")


def main():
    pdir = product_dir(sys.argv[1])
    data = load_product(pdir)
    c = Checks()
    info = pdir / "input" / "info.toml"
    check_input(c, {**data.get("input", {}), **(load_toml(info) if info.exists() else {})})
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

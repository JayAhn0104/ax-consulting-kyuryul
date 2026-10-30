"""지금까지 작업한 상품의 카테고리 판단 기록을 모아 보여준다.

새 상품의 카테고리를 정할 때 비슷한 식물의 과거 판단을 참고하기 위함.
products/*/product.json에서 상품명·카테고리·근거·단계를 읽음.

사용: uv run scripts/category_history.py
"""

import json

from lib import ROOT


def main():
    rows = []
    for path in sorted((ROOT / "products").glob("*/product.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        cat = data.get("category", {})
        if not cat.get("path"):
            continue
        rows.append({
            "product": data.get("input", {}).get("name") or path.parent.name,
            "category": cat["path"],
            "code": cat.get("code"),
            "basis": cat.get("basis", ""),
            "stage": data.get("status", {}).get("stage", "draft"),
        })
    print(json.dumps(rows, ensure_ascii=False, indent=2) if rows else "카테고리 기록 없음")


if __name__ == "__main__":
    main()

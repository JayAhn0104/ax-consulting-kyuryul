"""product.json으로 클라이언트 검토용 미리보기(preview.html)를 만든다.

섹션 순서는 스마트스토어 등록 화면 순서를 따름.

사용: uv run scripts/render_preview.py <상품폴더> [--open]
"""

import argparse
import webbrowser
from html import escape

from lib import load_product, product_dir, store_config

RESULT_LABEL = {"pass": "통과", "warning": "확인 필요", "error": "오류"}

CSS = """
:root { --ink:#1F2328; --sub:#6B7280; --line:#E5E7EB; --bg:#F7F8FA; --card:#fff;
        --ok:#2F7D4F; --warn:#B45309; --err:#C2410C; --acc:#3B5BDB; }
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--ink);
       font-family:"Apple SD Gothic Neo","Pretendard","Noto Sans KR","Malgun Gothic",sans-serif; font-size:14px; line-height:1.6; }
.wrap { max-width:960px; margin:0 auto; padding:28px 16px 60px; }
h1 { font-size:22px; margin:0 0 4px; }
.meta { color:var(--sub); font-size:13px; }
.summary { display:flex; gap:10px; margin:16px 0 24px; flex-wrap:wrap; }
.badge { padding:6px 12px; border-radius:999px; font-weight:700; font-size:13px; background:#fff; border:1px solid var(--line); }
.badge.err { color:var(--err); border-color:#FDBA74; } .badge.warn { color:var(--warn); border-color:#FCD34D; }
.badge.ok { color:var(--ok); border-color:#86EFAC; }
section { background:var(--card); border:1px solid var(--line); border-radius:12px; padding:18px 20px; margin-bottom:14px; }
section > h2 { font-size:15px; margin:0 0 12px; display:flex; align-items:center; gap:8px; }
section > h2 .no { color:var(--sub); font-weight:600; font-size:13px; }
.value { font-size:17px; font-weight:700; }
.basis { color:var(--sub); font-size:13px; margin-top:6px; }
table { border-collapse:collapse; width:100%; font-size:13px; }
td, th { border-bottom:1px solid var(--line); padding:6px 8px; text-align:left; vertical-align:top; }
th { color:var(--sub); font-weight:600; width:160px; }
.r-pass { color:var(--ok); } .r-warning { color:var(--warn); font-weight:700; } .r-error { color:var(--err); font-weight:700; }
.imgs { display:flex; gap:10px; flex-wrap:wrap; }
.imgs figure { margin:0; width:150px; } .imgs img { width:150px; height:150px; object-fit:cover; border-radius:8px; border:1px solid var(--line); }
.imgs figcaption { font-size:12px; color:var(--sub); }
.imgs figure.rep img { width:220px; height:220px; } .imgs figure.rep { width:220px; }
.tags { display:flex; gap:6px; flex-wrap:wrap; }
.tag { background:#EEF2FF; color:var(--acc); padding:4px 10px; border-radius:999px; font-size:13px; }
.detail { width:780px; max-width:100%; margin:0 auto; border:1px dashed var(--line); }
.detail img { max-width:100%; }
.missing { color:var(--err); }
button.copy { margin-left:8px; font-size:12px; padding:2px 8px; border:1px solid var(--line); background:#fff; border-radius:6px; cursor:pointer; }
"""

JS = """
document.querySelectorAll('button.copy').forEach(b => b.addEventListener('click', () => {
  navigator.clipboard.writeText(b.dataset.text).then(() => { b.textContent = '복사됨'; setTimeout(() => b.textContent = '복사', 1200); });
}));
"""


def e(value):
    return escape(str(value)) if value not in (None, "") else '<span class="missing">미입력</span>'


def copy_btn(text):
    return f'<button class="copy" data-text="{escape(text, quote=True)}">복사</button>' if text else ""


def checks_for(data, section):
    rows = [i for i in data.get("checks", {}).get("items", []) if i["section"] == section]
    if not rows:
        return ""
    body = "".join(
        f'<tr><td>{escape(i["rule"])}</td><td class="r-{i["result"]}">{RESULT_LABEL[i["result"]]}</td>'
        f'<td>{escape(i["detail"])}</td></tr>' for i in rows)
    return f'<table style="margin-top:10px">{body}</table>'


def section(no, title, body):
    return f'<section><h2><span class="no">{no}</span>{escape(title)}</h2>{body}</section>'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("product")
    ap.add_argument("--open", action="store_true", help="생성 후 브라우저로 열기")
    args = ap.parse_args()

    pdir = product_dir(args.product)
    data = load_product(pdir)
    cfg = store_config()
    checks = data.get("checks", {})
    parts = []

    cat = data.get("category", {})
    search_rows = "".join(f"<tr><td>{escape(c['path'])}</td><td>{c['count']}</td></tr>"
                          for c in cat.get("search", {}).get("categories", []))
    parts.append(section("1", "카테고리",
        f'<div class="value">{e(cat.get("path"))}{copy_btn(cat.get("path"))}</div>'
        f'<div class="basis">코드: {e(cat.get("code"))}</div>'
        f'<div class="basis">근거: {e(cat.get("basis"))}</div>'
        + (f'<table style="margin-top:10px"><tr><th>검색 상위 카테고리</th><th>상품 수</th></tr>{search_rows}</table>' if search_rows else "")
        + checks_for(data, "카테고리")))

    name = data.get("name", {})
    parts.append(section("2", "상품명",
        f'<div class="value">{e(name.get("value"))}{copy_btn(name.get("value"))}</div>'
        f'<div class="basis">근거: {e(name.get("basis"))}</div>' + checks_for(data, "상품명")))

    price = data.get("price") or {}
    if price:
        markup = f'{price["markup"]}배' if price.get("markup") else "-"
        cost = f'{price["cost"]:,}원' if price.get("cost") else None
        price_body = (
            f'<table><tr><th>정가 (판매가 입력값)</th><td>{price["list"]:,}원{copy_btn(str(price["list"]))}</td></tr>'
            f'<tr><th>기본할인</th><td>{price["discount_rate"]:.0%} ({price["discount"]:,}원)'
            f'{copy_btn(str(round(price["discount_rate"] * 100)))}</td></tr>'
            f'<tr><th>실판매가</th><td><b>{price["sale"]:,}원</b></td></tr>'
            f'<tr><th>매입가</th><td>{e(cost)}</td></tr>'
            f'<tr><th>판매가 / 매입가</th><td>{markup}</td></tr></table>'
            f'<div class="basis">근거: {e(price.get("basis"))}</div>')
    else:
        price_body = '<span class="missing">미계산</span>'
    parts.append(section("3", "판매가", price_body + checks_for(data, "판매가")))

    images = data.get("images") or {}
    figs = []
    if images.get("representative"):
        r = images["representative"]
        figs.append(f'<figure class="rep"><img src="{escape(r["file"])}"><figcaption>대표 · {escape(r["source"])}</figcaption></figure>')
    for o in images.get("optional", []):
        figs.append(f'<figure><img src="{escape(o["file"])}"><figcaption>추가 · {escape(o["source"])}</figcaption></figure>')
    img_basis = f'<div class="basis">근거: {escape(images["basis"])}</div>' if images.get("basis") else ""
    parts.append(section("6", "상품이미지", f'<div class="imgs">{"".join(figs) or e(None)}</div>' + img_basis + checks_for(data, "상품이미지")))

    detail_file = pdir / (data.get("detail") or {}).get("file", "detail.html")
    detail_html = detail_file.read_text(encoding="utf-8") if detail_file.exists() else e(None)
    detail_imgs = (data.get("detail") or {}).get("images", [])
    links = " · ".join(f'<a href="{escape(f)}" target="_blank">{escape(f.split("/")[-1])}</a>' for f in detail_imgs)
    detail_note = (f'<div class="basis" style="margin-bottom:10px">판매자센터 업로드용 상세 이미지: {links}</div>'
                   if links else '<div class="basis" style="margin-bottom:10px">상세 이미지 미생성 (export_detail.py)</div>')
    parts.append(section("7", "상세설명", detail_note + f'<div class="detail">{detail_html}</div>' + checks_for(data, "상세설명")))

    notice = data.get("notice", {})
    attrs = ", ".join(f'{a["name"]}: {a["value"]}' for a in data.get("attributes", []))
    parts.append(section("8·9", "상품주요정보 · 상품정보제공고시", (
        f'<table><tr><th>원산지</th><td>{e(cfg["origin"]["content"])}</td></tr>'
        f'<tr><th>브랜드 / 제조사</th><td>{e(cfg["product"]["brand"])} / {e(cfg["product"]["manufacturer"])}</td></tr>'
        f'<tr><th>상품상태</th><td>신상품</td></tr>'
        f'<tr><th>미성년자 구매</th><td>{"가능" if cfg["product"]["minor_purchasable"] else "불가"}</td></tr>'
        f'<tr><th>부가세</th><td>{"과세" if cfg["product"]["tax_type"] == "TAX" else "면세"}</td></tr>'
        f'<tr><th>고시 품명 / 모델명</th><td>{e(notice.get("item_name"))}{copy_btn(notice.get("item_name"))}'
        f' / {e(notice.get("model_name"))}{copy_btn(notice.get("model_name"))}</td></tr>'
        f'<tr><th>상품속성</th><td>{e(attrs)}</td></tr></table>'
        '<div class="basis">원산지·브랜드·부가세는 스토어 설정값(config/store.toml) 적용</div>')))

    d, a = cfg["delivery"], cfg["after_service"]
    parts.append(section("10~12", "배송 · 반품/교환 · A/S", (
        f'<table><tr><th>택배사</th><td>{e(d["company"])}</td></tr>'
        f'<tr><th>배송비</th><td>{e(d["fee_type"])} · 기본 {d["base_fee"]:,}원</td></tr>'
        f'<tr><th>반품 / 교환 배송비</th><td>{d["return_fee"]:,}원 / {d["exchange_fee"]:,}원</td></tr>'
        f'<tr><th>A/S 전화번호</th><td>{e(a["phone"])}</td></tr></table>'
        '<div class="basis">스토어 설정값 적용</div>' + checks_for(data, "스토어 설정"))))

    tags = data.get("tags", [])
    seo = data.get("seo", {})
    parts.append(section("15", "검색설정", (
        f'<div class="tags">{"".join(f"<span class=tag>{escape(t)}</span>" for t in tags) or e(None)}</div>'
        f'{copy_btn(",".join(tags))}'
        f'<table style="margin-top:12px"><tr><th>Page Title</th><td>{e(seo.get("page_title"))}{copy_btn(seo.get("page_title"))}</td></tr>'
        f'<tr><th>Meta description</th><td>{e(seo.get("meta_description"))}{copy_btn(seo.get("meta_description"))}</td></tr></table>'
        + checks_for(data, "검색설정"))))

    errors, warnings = checks.get("errors"), checks.get("warnings")
    summary = (
        f'<span class="badge {"err" if errors else "ok"}">오류 {errors}건</span>'
        f'<span class="badge {"warn" if warnings else "ok"}">확인 필요 {warnings}건</span>'
        if checks else '<span class="badge warn">검증 미실행</span>')
    title = name.get("value") or data.get("input", {}).get("name", "상품")
    stage = {"draft": "작성 중", "approved": "등록 승인됨", "private": "비공개 등록됨", "public": "판매 중"}
    html = (
        f'<!doctype html><html lang="ko"><head><meta charset="utf-8">'
        f'<meta name="viewport" content="width=device-width, initial-scale=1"><title>미리보기 · {escape(title)}</title>'
        f'<style>{CSS}</style></head><body><div class="wrap">'
        f'<h1>{escape(title)}</h1>'
        f'<div class="meta">상태: {stage.get(data.get("status", {}).get("stage", "draft"), "작성 중")}'
        f' · 검증 시각: {escape(checks.get("checked_at", "-"))}</div>'
        f'<div class="summary">{summary}</div>{"".join(parts)}</div><script>{JS}</script></body></html>')
    out = pdir / "preview.html"
    out.write_text(html, encoding="utf-8")
    print(f"미리보기 생성: {out}")
    if args.open:
        webbrowser.open(out.as_uri())


if __name__ == "__main__":
    main()

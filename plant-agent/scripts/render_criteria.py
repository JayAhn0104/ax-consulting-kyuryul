"""작성기준.md로 작성 기준 페이지(작성기준.html)를 만든다.

사용자가 AI의 현재 작성 기준을 확인하고, 바꾸고 싶은 부분을 채팅으로 요청할 수 있게 하기 위함.
화면은 미리보기와 같은 판매자센터 형식. 섹션 번호가 미리보기와 같아 미리보기에서 바로 이동 가능.
- 작성 기준: 작성기준.md의 섹션별 '### 항목'을 판매자센터처럼 '항목 | 내용' 줄로 표시.
  {{설정 이름}}은 스토어 설정값, 'A → B → C' 줄은 흐름도, '1.' 목록은 번호 목록으로 표시
- 자동 검사: validate.py가 섹션마다 확인하는 항목
- 금지어 등 참고 목록: naming-rules.toml

사용: uv run scripts/render_criteria.py [--open]
"""

import argparse
import re
import webbrowser
from html import escape

from lib import ROOT, naming_rules, store_config
from prepare_images import MAX_SIDE, MIN_SIDE
from render_preview import (CHECK_TO_TITLE, COMPANY_LABEL, CSS, FEE_LABEL, GEAR, NOTICE_LABEL, ORIGIN_LABEL, STAR,
                            grid, row)
from validate import QUESTIONS

SOURCE = ROOT / "작성기준.md"
OUT = ROOT / "작성기준.html"

KIND_BADGE = {
    "AI 작성": f'<span class="bd bd-ai src">{STAR}AI 작성</span>',
    "기본 설정": f'<span class="bd bd-preset-solid src">{GEAR}기본 설정</span>',
    "자동 작성 미지원": '<span class="bd bd-na src">자동 작성 미지원</span>',
}
MARKS = {
    "`[네이버 규칙]`": '<span class="bd bd-naver">네이버 규칙</span>',
    "`[임시]`": '<span class="bd bd-temp">임시</span>',
}
TEMP = "`[임시]`"


def won(v):
    return f"{v:,}원"


# 설정값 표시 형식. 없으면 숫자는 천 단위 구분, 문자는 그대로
DISPLAY = {
    "price.discount_rate": lambda v: f"{v:.0%}",
    "price.unit": lambda v: f"{v:,}",
    "price.list_price_round": lambda v: f"{v:,}",
    "product.tax_type": lambda v: {"TAX": "과세상품", "DUTYFREE": "면세상품", "SMALL": "영세상품"}.get(v, v),
    "product.sale_type": lambda v: {"NEW": "신상품", "USED": "중고상품"}.get(v, v),
    "product.minor_purchasable": lambda v: "가능" if v else "불가능",
    "origin.area_code": lambda v: ORIGIN_LABEL.get(v, v),
    "notice.type": lambda v: NOTICE_LABEL.get(v, v),
    "delivery.company": lambda v: COMPANY_LABEL.get(v, v),
    "delivery.fee_type": lambda v: FEE_LABEL.get(v, v),
    "delivery.return_fee": won,
    "delivery.exchange_fee": won,
    "delivery.shipping_address_id": lambda v: "설정됨",
    "delivery.return_address_id": lambda v: "설정됨",
}

PAGE_CSS = """
.pagehead .lead { color:var(--sub); }
.legend { display:flex; flex-wrap:wrap; gap:6px 16px; padding:0 4px 14px; color:var(--sub); font-size:12px; }
.legend span.item { display:inline-flex; align-items:center; gap:6px; }
.bd-naver { border:1px solid var(--green); color:var(--green-text); background:#fff; line-height:16px; border-radius:3px; font-size:10.5px; margin-left:4px; }
.bd-temp { border:1px solid var(--orange); color:#c25e00; background:#fff; line-height:16px; border-radius:3px; font-size:10.5px; margin-left:4px; }
.cv { display:inline-block; border:1px solid var(--field); background:#fafafa; padding:0 6px; margin:0 2px; font-weight:700; line-height:20px; }
.cv.empty { color:var(--red); font-weight:400; border-color:#f3b4b4; }
ul.rules, ol.steps { margin:0; padding:0 0 0 18px; }
ul.rules li, ol.steps li { margin:2px 0; }
ol.steps li::marker { color:var(--sub); font-weight:700; }
.temp { color:#8a4a00; }
.one { padding-top:0; }
.flow { display:flex; flex-wrap:wrap; align-items:center; gap:6px; margin:2px 0 6px; }
.flow .step { border:1px solid #cfd3d8; background:#fff; padding:4px 12px; }
.flow .arr { color:#9aa0a6; }
.row.note .field { color:var(--sub); }
details.checks > summary { cursor:pointer; color:var(--sub); list-style:none; }
details.checks > summary::-webkit-details-marker { display:none; }
details.checks > summary::after { content:" ›"; }
details.checks[open] > summary { margin-bottom:8px; }
code { background:#f3f4f6; padding:0 4px; font-size:12px; }
ul.checklist.plain .lb { width:110px; }
.sec-foot .preset .lbl { color:#4b5563; }
.asks { display:flex; flex-wrap:wrap; gap:6px; flex:1; }
.ask { background:#fff; border:1px solid #dcdfe4; border-radius:14px; padding:3px 12px; color:#333; }
.plain-card { background:#fff; border:1px solid var(--line); margin-bottom:10px; padding:20px 34px; }
.plain-card h2 { font-size:15px; margin:0 0 10px; }
@media (max-width: 640px) {
  .plain-card { padding:16px; }
  .sec-foot .preset { align-items:flex-start; flex-direction:column; }
}
"""


def config_values():
    cfg = store_config()
    cfg["naming"] = naming_rules()
    cfg["image"] = {"max_side": MAX_SIDE, "min_side": MIN_SIDE}
    return cfg


def lookup(values, path):
    cur = values
    for key in path.split("."):
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return cur


def inline(text, values):
    """목록 한 줄을 HTML로: 표기 배지, 설정값 칸, `코드`, **굵게**."""
    out = escape(text, quote=False)
    for mark, badge in MARKS.items():
        out = out.replace(mark, badge)

    def value(m):
        path = m.group(1).strip()
        v = lookup(values, path)
        if v in (None, ""):
            return '<span class="cv empty" title="스토어 설정값">미입력</span>'
        shown = DISPLAY[path](v) if path in DISPLAY else (f"{v:,}" if isinstance(v, int) and not isinstance(v, bool) else str(v))
        return f'<span class="cv" title="스토어 설정값">{escape(shown)}</span>'

    out = re.sub(r"\{\{(.+?)\}\}", value, out)
    out = re.sub(r"`(.+?)`", r"<code>\1</code>", out)
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", out)


def parse(text):
    """작성기준.md → 섹션 목록. 섹션: no, title, kind, rows[{label, items[(종류, 내용)]}], asks[]"""
    sections, cur = [], None
    for line in text.splitlines():
        if line.startswith("## "):
            head = line[3:].strip()
            m = re.match(r"([\d-]+)\.\s*(.+?)\s*·\s*(.+)$", head)
            cur = {"no": m[1] if m else None, "title": m[2] if m else head, "kind": m[3] if m else None,
                   "rows": [], "asks": []}
            sections.append(cur)
        elif cur is None:
            continue
        elif line.startswith("### "):
            cur["rows"].append({"label": line[4:].strip(), "items": []})
        elif line.startswith("> "):
            cur["asks"].append(line[2:].strip())
        elif m := re.match(r"(- |\d+\. )(.+)", line):
            if not cur["rows"]:
                cur["rows"].append({"label": None, "items": []})
            cur["rows"][-1]["items"].append(("ol" if m[1][0].isdigit() else "li", m[2].strip()))
    return sections


def items_html(items, values):
    """한 항목의 내용: 흐름도(A → B → C), 번호 목록, 일반 목록. 한 줄뿐이면 목록 기호 없이."""
    def li(text):
        cls = ' class="temp"' if TEMP in text else ""
        return f"<li{cls}>{inline(text, values)}</li>"

    if len(items) == 1 and items[0][0] == "li" and items[0][1].count(" → ") < 2:
        text = items[0][1]
        return f'<div class="one{" temp" if TEMP in text else ""}">{inline(text, values)}</div>'
    html, group, kind = [], [], None
    def flush():
        if group:
            tag = "ol class=\"steps\"" if kind == "ol" else "ul class=\"rules\""
            html.append(f"<{tag}>{''.join(li(t) for t in group)}</{tag.split()[0]}>")
            group.clear()
    for k, text in items:
        if k == "li" and text.count(" → ") >= 2:
            flush()
            steps = '<span class="arr">→</span>'.join(f'<span class="step">{inline(t, values)}</span>' for t in text.split(" → "))
            html.append(f'<div class="flow">{steps}</div>')
            continue
        if k != kind:
            flush()
            kind = k
        group.append(text)
    flush()
    return "".join(html)


def rules_html(rows, values):
    """제목 없는 목록 (공통 원칙, 변경 이력)."""
    return "".join(items_html(r["items"], values) for r in rows)


def checks_html(title):
    """validate.py가 이 섹션에서 확인하는 항목 (짧은 이름 기준 중복 제거)."""
    seen, items = set(), []
    for section, rules in QUESTIONS.items():
        if CHECK_TO_TITLE.get(section, section) != title:
            continue
        for label, question in rules.values():
            if label not in seen:
                seen.add(label)
                items.append(f'<li><span class="lb">{escape(label)}</span><span class="q">{escape(question)}</span></li>')
    return f'<ul class="checklist plain">{"".join(items)}</ul>' if items else ""


def reference(title, values):
    """섹션별 참고 목록 (설정 파일의 목록형 값) → (항목 이름, HTML)."""
    naming = values["naming"]
    if title == "상품명":
        severity = {"error": "등록 불가", "warning": "확인 필요"}
        rows = [[escape(r["description"]), escape(", ".join(r["words"])), severity[r["severity"]]] for r in naming["rules"]]
        rows.append(["금지 문자", escape(" ".join(naming["forbidden_chars"])), "등록 불가"])
        return "금지어 목록", grid(["구분", "단어", "처리"], rows)
    if title == "검색설정":
        tags = naming.get("tags", {}).get("forbidden", [])
        return "등록 불가 태그", '<div class="tags">' + "".join(f'<span class="tag">{escape(t)}</span>' for t in tags) + "</div>"
    return None, ""


def section_html(sec, values):
    texts = [t for r in sec["rows"] for _, t in r["items"]]
    temps = sum(TEMP in t for t in texts)
    unsupported = sec["kind"] == "자동 작성 미지원"
    if unsupported:
        state = '<span class="state">사용 안 함</span>'
    elif temps:
        state = f'<span class="state warn">임시 기준 {temps}</span>'
    else:
        state = '<span class="state"></span>'
    ref_label, ref = reference(sec["title"], values)
    body = ""
    for r in sec["rows"]:
        content = items_html(r["items"], values)
        if r["label"] == ref_label:
            content += f'<div style="margin-top:8px">{ref}</div>'
            ref = ""
        body += row(r["label"] or "작성 기준", content, cls="note" if r["label"] == "참고" else "")
    if ref:
        body += row(ref_label, ref)
    checks = checks_html(sec["title"])
    if checks:
        n = checks.count("<li>")
        body += row("자동 검사", f'<details class="checks"><summary>작성 후 프로그램이 확인하는 항목 {n}개</summary>{checks}</details>')
    foot = ""
    if sec["asks"]:
        asks = "".join(f'<span class="ask">“{escape(a)}”</span>' for a in sec["asks"])
        foot = (f'<div class="sec-foot"><div class="preset"><span class="lbl">이렇게 말하면 바뀝니다</span>'
                f'<span class="asks">{asks}</span></div></div>')
    open_ = "" if unsupported else " open"
    return (f'<details class="sec" id="c-{sec["no"]}"{open_}><summary><h2>{escape(sec["title"])}</h2>'
            f'{KIND_BADGE.get(sec["kind"], "")}{state}<span class="toggle"></span></summary>'
            f'<div class="sec-body">{body}</div>{foot}</details>')


def temp_box(sections, values):
    rows = []
    for sec in sections:
        if not sec["no"]:
            continue
        for r in sec["rows"]:
            for _, text in r["items"]:
                if TEMP not in text:
                    continue
                label = f'<b>{escape(r["label"])}</b> · ' if r["label"] and r["label"] != sec["title"] else ""
                rows.append(f'<div class="todo-row"><span class="bd bd-decide">확정 필요</span><span class="item">{escape(sec["title"])}</span>'
                            f'<span class="desc">{label}{inline(text.replace(TEMP, "").strip(), values)}</span>'
                            f'<a class="btn" href="#c-{sec["no"]}">바로가기</a></div>')
    if not rows:
        return '<div class="todo clear"><div class="todo-head">확정이 필요한 임시 기준이 없습니다</div></div>'
    return (f'<div class="todo"><div class="todo-head">확정이 필요한 임시 기준<em>{len(rows)}건</em></div>'
            + "".join(rows) + "</div>")


def build():
    values = config_values()
    sections = parse(SOURCE.read_text(encoding="utf-8"))
    numbered = [s for s in sections if s["no"]]
    common = next((s for s in sections if s["title"] == "공통 원칙"), None)
    history = next((s for s in sections if s["title"] == "변경 이력"), None)
    updated = ""
    if history and history["rows"] and history["rows"][0]["items"]:
        m = re.match(r"(\d{4}-\d{2}-\d{2})", history["rows"][0]["items"][0][1])
        updated = m[1] if m else ""

    legend = (f'<div class="legend"><span class="item">{KIND_BADGE["AI 작성"]} AI가 상품마다 작성</span>'
              f'<span class="item">{KIND_BADGE["기본 설정"]} 모든 상품에 같은 값</span>'
              f'<span class="item">{KIND_BADGE["자동 작성 미지원"]} 아직 사용하지 않음</span>'
              f'<span class="item">{MARKS["`[네이버 규칙]`"]} 네이버가 정한 규칙 (변경 불가)</span>'
              f'<span class="item">{MARKS[TEMP]} 확정 전 임시 기준</span>'
              '<span class="item"><span class="cv">값</span> 스토어 설정값</span></div>')
    parts = [temp_box(numbered, values)]
    if common:
        parts.append(f'<div class="plain-card"><h2>공통 원칙</h2>{rules_html(common["rows"], values)}</div>')
    parts += [section_html(s, values) for s in numbered]
    if history:
        parts.append(f'<div class="plain-card"><h2>변경 이력</h2>{rules_html(history["rows"], values)}</div>')

    return (
        '<!doctype html><html lang="ko"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1"><title>작성 기준</title>'
        f'<style>{CSS}{PAGE_CSS}</style></head><body>'
        f'<div class="topbar">상품등록<span>작성 기준</span><div class="stage">최종 변경 {escape(updated or "-")}</div></div>'
        '<div class="wrap"><div class="pagehead"><h1>상품 등록 작성 기준</h1>'
        '<span class="lead">AI가 상품 정보를 작성할 때 따르는 기준입니다. 바꾸고 싶은 내용은 채팅으로 말씀해 주세요.</span></div>'
        f'{legend}{"".join(parts)}</div></body></html>')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--open", action="store_true", help="생성 후 브라우저로 열기")
    args = ap.parse_args()
    OUT.write_text(build(), encoding="utf-8")
    print(f"작성 기준 페이지 생성: {OUT}")
    if args.open:
        webbrowser.open(OUT.as_uri())


if __name__ == "__main__":
    main()

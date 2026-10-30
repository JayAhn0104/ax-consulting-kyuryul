"""product.json으로 등록 전 검토용 미리보기(preview.html)를 만든다.

화면은 스마트스토어센터 상품 등록 화면의 섹션 순서·모양을 따름.
- 상단: 등록 전 확인 사항 (오류, 클라이언트 결정 필요 항목)
- 섹션 값 영역: 판매자센터에 들어갈 값만 표시. 사용하지 않는 섹션은 접고 '설정안함'
- 섹션 제목 옆 출처 배지: 'AI 작성' 또는 '기본 설정'
- 섹션 하단 'AI 판단 근거' 띠: 판단 요약 한두 문장. 띠를 누르면 근거 데이터·규칙 검사 결과

시안: docs/01-식물-상품등록/assets/06-미리보기-시안.html
이전 형식(최상위 basis.thumbnail 등)도 읽음.

사용: uv run scripts/render_preview.py <상품폴더> [--open]
"""

import argparse
import os
import webbrowser
from html import escape
from urllib.parse import quote

from lib import ROOT, load_product, product_dir, store_config

RESULT_LABEL = {"pass": "통과", "warning": "확인 필요", "error": "오류"}
STAGE_LABEL = {"draft": "비공개 등록 전", "approved": "등록 승인", "private": "비공개 등록됨", "public": "판매 중"}
FEE_LABEL = {"FREE": "무료", "CONDITIONAL_FREE": "조건부 무료", "PAID": "유료"}
ORIGIN_LABEL = {"00": "국산"}
NOTICE_LABEL = {"ETC": "기타 재화"}
COMPANY_LABEL = {"CJGLS": "CJ대한통운"}
# 검사 항목의 섹션 이름 → 미리보기 섹션 제목
CHECK_TO_TITLE = {"입력 정보": "상세설명", "스토어 설정": "배송", "상품이미지": "상품이미지/동영상"}
GEAR = '<svg viewBox="0 0 16 16"><path d="M8 5.2a2.8 2.8 0 1 0 0 5.6 2.8 2.8 0 0 0 0-5.6zm6.4 3.6-1.5.3a5 5 0 0 1-.5 1.2l.9 1.3-1.4 1.4-1.3-.9a5 5 0 0 1-1.2.5l-.3 1.5H7.1l-.3-1.5a5 5 0 0 1-1.2-.5l-1.3.9-1.4-1.4.9-1.3a5 5 0 0 1-.5-1.2L1.6 8.8V7.2l1.5-.3a5 5 0 0 1 .5-1.2l-.9-1.3 1.4-1.4 1.3.9a5 5 0 0 1 1.2-.5l.3-1.5h1.8l.3 1.5a5 5 0 0 1 1.2.5l1.3-.9 1.4 1.4-.9 1.3a5 5 0 0 1 .5 1.2l1.5.3z"/></svg>'
STAR = '<svg viewBox="0 0 16 16"><path d="M8 0l1.9 6.1L16 8l-6.1 1.9L8 16l-1.9-6.1L0 8l6.1-1.9z"/></svg>'

CSS = """
:root { --ink:#333; --sub:#666; --muted:#999; --line:#e5e5e5; --field:#d5d5d5; --bg:#f1f2f4;
        --green:#03c75a; --green-text:#00b843; --red:#f53b3b; --orange:#ff7a00; --blue:#1a6fd8; --ai:#5b4be0; }
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--ink); font-size:13px; line-height:1.55;
       font-family:"Nanum Gothic","Apple SD Gothic Neo","Malgun Gothic","Noto Sans KR",sans-serif; }
.topbar { background:#2b3036; color:#fff; height:48px; display:flex; align-items:center; padding:0 24px; font-weight:700; font-size:15px; }
.topbar span { color:var(--green); margin-left:4px; }
.topbar .stage { margin-left:auto; font-weight:400; font-size:12px; color:#c9c9c9; }
.wrap { max-width:1100px; margin:0 auto; padding:16px 20px 60px; }
.pagehead { display:flex; align-items:baseline; gap:12px; flex-wrap:wrap; padding:14px 4px 12px; }
.pagehead h1 { font-size:20px; font-weight:400; margin:0; word-break:keep-all; }
.pagehead .req { font-size:12px; color:var(--red); }

.bd { display:inline-block; font-size:11px; line-height:18px; padding:0 6px; white-space:nowrap; vertical-align:middle; }
.bd-decide { background:var(--orange); color:#fff; font-weight:700; }
.bd-fix { background:var(--red); color:#fff; font-weight:700; }
.bd-ai { background:linear-gradient(135deg,#6d5dfc,#3b82f6); color:#fff; font-weight:700; padding:1px 8px 1px 6px; border-radius:3px; }
.bd-ai svg { width:11px; height:11px; vertical-align:-1px; margin-right:3px; fill:#fff; }
summary .bd.src { margin-left:6px; }
.bd-na { border:1px dashed #b8bcc4; color:#8a8f99; background:#fff; line-height:16px; border-radius:3px; }
.bd-pick { background:#6d5dfc; color:#fff; font-weight:700; border-radius:3px; }
.bd-preset-solid { background:#6b7280; color:#fff; font-weight:700; padding:1px 8px 1px 6px; border-radius:3px; }
.bd-preset-solid svg { width:11px; height:11px; vertical-align:-1px; margin-right:3px; fill:#fff; }
.preset { display:flex; align-items:center; gap:10px; padding:10px 14px; background:#f5f6f7; border-radius:3px; }
.preset .lbl { color:#6b7280; font-weight:700; white-space:nowrap; }
.preset .lbl svg { width:11px; height:11px; fill:#6b7280; vertical-align:-1px; margin-right:4px; }
.preset .opinion { flex:1; color:#444; }
a.rule-link { color:var(--sub); font-size:12px; text-decoration:none; white-space:nowrap; }
a.rule-link:hover { color:var(--blue); text-decoration:underline; }
.topbar a { margin-left:16px; color:#c9c9c9; font-weight:400; font-size:12px; text-decoration:none; }

.todo { background:#fff; border:1px solid var(--line); margin-bottom:10px; }
.todo-head { padding:16px 34px; font-size:15px; font-weight:700; border-bottom:1px solid var(--line); }
.todo-head em { font-style:normal; color:var(--orange); margin-left:4px; }
.todo-head em.err { color:var(--red); }
.todo.clear .todo-head { border-bottom:0; color:var(--sub); font-weight:400; }
.todo-row { display:flex; align-items:center; gap:14px; padding:14px 34px; }
.todo-row + .todo-row { border-top:1px solid #f0f0f0; }
.todo-row .item { width:120px; font-weight:700; flex:none; }
.todo-row .desc { flex:1; }
.btn { border:1px solid #cfcfcf; background:#fff; padding:6px 12px; font-size:12px; color:#333; text-decoration:none; white-space:nowrap; }

details.sec { background:#fff; border:1px solid var(--line); margin-bottom:10px; scroll-margin-top:10px; }
details.sec > summary { display:flex; align-items:center; gap:8px; padding:22px 34px; list-style:none; cursor:pointer; }
details.sec > summary::-webkit-details-marker { display:none; }
summary h2 { font-size:15px; font-weight:700; margin:0; }
.dot { display:inline-block; width:5px; height:5px; border-radius:50%; background:var(--red); margin-left:4px; vertical-align:middle; }
summary .state { margin-left:auto; color:var(--sub); text-align:right; }
summary .state.warn { color:var(--orange); font-weight:700; } summary .state.err { color:var(--red); font-weight:700; }
summary .toggle { width:34px; height:34px; border:1px solid #cfcfcf; margin-left:18px; position:relative; flex:none; }
summary .toggle::after { content:""; position:absolute; left:12px; top:10px; width:8px; height:8px;
                         border-right:1.5px solid #555; border-bottom:1.5px solid #555; transform:rotate(45deg); }
details.sec[open] > summary .toggle::after { transform:rotate(-135deg); top:15px; }
details.sec[open] > summary { border-bottom:1px solid var(--line); }
.sec-body { padding:20px 34px 24px; }
.row { display:flex; padding:12px 0; }
.row + .row { border-top:1px solid #f0f0f0; }
.row .label { width:185px; flex:none; padding-top:8px; }
.row .field { flex:1; min-width:0; }
.row .field:not(:has(.box, .seg, .thumbs, .grid, .detail-frame, img, .tags, .inline)) { padding-top:8px; }
.box { display:flex; align-items:stretch; border:1px solid var(--field); background:#fafafa; min-height:36px; }
.box .v { flex:1; padding:7px 12px; display:flex; align-items:center; min-width:0; word-break:break-all; }
.box .unit, .box .count { border-left:1px solid var(--field); padding:0 14px; display:flex; align-items:center; background:#fff; color:var(--sub); white-space:nowrap; }
.box .count b { color:var(--green-text); font-weight:400; }
.box.empty .v { color:var(--muted); }
.w-200 { width:200px; } .w-90 { width:90px; } .w-300 { width:300px; max-width:100%; }
.inline { display:flex; align-items:center; gap:10px; flex-wrap:wrap; }
.hint { color:var(--sub); }
.seg { display:inline-flex; flex-wrap:wrap; }
.seg span { border:1px solid #cfcfcf; padding:8px 0; width:115px; text-align:center; color:var(--sub); background:#fff; }
.seg span + span { border-left:0; }
.seg span.on { background:var(--green); border-color:var(--green); color:#fff; }
.selected-cat { color:var(--blue); }
.selected-cat b { font-weight:700; }
.thumb { width:140px; height:140px; object-fit:cover; border:1px solid var(--line); display:block; }
.thumbs { display:flex; gap:8px; flex-wrap:wrap; }
.thumbs img { width:110px; height:110px; object-fit:cover; border:1px solid var(--line); }
.detail-frame { max-width:480px; max-height:720px; overflow:auto; border:1px solid var(--line); }
.detail-frame img { display:block; width:100%; }
.tags { display:flex; gap:6px; flex-wrap:wrap; }
.tag { border:1px solid #ddd; background:#f7f7f7; padding:4px 10px; }
.missing { color:var(--red); }
.decide-row .box { border-color:var(--orange); }
.decide-note { margin-top:8px; color:#c25e00; font-size:12px; }
.warn-note { margin-top:8px; color:#c25e00; font-size:12px; }
.copy { border:0; border-left:1px solid var(--field); background:#fff; color:var(--sub); font-size:11px; padding:0 10px; cursor:pointer; font-family:inherit; }

.sec-foot { border-top:1px solid #f0f0f0; padding:12px 34px 16px; }
details.ai > summary { display:flex; align-items:center; gap:10px; padding:10px 14px; cursor:pointer; list-style:none;
                       background:#f5f3ff; border-radius:3px; }
details.ai > summary::-webkit-details-marker { display:none; }
details.ai > summary .lbl { color:var(--ai); font-weight:700; white-space:nowrap; }
details.ai > summary .lbl svg { width:11px; height:11px; fill:var(--ai); vertical-align:-1px; margin-right:4px; }
details.ai > summary .opinion { flex:1; color:#333; }
details.ai > summary:hover { background:#ece8ff; }
details.ai > summary .more { width:8px; height:8px; flex:none; margin:0 4px 3px 8px;
                             border-right:2px solid var(--ai); border-bottom:2px solid var(--ai); transform:rotate(45deg); }
details.ai[open] > summary .more { transform:rotate(-135deg); margin:3px 4px 0 8px; }
details.ai[open] > summary { border-radius:3px 3px 0 0; }
.ai-body { background:#fff; border:1px solid #ece8fd; border-top:0; padding:14px 16px 16px; }
.ai-sub { display:flex; align-items:baseline; gap:8px; flex-wrap:wrap; font-weight:700; margin:16px 0 6px; }
.ai-sub:first-child { margin-top:0; }
.ai-sub small { font-weight:400; color:var(--muted); font-size:12px; }
.ai-body a { color:var(--blue); text-decoration:none; }
.ai-body .pair { display:flex; gap:12px; flex-wrap:wrap; }
.ai-body .pair figure { margin:0; width:220px; } .ai-body .pair img { width:100%; border:1px solid var(--line); }
.ai-body figcaption { font-size:11px; color:var(--muted); margin-top:3px; word-break:break-all; }
.ai-body .muted { color:var(--muted); }
table.grid { border-collapse:collapse; width:100%; font-size:12px; }
table.grid th { background:#f7f7f7; color:var(--sub); font-weight:400; text-align:left; padding:8px 10px; border:1px solid #e9e9e9; }
table.grid td { padding:8px 10px; border:1px solid #e9e9e9; vertical-align:top; }
table.grid tr.picked td { background:#f4f1ff; }
.r-pass { color:#4b5563; } .r-pass::before { content:"✓ "; }
ul.checklist { list-style:none; margin:0; padding:0; border:1px solid #e9e9e9; font-size:12px; }
ul.checklist li { display:flex; gap:10px; align-items:baseline; padding:8px 12px; border-top:1px solid #f0f0f0; }
ul.checklist li:first-child { border-top:0; }
ul.checklist .ic { width:16px; flex:none; font-weight:700; text-align:center; }
ul.checklist li.pass .ic::before { content:"✓"; color:#6b7280; }
ul.checklist li.warning .ic::before { content:"!"; color:var(--orange); }
ul.checklist li.error .ic::before { content:"✕"; color:var(--red); }
ul.checklist .lb { width:96px; flex:none; font-weight:700; color:#333; }
ul.checklist .q { flex:1; color:#555; }
ul.checklist .val { color:var(--sub); text-align:right; max-width:45%; }
ul.checklist li.warning { background:#fff8f0; } ul.checklist li.error { background:#fff3f3; }
ul.checklist li.warning .val { color:#c25e00; } ul.checklist li.error .val { color:var(--red); }
.r-warning { color:var(--orange); font-weight:700; } .r-error { color:var(--red); font-weight:700; }

@media (max-width: 640px) {
  .wrap { padding:8px 8px 40px; }
  details.sec > summary, .todo-head { padding:16px; } .sec-body { padding:12px 16px 18px; } .sec-foot { padding:12px 16px; }
  .todo-row { padding:12px 16px; flex-wrap:wrap; } .todo-row .item { width:auto; }
  .row { flex-direction:column; } .row .label { width:auto; padding:0 0 6px; }
  .sec-foot { padding:10px 16px 14px; }
  details.ai > summary, .preset { flex-wrap:wrap; } details.ai > summary .opinion, .preset .opinion { flex-basis:100%; order:3; }
  .seg span { width:96px; }
  .thumbs img { width:88px; height:88px; }
  ul.checklist li { flex-wrap:wrap; } ul.checklist .val, ul.checklist .q { max-width:100%; text-align:left; padding-left:26px; width:100%; }
}
"""

JS = """
document.querySelectorAll('button.copy').forEach(b => b.addEventListener('click', ev => {
  ev.preventDefault();
  navigator.clipboard.writeText(b.dataset.text).then(() => { b.textContent = '복사됨'; setTimeout(() => b.textContent = '복사', 1200); });
}));
document.querySelectorAll('a[href^="#sec-"]').forEach(a => a.addEventListener('click', () => {
  const el = document.querySelector(a.getAttribute('href')); if (el) el.open = true;
}));
"""

DIGITS = "영일이삼사오육칠팔구"


def hangul_amount(n):
    """32900 → 삼만이천구백"""
    def four(x):
        out = ""
        for value, unit in ((1000, "천"), (100, "백"), (10, "십"), (1, "")):
            d = x // value % 10
            if d:
                out += ("" if d == 1 and unit else DIGITS[d]) + unit
        return out
    parts = []
    for value, unit in ((10**8, "억"), (10**4, "만"), (1, "")):
        chunk = n // value % 10000
        if chunk:
            parts.append(four(chunk) + unit)
    return "".join(parts) or "영"


def e(value):
    return escape(str(value)) if value not in (None, "", []) else '<span class="missing">미입력</span>'


def box(value, unit="", cls="", copy=False):
    empty = value in (None, "")
    v = escape(str(value)) if not empty else "미입력"
    tail = f'<div class="unit">{unit}</div>' if unit else ""
    if copy and not empty:
        tail += f'<button class="copy" data-text="{escape(str(value), quote=True)}">복사</button>'
    return f'<div class="box {cls}{" empty" if empty else ""}"><div class="v">{v}</div>{tail}</div>'


def seg(options, on):
    return '<div class="seg">' + "".join(f'<span class="{"on" if o == on else ""}">{escape(o)}</span>' for o in options) + "</div>"


def row(label, field, required=False, cls=""):
    dot = '<span class="dot"></span>' if required else ""
    return f'<div class="row {cls}"><div class="label">{escape(label)}{dot}</div><div class="field">{field}</div></div>'


def off(label, required=False):
    """사용하지 않는 기능: 판매자센터와 같은 '설정함 / 설정안함' 버튼 줄."""
    return row(label, seg(["설정함", "설정안함"], "설정안함"), required=required)


NOT_SUPPORTED = '<p class="hint" style="margin:10px 0 0">이 기능은 아직 자동 작성을 지원하지 않습니다. 필요하면 판매자센터에서 직접 설정해 주세요.</p>'


def kv_row(label, text):
    return row(label, escape(text))


def grid(headers, rows, picked=None):
    head = "".join(f"<th>{h}</th>" for h in headers)
    body = "".join(f'<tr class="{"picked" if picked and picked(i) else ""}">' + "".join(f"<td>{c}</td>" for c in r) + "</tr>"
                   for i, r in enumerate(rows))
    return f'<table class="grid"><tr>{head}</tr>{body}</table>'


class Preview:
    def __init__(self, data, criteria=""):
        self.criteria = criteria  # 작성 기준 페이지 경로 (섹션 링크용)
        self.checks = data.get("checks", {}).get("items", [])
        self.legacy = data.get("basis", {}) if isinstance(data.get("basis"), dict) else {}
        self.parts = []
        self.anchors = {}

    def checks_of(self, names):
        return [c for c in self.checks if c["section"] in names]

    def checks_table(self, names):
        rows = self.checks_of(names)
        if not rows:
            return ""
        bad = [c for c in rows if c["result"] != "pass"]
        summary = f"{len(rows)}개 모두 통과" if not bad else f"{len(rows)}개 중 {len(bad)}개 {RESULT_LABEL[bad[0]['result']]}"
        items = "".join(
            f'<li class="ck {c["result"]}"><span class="ic"></span><span class="lb">{escape(c.get("label", c["rule"]))}</span>'
            f'<span class="q">{escape(c.get("question", c["rule"]))}</span>'
            f'<span class="val">{escape(c["detail"])}</span></li>'
            for c in bad + [c for c in rows if c["result"] == "pass"])
        return (f'<div class="ai-sub">규칙 검사 <small>네이버 등록 규칙에 맞는지 프로그램이 확인한 결과 · {summary}</small></div>'
                f'<ul class="checklist">{items}</ul>')

    def flag(self, names):
        bad = [c for c in self.checks_of(names) if c["result"] != "pass"]
        if not bad:
            return ""
        if any(c["result"] == "error" for c in bad):
            return f'<span class="state err">오류 {len(bad)}</span>'
        return f'<span class="state warn">확인 필요 {len(bad)}</span>'

    def add(self, no, title, value="", required=False, summary="설정안함", open_=False,
            ai=None, check_sections=(), preset=None, unsupported=False):
        """value: 판매자센터 값 영역. ai: (판단 요약, 펼침 내용) 이면 섹션 하단에 'AI 판단 근거' 띠.
        preset: 스토어 기본 설정값을 적용한 섹션의 안내 문장. 접힌 상태에 [기본 설정] 배지, 하단에 '기본 설정' 띠."""
        self.anchors[title] = f"sec-{no}"
        flag = self.flag(check_sections)
        is_open = open_ or bool(flag)
        dot = '<span class="dot"></span>' if required else ""
        state = flag or (f'<span class="state">{summary}</span>' if not open_ else "")
        if ai:
            src = f'<span class="bd bd-ai src">{STAR}AI 작성</span>'
        elif preset:
            src = f'<span class="bd bd-preset-solid src">{GEAR}기본 설정</span>'
        elif unsupported:
            src = '<span class="bd bd-na src">자동 작성 미지원</span>'
        else:
            src = ""
        foot = ""
        link = f'<a class="rule-link" href="{self.criteria}#c-{no}" target="_blank">작성 기준 ›</a>' if self.criteria else ""
        if preset:
            foot = (f'<div class="sec-foot"><div class="preset"><span class="lbl">{GEAR}기본 설정</span>'
                    f'<span class="opinion">{escape(preset)}</span>{link}</div></div>')
        if ai:
            opinion, detail = ai
            body = detail + self.checks_table(check_sections)
            ai_open = " open" if any(c.get("decision") or c["result"] == "error"
                                     for c in self.checks_of(check_sections) if c["result"] != "pass") else ""
            foot = (f'<div class="sec-foot"><details class="ai"{ai_open}><summary><span class="lbl">{STAR}AI 판단 근거</span>'
                    f'<span class="opinion">{escape(opinion) if opinion else "판단 근거가 기록되지 않았습니다."}</span>'
                    f'{link}<span class="more"></span></summary><div class="ai-body">{body or "<span class=muted>추가 근거 없음</span>"}</div></details></div>')
        content = f'<div class="sec-body">{value}</div>{foot}' if value or foot else ""
        self.parts.append(
            f'<details class="sec" id="sec-{no}"{" open" if is_open else ""}><summary><h2>{escape(title)}{dot}</h2>{src}'
            f'{state if state else "<span class=state></span>"}<span class="toggle"></span></summary>{content}</details>')


def build(pdir, data, cfg):
    criteria = ROOT / "작성기준.html"
    pv = Preview(data, quote(os.path.relpath(criteria, pdir).replace(os.sep, "/")) if criteria.exists() else "")
    inp = data.get("input", {})
    price = data.get("price") or {}
    images = data.get("images") or {}
    product_cfg, delivery, after, origin, ncfg = cfg["product"], cfg["delivery"], cfg["after_service"], cfg["origin"], cfg["notice"]

    # 카테고리
    cat = data.get("category", {})
    query = inp.get("name", "")
    value = f'<div class="selected-cat">선택한 카테고리 : <b>{e(cat.get("path"))}</b></div>'
    detail = ""
    candidates = cat.get("candidates", [])
    if candidates:
        pick = '<span class="bd bd-pick">AI 선택</span>'
        rows = [[pick if c.get("code") == cat.get("code") else "", escape(c.get("path", "")),
                 escape(str(c.get("demand", ""))), escape(c.get("reason", ""))] for c in candidates]
        detail += ('<div class="ai-sub">근거 데이터 <small>출처: 네이버 쇼핑인사이트 · 최근 3개월 카테고리 클릭 수</small></div>'
                   + grid(["", "후보 카테고리", "클릭 수요 (100 기준 상대값)", "AI가 본 특징"], rows,
                          picked=lambda i: candidates[i].get("code") == cat.get("code")))
    detail += f'<div class="ai-sub">카테고리 코드</div>{e(cat.get("code"))}'
    if query:
        detail += (f'<div class="ai-sub">직접 확인</div><a href="https://search.shopping.naver.com/search/all?query={quote(query)}" '
                   f'target="_blank">네이버쇼핑에서 \'{escape(query)}\' 검색 결과 보기 ›</a>')
    pv.add("1", "카테고리", value, required=True, open_=True, ai=(cat.get("basis"), detail), check_sections=["카테고리"])

    pv.add("2", "예약구매", off("예약구매", required=True) + NOT_SUPPORTED, unsupported=True)

    # 상품명
    name = data.get("name", {})
    title = name.get("value", "")
    if title:
        name_box = (f'<div class="box"><div class="v">{escape(title)}</div><div class="count"><b>{len(title)}</b>/100</div>'
                    f'<button class="copy" data-text="{escape(title, quote=True)}">복사</button></div>')
    else:
        name_box = box(None)
    value = row("상품명", name_box, required=True)
    detail = ""
    if name.get("parts"):
        detail += '<div class="ai-sub">상품명 구성</div>' + grid(
            ["단어", "출처"], [[escape(p.get("text", "")), escape(p.get("source", ""))] for p in name["parts"]])
    if name.get("keywords"):
        detail += ('<div class="ai-sub">근거 데이터 <small>출처: 네이버 쇼핑인사이트 · 카테고리 내 키워드 클릭 수</small></div>'
                   + grid(["키워드", "클릭 수 (최대 = 100)"],
                          [[escape(k["keyword"]) + (' <span class="bd bd-pick">사용</span>' if k.get("used") else ""),
                            escape(str(k.get("score", "")))] for k in name["keywords"]],
                          picked=lambda i: name["keywords"][i].get("used")))
    pv.add("3", "상품명", value, required=True, open_=True, ai=(name.get("basis"), detail), check_sections=["상품명"])

    # 판매가
    if price:
        provisional = price.get("provisional")
        note = ('<div class="decide-note"><span class="bd bd-decide">결정 필요</span> '
                '임시 가격 규칙으로 계산한 값입니다. 이 가격으로 등록할지 정해 주세요.</div>') if provisional else ""
        list_box = box(f"{price['list']:,}", "원", "w-200")
        value = row("판매가", f'<div class="inline">{list_box}'
                              f'<span class="hint">{hangul_amount(price["list"])} 원</span></div>{note}',
                    required=True, cls="decide-row" if provisional else "")
        rate = round(price["discount_rate"] * 100)
        value += row("즉시할인", f'{seg(["설정함", "설정안함"], "설정함")}'
                                 f'<div class="inline" style="margin-top:10px"><span>기본할인</span>{box(rate, "%", "w-90")}<span>할인</span></div>'
                                 f'<div style="margin-top:8px">할인가 <b>{price["sale"]:,}원</b> <span class="hint">({price["discount"]:,}원 할인)</span></div>')
        value += row("예약할인", '<span class="hint">설정안함</span>') + off("판매기간")
        value += row("부가세", seg(["과세상품", "면세상품", "영세상품"],
                                 {"TAX": "과세상품", "DUTYFREE": "면세상품", "SMALL": "영세상품"}.get(product_cfg["tax_type"], "과세상품")),
                     required=True)
        steps = [["매입가", f'{price["cost"]:,}원' if price.get("cost") else "-"]]
        if provisional and price.get("cost"):
            mult = round(price["list"] / price["cost"], 2)
            steps.append([f"임시 규칙 적용 (매입가 × {cfg['price']['provisional_multiplier']})",
                          f'{round(price["cost"] * cfg["price"]["provisional_multiplier"]):,}원'])
            steps.append([f'{cfg["price"]["list_price_round"]}원 단위 반올림 → 정가', f'<b>{price["list"]:,}원</b>'])
        else:
            steps.append(["입력한 정가", f'<b>{price["list"]:,}원</b>'])
        steps.append([f"기본할인 {rate}% 적용 → 할인가", f'{price["sale"]:,}원 (매입가의 {price.get("markup", "-")}배)'])
        detail = '<div class="ai-sub">계산 과정 <small>정해진 규칙으로 계산</small></div>' + grid(["단계", "값"], steps)
        if provisional:
            opinion = (f'정가가 입력되지 않아 임시 규칙(매입가 × {cfg["price"]["provisional_multiplier"]})으로 계산했습니다. '
                       '실제 가격 기준이 있으면 알려 주세요.')
        else:
            opinion = f"입력한 정가에 기본할인 {rate}%를 적용했습니다."
    else:
        value, detail, opinion = row("판매가", box(None), required=True), "", None
    pv.add("4", "판매가", value, required=True, open_=True, ai=(opinion, detail), check_sections=["판매가"])
    pv.add("4-1", "N배송으로 판매하기", row("네이버 풀필먼트", '<span class="hint">신청 안 함</span>', required=True) + NOT_SUPPORTED,
           summary="사용안함", unsupported=True)

    pv.add("5", "재고수량", f'<div class="inline">{box(product_cfg["stock_quantity"], "개", "w-200")}</div>',
           required=True, open_=True, preset="스토어 기본 설정값을 그대로 적용했습니다. 바꾸려면 말씀해 주세요 (모든 상품에 적용).")
    pv.add("6", "옵션", off("선택형") + off("직접입력형") + NOT_SUPPORTED, unsupported=True)

    # 상품이미지/동영상
    rep = images.get("representative") or {}
    optional = images.get("optional", [])
    rep_html = f'<img class="thumb" src="{escape(rep["file"])}">' if rep else box(None)
    thumbs = "".join(f'<img src="{escape(o["file"])}" title="{escape(o["source"])}">' for o in optional)
    value = (row("대표이미지", rep_html, required=True)
             + row(f"추가이미지 ({len(optional)}/9)", f'<div class="thumbs">{thumbs}</div>' if thumbs else '<span class="hint">없음</span>')
             + row("동영상", '<span class="hint">없음</span>') + row("동영상 타이틀", box(None).replace("미입력", "없음")))
    detail = ""
    if rep.get("original_file"):
        detail += ('<div class="ai-sub">대표이미지 보정본 · 원본 비교</div><div class="pair">'
                   f'<figure><img src="{escape(rep["file"])}"><figcaption>보정본 (등록됨)</figcaption></figure>'
                   f'<figure><img src="{escape(rep["original_file"])}"><figcaption>원본 · {escape(rep.get("original", ""))}</figcaption></figure></div>'
                   + (f'<div class="muted" style="margin-top:6px">보정 지시: {escape(rep["edit"])}</div>' if rep.get("edit") else ""))
    elif rep:
        detail += '<div class="ai-sub">대표이미지 원본</div><span class="muted">원본 사진 기록 없음 — 보정본이라면 원본과 비교할 수 없습니다.</span>'
    if rep or optional:
        img_rows = ([["대표", escape(rep.get("source", ""))]] if rep else []) + [[f"추가 {i}", escape(o["source"])] for i, o in enumerate(optional, 1)]
        detail += '<div class="ai-sub">사용한 사진</div>' + grid(["순서", "원본 파일"], img_rows)
    pv.add("7", "상품이미지/동영상", value, required=True, open_=True,
           ai=(images.get("basis") or pv.legacy.get("thumbnail"), detail), check_sections=["상품이미지"])

    pv.add("8", "라이브 숏클립", off("대표이미지 숏클립 노출 설정") + NOT_SUPPORTED, unsupported=True)

    # 상세설명
    d = data.get("detail") or {}
    imgs = d.get("images", [])
    if imgs:
        frame = "".join(f'<img src="{escape(f)}">' for f in imgs)
        value = f'<div class="hint" style="margin-bottom:8px">상세 이미지 {len(imgs)}장</div><div class="detail-frame">{frame}</div>'
    else:
        path = pdir / d.get("file", "detail.html")
        value = f'<div class="detail-frame">{path.read_text(encoding="utf-8") if path.exists() else e(None)}</div>'
    pv.add("9", "상세설명", value, required=True, open_=True, ai=(d.get("basis"), ""), check_sections=["상세설명", "입력 정보"])

    # 상품 주요정보
    origin_name = ORIGIN_LABEL.get(origin["area_code"], origin["area_code"])
    attrs = ", ".join(f'{a["name"]}: {a["value"]}' for a in data.get("attributes", []))
    attr_map = {a["name"]: a["value"] for a in data.get("attributes", [])}
    attr_rows = [[escape(n), escape(str(attr_map.get(n, "")) or "선택 안 함")] for n in ("형태", "가로사이즈", "세로사이즈", "높이", "무게")]
    value = (row("모델명", '<span class="hint">카탈로그 연결 안 함</span>') + row("품번", box(None).replace("미입력", "없음"))
             + row("브랜드", box(product_cfg["brand"] or None)) + row("제조사", box(product_cfg["manufacturer"] or None))
             + row("상품속성", grid(["기타속성", "값"], attr_rows))
             + row("KC인증", seg(["KC인증 있음", "KC인증 없음"], "KC인증 없음")
                   + '<div class="hint" style="margin-top:6px">KC 안전관리대상 아님</div>')
             + row("인증정보", '<span class="hint">없음</span>')
             + row("원산지", box(origin_name or None, cls="w-300"), required=True)
             + row("상품상태", seg(["신상품", "중고상품"], "신상품"), required=True)
             + row("맞춤제작", '<span class="hint">해당 없음</span>')
             + row("제조일자 / 유효일자", '<span class="hint">없음</span>')
             + row("미성년자 구매", seg(["가능", "불가능"], "가능" if product_cfg["minor_purchasable"] else "불가능"), required=True))
    pv.add("10", "상품 주요정보", value, required=True, summary=f"원산지 {escape(origin_name or '미입력')} · 신상품",
           preset="원산지·상품상태·미성년자 구매 등은 스토어 기본 설정값을 그대로 적용했습니다. 바꾸려면 말씀해 주세요 (모든 상품에 적용).")

    pv.add("11", "사이즈", off("사이즈") + NOT_SUPPORTED, unsupported=True)

    # 상품정보제공고시
    notice = data.get("notice", {})
    notice_type = NOTICE_LABEL.get(ncfg["type"], ncfg["type"])
    value = (row("상품군", box(notice_type, cls="w-300")) + row("품명", box(notice.get("item_name")))
             + row("모델명", box(notice.get("model_name")))
             + row("법에 의한 인증·허가 사항", seg(["직접입력", "해당사항 없음"], "해당사항 없음"))
             + row("제조자(사)", box(ncfg["manufacturer"] or None))
             + row("소비자 상담 관련 전화번호", box(ncfg["customer_service_phone"] or None, cls="w-300"))
             + row("청약철회·반품비용 등 4개 항목", '<span class="hint">상품상세 참조</span>'))
    pv.add("12", "상품정보제공고시", value, required=True, summary=f"설정함 / {escape(notice_type)}",
           preset="품명·모델명은 상품 정보로 작성하고, 상품군·제조자·상담 전화번호는 스토어 기본 설정값을 적용했습니다.")

    # 배송 · 반품/교환 · A/S
    company = COMPANY_LABEL.get(delivery["company"], delivery["company"])
    fee = FEE_LABEL.get(delivery["fee_type"], delivery["fee_type"] or "미입력")
    store_warn = [c for c in pv.checks_of(["스토어 설정"]) if c["result"] != "pass"]
    warn = "".join(f'<div class="warn-note">{escape(c["detail"])}</div>' for c in store_warn)
    value = (row("배송여부", seg(["배송", "배송없음"], "배송"), required=True)
             + row("배송방법", seg(["택배, 소포, 등기", "직접배송(화물배달)"], "택배, 소포, 등기"), required=True)
             + row("배송속성", seg(["일반배송", "오늘출발"], "일반배송"), required=True)
             + row("택배사", box(company, cls="w-300"), required=True)
             + row("묶음배송", seg(["가능", "불가(개별계산)"], "불가(개별계산)"), required=True)
             + row("상품별 배송비", box(fee + (f' · 기본 {delivery["base_fee"]:,}원' if delivery["base_fee"] else ""), cls="w-300"), required=True)
             + off("제주/도서산간 추가배송비")
             + row("별도 설치비", seg(["있음", "없음"], "없음"), required=True)
             + row("출고지", "설정됨" if delivery["shipping_address_id"] else '<span class="missing">미설정</span>', required=True)
             + warn)
    pv.add("13", "배송", value, required=True, summary=f"{escape(company)} · {escape(fee)}", check_sections=["스토어 설정"],
           preset="스토어 기본 설정값을 그대로 적용했습니다. 바꾸려면 말씀해 주세요 (모든 상품에 적용).")
    return_box = box(f"{delivery['return_fee']:,}", "원", "w-200")
    exchange_box = box(f"{delivery['exchange_fee']:,}", "원", "w-200")
    value = (row("반품/교환 택배사", box("기본 반품택배사", cls="w-300"), required=True)
             + row("반품배송비(편도)", f'<div class="inline">{return_box}</div>', required=True)
             + row("교환배송비(왕복)", f'<div class="inline">{exchange_box}</div>', required=True)
             + row("반품/교환지", "설정됨" if delivery["return_address_id"] else '<span class="missing">미설정</span>', required=True))
    pv.add("14", "반품/교환", value, required=True,
           summary=f'반품 {delivery["return_fee"]:,}원 · 교환 {delivery["exchange_fee"]:,}원', preset="스토어 기본 설정값을 그대로 적용했습니다. 바꾸려면 말씀해 주세요 (모든 상품에 적용).")
    value = (row("A/S전화번호", box(after["phone"] or None, cls="w-300"), required=True)
             + row("A/S안내", box(after["guide"] or None), required=True)
             + row("판매자 특이사항", box(None).replace("미입력", "없음")))
    pv.add("15", "A/S, 특이사항", value, required=True, summary=escape(after["phone"] or "미입력"), preset="스토어 기본 설정값을 그대로 적용했습니다. 바꾸려면 말씀해 주세요 (모든 상품에 적용).")

    pv.add("16", "추가상품", off("선택형") + NOT_SUPPORTED, unsupported=True)
    benefit = (row("최소구매수량", box(None).replace("미입력", "없음 (기본 1개)")) + row("최대구매수량", '<span class="hint">제한 없음</span>')
               + off("복수구매할인") + row("포인트", '<span class="hint">지급 안 함</span>') + off("무이자할부")
               + row("사은품", '<span class="hint">없음</span>') + row("이벤트", '<span class="hint">없음</span>') + NOT_SUPPORTED)
    pv.add("17", "구매/리뷰 혜택 조건", benefit, unsupported=True)

    # 검색설정
    tags = data.get("tags", [])
    seo = data.get("seo", {})
    tag_html = '<div class="tags">' + "".join(f'<span class="tag">{escape(t)}</span>' for t in tags) + "</div>" if tags else box(None)
    value = (row(f"태그 ({len(tags)}/10)", tag_html + (f'<button class="copy" style="border:1px solid #ddd;margin-top:6px;padding:3px 10px" data-text="{escape(",".join(tags), quote=True)}">복사</button>' if tags else ""))
             + row("Page Title", box(seo.get("page_title"), copy=True))
             + row("Meta description", box(seo.get("meta_description"), copy=True)))
    tag_rows = [[escape(t.get("tag", "")), escape(t.get("reason", ""))] for t in data.get("tag_basis", [])]
    detail = ('<div class="ai-sub">태그별 선정 이유</div>' + grid(["태그", "이유"], tag_rows)) if tag_rows else ""
    pv.add("18", "검색설정", value, open_=True, ai=(seo.get("basis") or pv.legacy.get("tags"), detail), check_sections=["검색설정"])

    pv.add("19", "판매자 코드", "".join(row(n, box(None).replace("미입력", "없음"))
                                       for n in ("판매자 상품코드", "판매자 바코드", "판매자 내부코드1", "판매자 내부코드2")), unsupported=True)
    stage = data.get("status", {}).get("stage", "draft")
    display = "전시중" if stage == "public" else "전시중지"
    channel = (row("채널명", "스마트스토어", required=True)
               + row("스마트스토어전용 상품명", '<span class="hint">사용 안 함</span>')
               + row("가격비교 사이트 등록", "네이버쇼핑")
               + row("전시상태", seg(["전시중", "전시중지"], display)
                     + ('<div class="hint" style="margin-top:6px">비공개로 등록한 뒤, 승인하면 전시중으로 바꿉니다.</div>' if display == "전시중지" else ""),
                     required=True)
               + off("알림받기 동의 고객 전용상품") + off("공지사항"))
    pv.add("20", "노출 채널", channel, required=True, summary=f"스마트스토어 · {display}", preset="스토어 기본 설정값을 그대로 적용했습니다. 바꾸려면 말씀해 주세요 (모든 상품에 적용).")
    return pv


def todo_box(data, anchors):
    items = data.get("checks", {}).get("items", [])
    todo = [c for c in items if c["result"] == "error"] + [c for c in items if c.get("decision") and c["result"] == "warning"]
    if not data.get("checks"):
        return '<div class="todo"><div class="todo-head">자동 검사를 아직 실행하지 않았습니다</div></div>'
    if not todo:
        return '<div class="todo clear"><div class="todo-head">등록 전 확인할 사항이 없습니다</div></div>'
    has_err = any(c["result"] == "error" for c in todo)
    rows = []
    for c in todo:
        title = CHECK_TO_TITLE.get(c["section"], c["section"])
        badge = '<span class="bd bd-fix">수정 필요</span>' if c["result"] == "error" else '<span class="bd bd-decide">결정 필요</span>'
        link = f'<a class="btn" href="#{anchors[title]}">바로가기</a>' if title in anchors else ""
        rows.append(f'<div class="todo-row">{badge}<span class="item">{escape(title)}</span>'
                    f'<span class="desc">{escape(c["detail"] or c["rule"])}</span>{link}</div>')
    return (f'<div class="todo"><div class="todo-head">등록 전 확인 사항<em class="{"err" if has_err else ""}">{len(todo)}건</em></div>'
            + "".join(rows) + "</div>")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("product")
    ap.add_argument("--open", action="store_true", help="생성 후 브라우저로 열기")
    args = ap.parse_args()

    pdir = product_dir(args.product)
    data = load_product(pdir)
    pv = build(pdir, data, store_config())
    title = data.get("name", {}).get("value") or data.get("input", {}).get("name", "상품")
    stage = STAGE_LABEL.get(data.get("status", {}).get("stage", "draft"), "비공개 등록 전")
    checked = data.get("checks", {}).get("checked_at", "-").replace("T", " ")[:16]
    html = (
        f'<!doctype html><html lang="ko"><head><meta charset="utf-8">'
        f'<meta name="viewport" content="width=device-width, initial-scale=1"><title>미리보기 · {escape(title)}</title>'
        f'<style>{CSS}</style></head><body>'
        f'<div class="topbar">상품등록<span>검토</span>'
        + (f'<a href="{pv.criteria}" target="_blank">작성 기준 보기 ›</a>' if pv.criteria else "")
        + f'<div class="stage">{stage} · {escape(checked)} 검사</div></div>'
        f'<div class="wrap"><div class="pagehead"><h1>{escape(title)}</h1><span class="req">● 필수항목</span></div>'
        f'{todo_box(data, pv.anchors)}{"".join(pv.parts)}</div><script>{JS}</script></body></html>')
    out = pdir / "preview.html"
    out.write_text(html, encoding="utf-8")
    print(f"미리보기 생성: {out}")
    if args.open:
        webbrowser.open(out.as_uri())


if __name__ == "__main__":
    main()

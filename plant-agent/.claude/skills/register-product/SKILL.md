---
name: register-product
description: 새 식물 상품의 네이버 스마트스토어 등록 정보를 작성하고 검토용 미리보기를 만든다. 사용자가 새 상품 등록을 요청하거나 사진을 넣었다고 할 때 사용.
---

# 상품 등록 정보 작성

사진과 기본 정보로 등록 정보(product.json, detail.html)를 작성하고 미리보기를 만든다.

**무엇을 어떻게 쓸지는 [작성기준.md](../../../작성기준.md)를 따른다.** 시작 전에 읽는다. 이 파일은 절차(순서·스크립트·기록 위치)만 다룬다.
`{{설정 이름}}`은 config의 스토어 설정값을 가리킨다 (작성 기준 페이지에 실제 값으로 표시됨).

## 근거 기록 규칙

미리보기는 AI가 정한 섹션 하단에 'AI 판단' 띠로 근거를 보여준다. 아래 위치에만 기록한다 (최상위 `basis` 사용 금지).

- `basis` 문장은 사용자가 읽는 **한두 문장**으로 쓴다. 무엇을 왜 그렇게 정했는지 결론부터. 파일명·URL·내부 용어는 넣지 않는다.
  - 좋은 예: "드라세나류는 공기정화식물로 통용되고, 최근 3개월 클릭 수요도 관엽식물보다 높아 공기정화식물이 적합합니다."
- 수치·후보·출처 같은 세부 근거는 `candidates`, `parts`, `keywords`, `tag_basis` 같은 구조화 필드에 넣는다 (펼침 영역에 표로 표시됨).

| 항목 | 기록 위치 |
|---|---|
| 카테고리 | `category.basis`, `category.candidates[]` (`path`, `code`, `reason`, `demand`) |
| 상품명 | `name.basis`, `name.parts[]` (`text`, `source`: 식물명 / 구성 / 키워드 / 특징), `name.keywords[]` (`keyword`, `score`, `used`: 쇼핑인사이트 키워드 비교 결과) |
| 판매가 | 스크립트가 기록 |
| 상품이미지 | `prepare_images.py`의 `--basis`, `--original`, `--edit` |
| 상세설명 | `detail.basis` (문구 출처: 입력 정보 / 일반 관리법 / 사용자 지정 문구) |
| 검색설정 | `tag_basis[]` (`tag`, `reason`), `seo.basis` |

수정 이력과 대화 중 결정은 log.md에도 기록한다.

## 1. 입력 준비

1. 상품 폴더 만들기 — 사진 출처에 따라:
   - 채팅 첨부(경로를 알 때): `uv run scripts/new_product.py "<상품명>" --photos "<경로1>" "<경로2>" ...`
   - 사진함: `uv run scripts/new_product.py "<상품명>"`
   - 이미 상품 폴더가 있으면 이 단계를 건너뛴다.
   스크립트가 `input/info.toml`과 `product.json` 양식을 함께 만든다.
2. `input/info.toml`을 채운다. 비어 있는 필수 정보는 한 번에 모아 묻는다.
   - 식물 이름, 구성(수량), 매입가, 높이, 화분 지름
   - 정가는 사용자가 알려주면 입력하고, 모르면 비워 둔다 (임시 가격 규칙 적용)
   - 답을 받지 못한 항목은 비워 두고 진행한다 (상세설명에서 해당 항목 생략).
3. `product.json`의 `input` 항목을 채운다.

## 2. 이미지

1. `input/`의 사진을 모두 열어 보고 작성기준 '상품이미지/동영상'에 따라 대표이미지와 추가이미지 순서를 정한다.
2. 사용자가 대표이미지 보정을 요청하면 원본 사진 1장을 골라 작성기준의 보정 원칙대로 보정본을 만들고 `input/대표_<설명>.png`로 저장한다.
3. `uv run scripts/prepare_images.py products/<상품> --rep "<파일명>" --order "<파일명>,<파일명>,..." --basis "<선택 근거>"`
   - 보정본을 대표로 쓰면 `--original "<원본 파일명>" --edit "<보정 지시 내용>"`을 함께 넘긴다. 미리보기에서 원본과 나란히 비교된다.
4. 결과의 규격 경고(정사각형 아님, 최소 300px 미만)는 사용자에게 전달한다.

## 3. 카테고리

작성기준 '카테고리'에 따라 후보를 정한다.

1. 과거 기록 확인: `uv run scripts/category_history.py`
2. 후보 코드 조회: `uv run scripts/naver_api.py categories --find "원예/식물>"`
3. 수요 비교: `uv run scripts/shopping_insight.py categories <후보 코드> ...`
4. product.json `category`에 기록한다:
   - `path`, `code`: 1순위 후보
   - `candidates`: 후보 목록 `[{"path", "code", "reason", "demand"}]`
   - `basis`: 선정 이유 한 줄
5. 미리보기의 'AI 판단 근거'에 네이버쇼핑 검색 결과 링크가 표시되어, 사용자가 검토할 때 실제 상위 상품의 카테고리와 비교할 수 있다.

## 4. 상품명

작성기준 '상품명'에 따라 작성한다.

- 식물 이름 표기 비교: `uv run scripts/shopping_insight.py keywords --category <카테고리 코드> <표기1> <표기2> ...`
- 금지어·글자수는 8단계 검증에서 스크립트가 확인한다.
- `name.value`, `name.basis`, `name.parts`에 기록한다. `parts`는 상품명을 구성 요소로 나눠 각 출처를 적는다.

## 5. 가격

`uv run scripts/price.py products/<상품>` — 직접 계산하지 않는다.
임시 가격 규칙이 적용되면 사용자에게 정가 확인을 요청한다.

## 6. 상세설명

`detail.html`에 HTML 조각으로 작성한다 (`<html>`, `<head>`, `<body>` 없이). 내용·구성은 작성기준 '상세설명'을 따른다.
스타일 기준은 `products/2026-10-29_무늬아이비_1+1/detail.html`.

- 사용 태그: `div, p, h2, h3, img, ul, li, strong, br, table`. 인라인 style 사용 가능.
- `script`, `style`, `iframe`, 이벤트 속성(onclick 등), 외부 링크 금지.
- 사진은 `images/add-N.jpg`처럼 상대 경로로 넣는다.

`detail.basis`에 문구 출처를 적는다 (예: "상품 정보는 입력값, 관리법은 일반 정보, 안내 문구는 사용자 지정").

작성 후 판매자센터 업로드용 이미지를 만든다: `uv run scripts/export_detail.py products/<상품>`

## 7. 검색설정 · 기타

작성기준 '검색설정'에 따라 작성한다.

- `tags`, `tag_basis`(태그마다 선정 이유), `seo.page_title`, `seo.meta_description`, `seo.basis`
- `notice.item_name`: 식물 이름. `notice.model_name`: 상품명과 같은 값 또는 "상세설명 참조".
- `attributes`: 카테고리 속성 중 확실한 것만.

## 8. 검증 · 미리보기

1. `uv run scripts/validate.py products/<상품>` — 오류가 있으면 고치고 다시 실행한다.
2. `uv run scripts/render_preview.py products/<상품> --open` — 미리보기가 브라우저에서 열린다.
3. 사용자에게 요약한다: 카테고리, 상품명, 판매가, 확인이 필요한 항목. 그리고 수정할 부분이 있는지 묻는다.
4. log.md에 작성 일시, 주요 판단 근거, 사용자 수정 요청과 반영 내용을 기록한다.

수정 요청을 받으면 해당 단계만 다시 하고 8단계를 반복한다.

---
name: register-product
description: 새 식물 상품의 네이버 스마트스토어 등록 정보를 작성하고 검토용 미리보기를 만든다. 사용자가 새 상품 등록을 요청하거나 사진을 넣었다고 할 때 사용.
---

# 상품 등록 정보 작성

사진과 기본 정보로 등록 정보(product.json, detail.html)를 작성하고 미리보기를 만든다.
각 단계의 판단 근거는 product.json의 `basis`와 log.md에 기록한다.

## 1. 입력 준비

1. 상품 폴더 확인. 없으면 `products/YYYY-MM-DD_<상품명>/input/`을 만들고 사용자에게 사진을 넣어 달라고 안내한다.
2. `templates/info.template.toml`을 `input/info.toml`로 복사해 채운다. 비어 있는 필수 정보는 한 번에 모아 묻는다.
   - 식물 이름, 구성(수량), 매입가, 높이, 화분 지름
   - 정가는 사용자가 알려주면 입력하고, 모르면 비워 둔다 (임시 가격 규칙 적용)
3. `templates/product.template.json`을 `product.json`으로 복사하고 `input` 항목을 채운다.

## 2. 이미지

1. `input/`의 사진을 모두 열어 보고 대표이미지와 추가이미지 순서를 정한다.
   - 대표이미지: 파일명이 '대표'·'썸네일'로 시작하는 사진이 있으면 그것. 없으면 직접 고른다.
     기준: 식물 전체(화분 포함)가 보임 > 배경이 깔끔함 > 정사각형 > 해상도. 보정된 연출 사진이 있으면 우선.
   - 추가이미지 순서: 전체 모습 → 잎·무늬 근접 → 줄기·화분 등 세부.
2. `uv run scripts/prepare_images.py products/<상품> --rep "<파일명>" --order "<파일명>,<파일명>,..." --basis "<선택 근거>"`
3. 결과의 규격 경고(정사각형 아님, 640px 미만)는 사용자에게 전달한다.

## 3. 카테고리

1. `uv run scripts/search_category.py "<식물 이름>"`
2. 가장 많이 나온 카테고리 경로를 선택한다. 상위 두 경로의 개수 차이가 1 이하이면 두 후보를 미리보기에 함께 적고 사용자에게 선택을 요청한다.
3. 코드 조회: `uv run scripts/naver_api.py categories --find "<경로 마지막 이름>"`
4. product.json `category`에 `path`, `code`, `basis`(예: "검색 상위 10개 중 7개"), `search`(스크립트 출력)를 기록한다.
5. 검색 API 키가 없으면 사용자에게 지금 쓰는 카테고리를 묻고, `basis`에 "사용자 지정"으로 기록한다.

## 4. 상품명

- 구성: `[식물 이름] [구성·수량] [검색 키워드] [특징]`
- 검색 키워드는 3단계 검색 결과의 상위 상품명과 카테고리명에서 고른다 (예: 공기정화식물, 관엽식물, 행잉식물).
- 50자 이내. `config/naming-rules.toml`의 금지어·금지 문자를 쓰지 않고 같은 단어를 반복하지 않는다.
- 사실이 아닌 표현(크기, 효능 과장)을 쓰지 않는다.
- `name.value`, `name.basis`에 기록한다.

## 5. 가격

`uv run scripts/price.py products/<상품>` — 직접 계산하지 않는다.
임시 가격 규칙이 적용되면 사용자에게 정가 확인을 요청한다.

## 6. 상세설명

`detail.html`에 HTML 조각으로 작성한다 (`<html>`, `<head>`, `<body>` 없이).
스타일 기준은 `products/2026-10-29_무늬아이비_1+1/detail.html` (클라이언트 기존 상세페이지 형식을 따름).

- 폭 780px 기준. 사용 태그: `div, p, h2, h3, img, ul, li, strong, br, table`. 인라인 style 사용 가능.
- `script`, `style`, `iframe`, 이벤트 속성(onclick 등), 외부 링크 금지.
- 사진은 `images/add-N.jpg`처럼 상대 경로로 넣는다.
- 구성 순서:
  1. 도입 문구 1줄 + 상품명 (강조색 제목)
  2. 대표 사진 + 식물 소개 2~3문장 (어디에 두기 좋은지)
  3. 나머지 사진
  4. 상품 정보: 높이, 화분 지름, 구성 — info.toml 값만 사용
  5. 키우는 법: 빛, 물, 온도, 통풍 — 일반적으로 알려진 내용만
  6. 안내 사항: 개체별 차이, 반려동물 섭취 주의 등 해당 시
- info.toml에 없는 수치는 쓰지 않는다. 실제와 다른 이미지·인물·농장 등 사실이 아닌 내용을 넣지 않는다.

작성 후 판매자센터 업로드용 이미지를 만든다: `uv run scripts/export_detail.py products/<상품>`

## 7. 검색설정 · 기타

- `tags`: 최대 10개, 공백·특수문자 없이. 상품명에 없는 연관 검색어 위주.
- `seo.page_title`: 상품명 기반 1줄. `seo.meta_description`: 상품 요약 1~2문장.
- `notice.item_name`: 식물 이름. `notice.model_name`: 상품명과 같은 값 또는 "상세설명 참조".
- `attributes`: 카테고리 속성 중 확실한 것만.

## 8. 검증 · 미리보기

1. `uv run scripts/validate.py products/<상품>` — 오류가 있으면 고치고 다시 실행한다.
2. `uv run scripts/render_preview.py products/<상품>` 후 미리보기를 연다.
3. 사용자에게 요약한다: 카테고리, 상품명, 판매가, 확인이 필요한 항목. 그리고 수정할 부분이 있는지 묻는다.
4. log.md에 작성 일시, 주요 판단 근거, 사용자 수정 요청과 반영 내용을 기록한다.

수정 요청을 받으면 해당 단계만 다시 하고 8단계를 반복한다.

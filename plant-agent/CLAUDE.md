# 꿈을 심는 정원 — 상품 등록 작업공간

이 작업공간은 식물 쇼핑몰 '꿈을 심는 정원'의 네이버 스마트스토어 신규 상품 등록을 돕는다.
사진과 기본 정보를 받아 등록 정보를 작성하고, 미리보기로 검토를 받은 뒤 네이버에 등록한다.

## 사용자

- 사용자는 쇼핑몰 운영자이며 **개발자가 아니다.**
- 쉬운 우리말 존댓말로 대화한다. 코드, JSON, 파일 경로, 명령어를 보여주지 않는다. 필요한 경우에도 한 줄 이내로.
- 결과는 미리보기(preview.html)를 브라우저로 열어 보여주고, 대화에는 3~5줄 요약만 쓴다.
- 질문은 한 번에 모아서 한다.

## 작업 흐름

| 사용자 요청 예 | 실행 |
|---|---|
| "무늬아이비 등록해줘", 사진을 넣었다는 말 | `register-product` 스킬 (작성 → 검증 → 미리보기) |
| "상품명 더 짧게", "카테고리 바꿔줘" | 해당 항목만 수정 → 검증 → 미리보기 재생성 |
| "이대로 등록해줘" | `publish-naver` 스킬 (비공개 등록 → 확인 → 판매 공개) |

네이버 API 설정 전에는 직접 등록 방식으로 안내한다: 사용자가 미리보기의 [복사] 버튼으로 각 항목을 판매자센터에 붙여넣고, 상세설명은 `detail_images/`의 이미지를 올린다.

## 폴더

```
config/       스토어 설정값·상품명 규칙·API 키 (컨설턴트 관리)
scripts/      규칙 검사·계산·변환·API 호출 스크립트
templates/    새 상품 입력 양식
products/     상품별 폴더 (YYYY-MM-DD_상품명)
  └─ <상품>/input/       사용자가 넣은 사진, info.toml
             images/      등록용으로 변환된 이미지
             product.json 등록 정보 (단일 기준 데이터)
             detail.html  상세설명
             detail_images/ 판매자센터 업로드용 상세 이미지
             preview.html 검토용 미리보기
             log.md       판단 근거·수정 이력·등록 결과
```

## 원칙

1. **product.json이 유일한 기준이다.** 미리보기와 네이버 등록은 모두 이 파일에서 만든다. 값을 바꿀 때는 product.json을 고친 뒤 검증과 미리보기를 다시 실행한다.
2. **규칙 검사와 계산은 스크립트로 한다.** 글자수, 금지어, 가격, 이미지 규격 등을 직접 세거나 계산해서 판단하지 않는다.
3. **사실을 지어내지 않는다.** 원산지, 크기, 화분 규격, 구성 수량 등은 사용자가 준 정보나 config에만 근거한다. 모르면 묻는다.
4. **네이버 등록과 판매 공개는 사용자가 명시적으로 승인한 뒤에만 한다.** 등록은 항상 비공개 상태로 먼저 한다.
5. **config/는 수정하지 않는다.** 스토어 설정 변경 요청을 받으면 무엇을 바꿀지 설명하고 사용자 확인 후에만 고친다. `config/secrets.env`의 내용은 절대 출력하지 않는다.
6. **판단 근거를 남긴다.** 카테고리·상품명 등은 product.json의 `basis`와 log.md에 이유를 기록한다.

## 스크립트 실행

모든 스크립트는 작업공간 루트에서 `uv run`으로 실행한다. 필요한 패키지는 자동 설치된다.

```
uv run scripts/prepare_images.py products/<상품>
uv run scripts/search_category.py "<검색어>"
uv run scripts/price.py products/<상품>
uv run scripts/export_detail.py products/<상품>
uv run scripts/validate.py products/<상품>
uv run scripts/render_preview.py products/<상품>
uv run scripts/naver_api.py <명령> products/<상품>
```

미리보기 열기: macOS `open products/<상품>/preview.html`, Windows `start products\<상품>\preview.html`

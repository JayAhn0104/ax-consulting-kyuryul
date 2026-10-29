# plant-agent

'꿈을 심는 정원' 네이버 스마트스토어 상품 등록 작업공간. 설계: [docs/01-식물-상품등록/03-설계.md](../docs/01-식물-상품등록/03-설계.md)

에이전트 지침은 [CLAUDE.md](CLAUDE.md), 작업 절차는 `.claude/skills/`에 있음. 이 문서는 컨설턴트용 설치·운영 안내.

## 설치 (클라이언트 PC)

1. Claude 데스크톱 앱 설치 및 로그인
2. [uv](https://docs.astral.sh/uv/) 설치 — 스크립트 실행과 패키지 설치를 자동 처리
3. 이 폴더를 클라이언트 PC에 복사하고 Claude 데스크톱 앱의 Claude Code에서 폴더 열기
4. `config/secrets.example.env`를 `config/secrets.env`로 복사하고 API 키 입력
5. `config/store.toml`의 빈 값 입력 (원산지 코드, A/S, 배송, 주소록 ID 등)
6. 연결 확인: `uv run scripts/naver_api.py token`, `uv run scripts/naver_api.py categories`

## 구성 요소 상태 (2026-10-29)

| 구성 요소 | 상태 | 비고 |
|---|---|---|
| prepare_images.py | 동작 확인 | 무늬아이비 사례 |
| price.py | 동작 확인 | 정가 미입력 시 임시 가격 규칙(매입가 × 2.74) 적용 |
| validate.py | 동작 확인 | 금지어·반복·태그 규칙 위반 사례로 검증 |
| render_preview.py | 동작 확인 | 항목별 복사 버튼 (API 설정 전 직접 등록용) |
| export_detail.py | 동작 확인 | 상세설명 → 780px 이미지. Chrome 또는 Edge 필요 |
| Codex 실행 | 미검증 | AGENTS.md가 CLAUDE.md와 스킬 파일을 참조 |
| search_category.py | 미검증 | 검색 API 키 필요 |
| naver_api.py | 일부 확인 | 등록 요청 생성(`payload`)만 확인. 인증·등록·공개는 실제 키로 시험 필요 |
| 대표이미지 생성 | 미구현 | 현재 클라이언트가 ChatGPT로 생성해 `input/`에 넣는 방식 |
| 엑셀 일괄등록 (대체 경로) | 미구현 | |

## 실제 등록 전 확인 사항

- 커머스API 애플리케이션 등록 및 자택 IP 등록
- `naver_api.py`의 요청 필드를 [커머스API 문서](https://apicenter.commerce.naver.com)와 대조 (특히 상품정보제공고시 `etc` 필드, 배송 정보, 공개 전환 방식)
- 첫 등록은 컨설턴트 입회 하에 진행하고, 판매자센터에서 결과 확인

# plant-agent

'꿈을 심는 정원' 네이버 스마트스토어 상품 등록 작업공간. 설계: [docs/01-식물-상품등록/03-설계.md](../docs/01-식물-상품등록/03-설계.md)

에이전트 지침은 [AGENTS.md](AGENTS.md) (Claude Code는 [CLAUDE.md](CLAUDE.md)를 통해 같은 파일을 읽음), 작업 절차는 `.claude/skills/`에 있음.
이 문서는 컨설턴트용 설치·운영 안내.

## 목표 사용 환경

- 클라이언트 PC: **Windows**
- 도구: **Codex 앱** (채팅 UI, 내 컴퓨터에서 실행). Claude 데스크톱 앱에서도 동일하게 동작
- 클라이언트는 채팅만 사용: 사진 첨부(또는 `사진함` 폴더) + 상품명·도매가 입력 → 미리보기 확인 → 수정 요청

## 설치 (클라이언트 Windows PC)

1. **Codex 앱** 설치 및 ChatGPT 계정 로그인 — Windows 지원 여부·설치 경로 확인 필요
2. **uv** 설치 (PowerShell):
   `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
3. 이 `plant-agent` 폴더만 클라이언트 PC에 복사 (예: `문서\plant-agent`). 컨설팅 문서(`docs/`, `data/`)는 복사하지 않음
4. 폴더에서 패키지 설치 (1회, 인터넷 필요): `uv sync`
5. `config/secrets.example.env`를 `config/secrets.env`로 복사하고 API 키 입력
6. `config/store.toml`의 빈 값 입력 (원산지 코드, A/S, 배송, 주소록 ID 등)
7. Codex 앱에서 `plant-agent` 폴더를 프로젝트로 추가
   - 상위 폴더가 아니라 반드시 `plant-agent` 자체를 프로젝트로 지정 (AGENTS.md 인식)
   - 승인 요청 빈도를 줄이도록 이 프로젝트의 실행 권한 설정 (설정 항목은 리허설에서 확인)
8. 연결 확인: `uv run scripts/naver_api.py token`, `uv run scripts/naver_api.py categories`
9. Edge 또는 Chrome 설치 확인 (상세 이미지 변환에 사용. Windows는 Edge 기본 설치)

## 리허설 체크리스트 (설치 전, 컨설턴트 PC)

- [ ] 채팅에 첨부한 사진의 파일 경로를 에이전트가 알 수 있는지 (불가 시 `사진함` 방식으로 운영)
- [ ] 한 상품 등록 중 승인 요청 횟수, 권한 설정으로 줄일 수 있는지
- [ ] `export_detail.py` 실행 시 브라우저 비정상 종료 여부 (Codex 실행 제한 환경)
- [ ] 미리보기가 브라우저에서 자동으로 열리는지
- [ ] 비개발자 말투의 요청("이거 등록해줘", "가격 좀 낮춰줘")에 지침대로 반응하는지

## 구성 요소 상태 (2026-10-29)

| 구성 요소 | 상태 | 비고 |
|---|---|---|
| new_product.py | 동작 확인 | 채팅 첨부 경로 복사 / 사진함 이동 두 방식 |
| prepare_images.py | 동작 확인 | 에이전트가 대표이미지·순서 지정 (`--rep`, `--order`) |
| price.py | 동작 확인 | 정가 미입력 시 임시 가격 규칙(매입가 × 2.74) 적용 |
| validate.py | 동작 확인 | 금지어·반복·태그 규칙 위반 사례로 검증 |
| render_preview.py | 동작 확인 | 항목별 복사 버튼. `--open`으로 브라우저 열기 |
| export_detail.py | 동작 확인 (macOS) | 상세설명 → 780px 이미지, 여백 기준 분할. Windows 미검증 |
| Windows 실행 | 미검증 | 한글 출력 UTF-8 처리, Edge 경로 반영 |
| Codex 앱 실행 | 미검증 | 리허설 필요 |
| search_category.py | 미검증 | 검색 API 키 필요 |
| naver_api.py | 일부 확인 | 등록 요청 생성(`payload`)만 확인. 인증·등록·공개는 실제 키로 시험 필요 |
| 대표이미지 생성 | 미구현 | 현재 클라이언트가 ChatGPT로 생성. 에이전트는 받은 사진 중에서 선택 |
| 엑셀 일괄등록 (대체 경로) | 미구현 | |

## 실제 등록 전 확인 사항

- 커머스API 애플리케이션 등록 및 자택 IP 등록
- `naver_api.py`의 요청 필드를 [커머스API 문서](https://apicenter.commerce.naver.com)와 대조 (특히 상품정보제공고시 `etc` 필드, 배송 정보, 공개 전환 방식)
- 첫 등록은 컨설턴트 입회 하에 진행하고, 판매자센터에서 결과 확인

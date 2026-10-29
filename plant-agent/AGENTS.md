# AGENTS.md

이 작업공간의 지침은 [CLAUDE.md](CLAUDE.md)에 있다. 작업 전에 반드시 CLAUDE.md를 읽고 그대로 따른다.

작업 절차는 다음 파일을 따른다.

| 사용자 요청 | 절차 파일 |
|---|---|
| 새 상품 등록 정보 작성, 수정 | [.claude/skills/register-product/SKILL.md](.claude/skills/register-product/SKILL.md) |
| 네이버 등록, 판매 공개 | [.claude/skills/publish-naver/SKILL.md](.claude/skills/publish-naver/SKILL.md) |

스크립트는 `uv run scripts/<이름>.py`로 실행한다. 첫 실행 시 패키지 설치를 위해 네트워크 접근이 필요하다.

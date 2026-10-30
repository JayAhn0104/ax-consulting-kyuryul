"""스크립트 공통 유틸: 경로, 설정·비밀값 로드, product.json 입출력."""

import json
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config"

# Windows에서 출력이 파이프로 전달될 때 기본 인코딩(cp949) 대신 UTF-8 사용
for stream in (sys.stdout, sys.stderr):
    stream.reconfigure(encoding="utf-8", errors="replace")


def load_toml(path: Path) -> dict:
    with open(path, "rb") as f:
        return tomllib.load(f)


def store_config() -> dict:
    """store.toml(공유 양식)에 store.local.toml(실제 스토어 값, 깃 제외)을 덮어쓴 설정."""
    cfg = load_toml(CONFIG / "store.toml")
    local = CONFIG / "store.local.toml"
    if local.exists():
        for section, values in load_toml(local).items():
            cfg.setdefault(section, {}).update(values)
    return cfg


def naming_rules() -> dict:
    return load_toml(CONFIG / "naming-rules.toml")


def secrets() -> dict:
    """config/secrets.env (KEY=VALUE 형식)를 읽는다. 없으면 빈 dict."""
    path = CONFIG / "secrets.env"
    values = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip()
    return values


def product_dir(arg: str) -> Path:
    path = Path(arg)
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    if not path.is_dir():
        sys.exit(f"상품 폴더를 찾을 수 없음: {path}")
    return path


def load_product(pdir: Path) -> dict:
    path = pdir / "product.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_product(pdir: Path, data: dict) -> None:
    path = pdir / "product.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_info(pdir: Path) -> dict:
    path = pdir / "input" / "info.toml"
    if not path.exists():
        sys.exit(f"입력 정보 파일이 없음: {path}")
    return load_toml(path)

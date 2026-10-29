"""새 상품 폴더를 만들고 사진을 input/으로 옮긴다.

사진 출처 (둘 중 하나):
- --photos 경로 ...  : 채팅 첨부 파일 등 경로를 아는 사진 (복사)
- 지정하지 않으면    : 사진함/ 폴더의 사진 전부 (이동)

결과: products/YYYY-MM-DD_<상품명>/input/ 에 사진, info.toml, 상품 폴더에 product.json 템플릿

사용: uv run scripts/new_product.py "<상품명>" [--photos 경로 ...]
"""

import argparse
import re
import shutil
import sys
from datetime import date
from pathlib import Path

from lib import ROOT

INBOX = ROOT / "사진함"
TEMPLATES = ROOT / "templates"
EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".heic"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("--photos", nargs="*", help="복사할 사진 경로 (채팅 첨부 등)")
    args = ap.parse_args()

    safe = re.sub(r'[\\/:*?"<>|\s]+', "_", args.name.strip())
    pdir = ROOT / "products" / f"{date.today().isoformat()}_{safe}"
    if pdir.exists():
        sys.exit(f"이미 같은 이름의 상품 폴더가 있음: {pdir.name}")

    if args.photos:
        sources = [Path(p) for p in args.photos]
        missing = [str(p) for p in sources if not p.is_file()]
        if missing:
            sys.exit("사진 파일을 찾을 수 없음: " + ", ".join(missing))
        move = False
    else:
        sources = sorted(p for p in INBOX.iterdir() if p.suffix.lower() in EXTS) if INBOX.exists() else []
        move = True
    if not sources:
        sys.exit("사진이 없음: 채팅에 첨부하거나 사진함 폴더에 넣어야 함")

    inp = pdir / "input"
    inp.mkdir(parents=True)
    for src in sources:
        (shutil.move if move else shutil.copy2)(str(src), inp / src.name)
    shutil.copy2(TEMPLATES / "info.template.toml", inp / "info.toml")
    shutil.copy2(TEMPLATES / "product.template.json", pdir / "product.json")

    print(f"상품 폴더 생성: products/{pdir.name}")
    print(f"사진 {len(sources)}장 {'이동(사진함)' if move else '복사'}: " + ", ".join(s.name for s in sources))


if __name__ == "__main__":
    main()

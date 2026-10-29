# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow"]
# ///
"""detail.html을 상세 이미지(PNG)로 변환한다. 판매자센터에 이미지로 올리는 방식용.

- 가로폭·분할 높이는 config/store.toml [detail] 설정을 따름
- 결과: <상품폴더>/detail_images/detail-1.png, detail-2.png ...
- Chrome 또는 Edge 필요 (환경변수 CHROME_PATH로 경로 지정 가능)

사용: uv run scripts/export_detail.py <상품폴더>
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageChops

from lib import load_product, product_dir, save_product, store_config

CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]
MAX_RENDER_HEIGHT = 16000


def find_browser():
    if os.environ.get("CHROME_PATH"):
        return os.environ["CHROME_PATH"]
    for path in CANDIDATES:
        if Path(path).exists():
            return path
    for name in ("google-chrome", "chromium", "chrome", "msedge"):
        if shutil.which(name):
            return shutil.which(name)
    sys.exit("Chrome 또는 Edge를 찾을 수 없음. 설치하거나 CHROME_PATH를 지정해야 함.")


def trim_bottom(img):
    """하단의 빈 배경을 잘라낸다."""
    bg = Image.new(img.mode, img.size, img.getpixel((0, img.height - 1)))
    box = ImageChops.difference(img, bg).getbbox()
    return img.crop((0, 0, img.width, min(img.height, box[3] + 40))) if box else img


def cut_points(img, split, search=1200):
    """split 높이 이하에서 가장 가까운 '전부 흰 행'을 찾아 분할 지점으로 쓴다. 사진이 잘리지 않게 하기 위함."""
    gray = img.convert("L")
    points, top = [], 0
    while img.height - top > split:
        target = top + split
        cut = target
        for y in range(target, max(top + 1, target - search), -1):
            if gray.crop((0, y, img.width, y + 1)).getextrema()[0] >= 245:
                cut = y
                break
        points.append(cut)
        top = cut
    return [0, *points, img.height]


def main():
    pdir = product_dir(sys.argv[1])
    cfg = store_config()["detail"]
    width, split = cfg["width"], cfg["split_height"]
    data = load_product(pdir)
    fragment = (pdir / data.get("detail", {}).get("file", "detail.html")).read_text(encoding="utf-8")

    page = pdir / "_detail_render.html"
    page.write_text(
        f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><style>'
        f'html,body{{margin:0;background:#fff;width:{width}px;}}'
        f'body{{font-family:"Apple SD Gothic Neo","Malgun Gothic","Noto Sans KR",sans-serif;}}'
        f'img{{max-width:100%;}}</style></head><body>{fragment}</body></html>',
        encoding="utf-8")
    shot = pdir / "_detail_full.png"
    subprocess.run([find_browser(), "--headless=new", "--disable-gpu", "--hide-scrollbars",
                    "--force-device-scale-factor=1", f"--window-size={width},{MAX_RENDER_HEIGHT}",
                    f"--screenshot={shot}", page.as_uri()],
                   check=True, capture_output=True)

    img = trim_bottom(Image.open(shot).convert("RGB"))
    out = pdir / "detail_images"
    out.mkdir(exist_ok=True)
    for old in out.glob("detail-*.png"):
        old.unlink()
    files = []
    points = cut_points(img, split)
    for i, (top, bottom) in enumerate(zip(points, points[1:]), 1):
        name = f"detail_images/detail-{i}.png"
        img.crop((0, top, width, bottom)).save(pdir / name)
        files.append(name)
    page.unlink()
    shot.unlink()

    data.setdefault("detail", {})["images"] = files
    save_product(pdir, data)
    print(f"상세 이미지 {len(files)}장 생성 ({width}×{img.height}px): {out}")


if __name__ == "__main__":
    main()

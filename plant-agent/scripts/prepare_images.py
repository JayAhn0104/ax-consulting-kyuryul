"""input/의 사진을 등록용 규격으로 변환해 images/에 저장하고 product.json에 기록한다.

- 대표이미지: --rep로 지정한 사진. 없으면 파일명이 '대표' 또는 '썸네일'로 시작하는 사진
- 추가이미지: 나머지 사진 (최대 9장). --order로 순서 지정, 없으면 파일명 순
- JPEG 변환, 긴 변 최대 1000px

사용: uv run scripts/prepare_images.py <상품폴더> [--rep 파일명] [--order 파일명,...] [--basis 근거]
"""

import argparse
import sys

from PIL import Image, ImageOps

from lib import load_product, product_dir, save_product

EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".heic"}
REP_PREFIXES = ("대표", "썸네일")
MAX_SIDE = 1000
MIN_SIDE = 640  # 네이버 공식 권장 규격
MAX_OPTIONAL = 9


def convert(src, dst):
    img = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
    if max(img.size) > MAX_SIDE:
        img.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
    img.save(dst, "JPEG", quality=90)
    return img.size


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("product")
    ap.add_argument("--rep", help="대표이미지로 쓸 input/ 안의 파일명")
    ap.add_argument("--order", help="추가이미지 순서 (쉼표로 구분한 파일명)")
    ap.add_argument("--basis", default="", help="대표이미지·순서 선택 근거")
    args = ap.parse_args()

    pdir = product_dir(args.product)
    photos = sorted(p for p in (pdir / "input").iterdir() if p.suffix.lower() in EXTS)
    by_name = {p.name: p for p in photos}
    for name in [args.rep, *(args.order.split(",") if args.order else [])]:
        if name and name.strip() not in by_name:
            sys.exit(f"input/에 없는 파일: {name}")

    if args.rep:
        reps = [by_name[args.rep]]
    else:
        reps = [p for p in photos if p.stem.startswith(REP_PREFIXES)]
    optional = [p for p in photos if p not in reps[:1]]
    if args.order:
        ordered = [by_name[n.strip()] for n in args.order.split(",")]
        optional = [p for p in ordered if p in optional] + [p for p in optional if p not in ordered]

    out = pdir / "images"
    out.mkdir(exist_ok=True)
    notes = []
    result = {"representative": None, "optional": [], "basis": args.basis, "notes": notes}

    if not reps:
        notes.append("대표이미지 없음: --rep로 지정하거나 파일명이 '대표'·'썸네일'로 시작하는 사진 필요")
    else:
        if len(reps) > 1:
            notes.append(f"대표이미지 후보가 {len(reps)}장: {reps[0].name} 사용")
        size = convert(reps[0], out / "rep.jpg")
        result["representative"] = {"file": "images/rep.jpg", "source": reps[0].name, "size": size}

    if len(optional) > MAX_OPTIONAL:
        notes.append(f"추가이미지 {len(optional)}장 중 {MAX_OPTIONAL}장만 사용")
    for i, src in enumerate(optional[:MAX_OPTIONAL], 1):
        size = convert(src, out / f"add-{i}.jpg")
        result["optional"].append({"file": f"images/add-{i}.jpg", "source": src.name, "size": size})

    for item in [result["representative"], *result["optional"]]:
        if not item:
            continue
        w, h = item["size"]
        if w != h:
            notes.append(f"{item['source']}: 정사각형 아님 ({w}×{h})")
        if min(w, h) < MIN_SIDE:
            notes.append(f"{item['source']}: 권장 규격 640×640 미만 ({w}×{h})")

    data = load_product(pdir)
    data["images"] = result
    save_product(pdir, data)

    print(f"대표이미지: {result['representative']['source'] if result['representative'] else '없음'}")
    print(f"추가이미지: {len(result['optional'])}장")
    for n in notes:
        print(f"- {n}")


if __name__ == "__main__":
    main()

# /// script
# requires-python = ">=3.11"
# ///
"""판매가를 계산해 product.json에 기록한다.

정가(네이버 '판매가' 입력값)와 기본할인율로 실판매가를 계산함.
정가는 info.toml의 list_price를 우선 사용하고, 없으면 스토어 설정의 임시 가격 규칙
(매입가 × provisional_multiplier)을 적용함. 임시 규칙 적용 시 provisional=true로 표시.

사용: uv run scripts/price.py <상품폴더>
"""

import sys

from lib import load_info, load_product, product_dir, save_product, store_config


def main():
    pdir = product_dir(sys.argv[1])
    info = load_info(pdir)
    cfg = store_config()["price"]
    unit = cfg["unit"]
    rate = cfg["discount_rate"]
    cost = info.get("cost")

    list_price = info.get("list_price")
    provisional = False
    if list_price:
        basis = "클라이언트 입력 정가 + 기본할인율"
    elif cost:
        step = cfg["list_price_round"]
        list_price = round(cost * cfg["provisional_multiplier"] / step) * step
        provisional = True
        basis = f"임시 가격 규칙: 매입가 × {cfg['provisional_multiplier']} ({step}원 단위 반올림) + 기본할인율"
    else:
        sys.exit("정가와 매입가가 모두 없음. 둘 중 하나는 있어야 함.")
    if list_price % unit:
        sys.exit(f"정가는 {unit}원 단위여야 함: {list_price}")

    discount = int(list_price * rate) // unit * unit
    sale = list_price - discount

    price = {
        "list": list_price,
        "discount_rate": rate,
        "discount": discount,
        "sale": sale,
        "cost": cost,
        "markup": round(sale / cost, 2) if cost else None,
        "provisional": provisional,
        "basis": basis,
    }
    data = load_product(pdir)
    data["price"] = price
    save_product(pdir, data)

    print(f"정가 {list_price:,}원 → 기본할인 {rate:.0%} ({discount:,}원) → 판매가 {sale:,}원")
    if provisional:
        print("임시 가격 규칙 적용: 클라이언트 확인 필요")
    if cost:
        print(f"매입가 {cost:,}원, 판매가/매입가 {price['markup']}배")


if __name__ == "__main__":
    main()

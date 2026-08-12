#!/usr/bin/env python3
"""Calculate Visa Kita contribution economics from normalized CSV data."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_row(path: Path, sku: str) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row.get("sku") == sku:
                return row
    raise SystemExit(f"SKU not found in {path.name}: {sku}")


def rupiah(value: float) -> str:
    return f"Rp{value:,.0f}".replace(",", ".")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sku", required=True)
    parser.add_argument("--cpl", type=float, default=0, help="Cost per lead in IDR")
    parser.add_argument("--conversion", type=float, default=1, help="Paid conversion, 0 < value <= 1")
    parser.add_argument("--price", type=float, help="Override draft price in IDR")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if not 0 < args.conversion <= 1:
        parser.error("--conversion must be greater than 0 and at most 1")
    if args.cpl < 0:
        parser.error("--cpl cannot be negative")

    pricing = load_row(ROOT / "data" / "active-pricing.csv", args.sku)
    costs = load_row(ROOT / "data" / "unit-costs.csv", args.sku)
    price = args.price if args.price is not None else float(pricing["price_idr"])
    payment = price * float(costs["payment_rate"])
    variable = sum(
        float(costs[key])
        for key in (
            "government_fee_idr",
            "levy_idr",
            "benefit_cost_idr",
            "cs_cost_idr",
            "operations_cost_idr",
        )
    ) + payment
    pre_ad = price - variable
    cpa = args.cpl / args.conversion
    post_ad = pre_ad - cpa
    result = {
        "sku": args.sku,
        "price_status": pricing["status"],
        "revenue_idr": round(price, 2),
        "payment_fee_idr": round(payment, 2),
        "variable_cost_idr": round(variable, 2),
        "contribution_before_acquisition_idr": round(pre_ad, 2),
        "pre_ad_margin": round(pre_ad / price, 4),
        "cpa_idr": round(cpa, 2),
        "contribution_after_acquisition_idr": round(post_ad, 2),
        "post_ad_margin": round(post_ad / price, 4),
        "break_even_conversion": None if pre_ad <= 0 else round(args.cpl / pre_ad, 4),
        "max_cpl_at_given_conversion_idr": round(max(pre_ad, 0) * args.conversion, 2),
    }
    if args.json:
        print(json.dumps(result, indent=2))
        return
    for key, value in result.items():
        if key.endswith("_idr") and value is not None:
            print(f"{key}: {rupiah(value)}")
        elif key.endswith("margin") or key.endswith("conversion"):
            print(f"{key}: {'n/a' if value is None else f'{value:.2%}'}")
        else:
            print(f"{key}: {value}")


if __name__ == "__main__":
    main()

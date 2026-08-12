#!/usr/bin/env python3
"""Validate normalized Visa Kita knowledge invariants."""

from __future__ import annotations

import csv
import re
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALID_PRICE = {"draft", "active", "retired", "needs-approval"}
VALID_BENEFIT = {"confirmed", "partner-dependent", "planned", "unverified", "retired"}
NON_PORTABLE_MARKERS = (
    "." + "extra/",
    "/" + "Users/",
    "~" + "/",
    "$" + "HOME",
    "${" + "HOME}",
)


def rows(name: str) -> list[dict[str, str]]:
    with (ROOT / "data" / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    errors: list[str] = []
    prices = rows("active-pricing.csv")
    costs = rows("unit-costs.csv")
    benefits = rows("benefits.csv")
    cost_skus = {row["sku"] for row in costs}

    duplicate_active = [
        sku for sku, count in Counter(row["sku"] for row in prices if row["status"] == "active").items() if count > 1
    ]
    if duplicate_active:
        errors.append(f"multiple active prices: {', '.join(duplicate_active)}")
    for row in prices:
        if row["status"] not in VALID_PRICE:
            errors.append(f"invalid price status for {row['sku']}: {row['status']}")
        if row["sku"] not in cost_skus:
            errors.append(f"missing unit costs for {row['sku']}")
        if row["status"] == "active" and not all(row[key] for key in ("effective_date", "approver")):
            errors.append(f"active price lacks approval metadata: {row['sku']}")
    for row in benefits:
        if row["status"] not in VALID_BENEFIT:
            errors.append(f"invalid benefit status for {row['benefit']}: {row['status']}")

    source_text = (ROOT / "references" / "source-register.md").read_text(encoding="utf-8")
    known_sources = set(re.findall(r"\| ([A-Z][A-Z0-9-]+) \|", source_text))
    for line in source_text.splitlines():
        if line.startswith("| INT-"):
            bundled_and_origin = re.findall(r"`([^`]+)`", line)
            for bundled in bundled_and_origin[:-1]:
                if "/" in bundled and not (ROOT / bundled).is_file():
                    errors.append(f"missing bundled runtime source: {bundled}")
    for path in ROOT.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".md", ".csv", ".json", ".yaml", ".yml", ".py"}:
            text = path.read_text(encoding="utf-8")
            for marker in NON_PORTABLE_MARKERS:
                if marker in text:
                    errors.append(f"non-portable path marker {marker!r} in {path.relative_to(ROOT)}")
    for filename in ("products.csv", "active-pricing.csv", "unit-costs.csv", "benefits.csv", "competitors.csv", "assumptions.csv"):
        for row in rows(filename):
            source = row.get("source_id", "")
            if source and source not in known_sources:
                errors.append(f"unknown source {source} in {filename}")

    if errors:
        print("Knowledge validation failed:")
        for error in errors:
            print(f"- {error}")
        sys.exit(1)
    print(f"Knowledge validation passed: {len(prices)} price rows, {len(benefits)} benefits, {len(known_sources)} sources")


if __name__ == "__main__":
    main()

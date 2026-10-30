#!/usr/bin/env python3
"""Verify and, when required, reconcile calorie and macro targets."""

from __future__ import annotations

import argparse
import json
from decimal import Decimal, ROUND_HALF_UP


def q(value: Decimal, places: str = "0.1") -> float:
    return float(value.quantize(Decimal(places), rounding=ROUND_HALF_UP))


def reconcile(calories: Decimal, protein: Decimal, carbs: Decimal, fat: Decimal, carb_definition: str) -> dict:
    if min(calories, protein, carbs, fat) < 0 or calories == 0:
        raise ValueError("Calories must be positive and macros cannot be negative")
    macro_kcal = protein * 4 + carbs * 4 + fat * 9
    gap = abs(macro_kcal - calories) / calories
    original = {
        "calories": q(calories),
        "protein_g": q(protein),
        "carbs_g": q(carbs),
        "fat_g": q(fat),
        "macro_kcal": q(macro_kcal),
        "gap_percent": q(gap * 100),
    }

    adjusted = False
    final_carbs, final_fat = carbs, fat
    if gap > Decimal("0.05"):
        remaining = calories - protein * 4
        if remaining <= 0:
            raise ValueError("Protein calories meet or exceed the calorie target")
        carb_kcal = carbs * 4
        fat_kcal = fat * 9
        split_total = carb_kcal + fat_kcal
        if split_total <= 0:
            raise ValueError("Cannot preserve a zero carbohydrate-to-fat ratio")
        final_carb_kcal = remaining * carb_kcal / split_total
        final_fat_kcal = remaining - final_carb_kcal
        final_carbs = final_carb_kcal / 4
        final_fat = final_fat_kcal / 9
        adjusted = True

    final = {
        "calories": q(calories),
        "protein_g": q(protein),
        "carbs_g": q(final_carbs),
        "fat_g": q(final_fat),
        "carb_definition": carb_definition,
    }
    ranges = {
        "calories": [q(calories * Decimal("0.95"), "1"), q(calories * Decimal("1.05"), "1")],
        "protein_g": [q(protein), None],
        "carbs_g": [q(final_carbs * Decimal("0.90"), "1"), q(final_carbs * Decimal("1.10"), "1")],
        "fat_g": [q(final_fat * Decimal("0.90"), "1"), q(final_fat * Decimal("1.10"), "1")],
    }
    return {"adjusted": adjusted, "original": original, "final": final, "accepted_ranges": ranges}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--calories", required=True)
    parser.add_argument("--protein", required=True)
    parser.add_argument("--carbs", required=True)
    parser.add_argument("--fat", required=True)
    parser.add_argument("--carb-definition", choices=("net", "total"), required=True)
    args = parser.parse_args()
    result = reconcile(
        *(Decimal(value) for value in (args.calories, args.protein, args.carbs, args.fat)),
        args.carb_definition,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()


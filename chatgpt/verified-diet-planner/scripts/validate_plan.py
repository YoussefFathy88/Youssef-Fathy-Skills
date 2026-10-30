#!/usr/bin/env python3
"""Calculate displayed rows and validate a diet plan against the approved catalog."""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


METRICS = ("kcal", "protein", "carbs", "fat")
COLUMNS = {
    "kcal": "kcal_per_100g",
    "protein": "protein_g_per_100g",
    "carbs": "total_carbs_g_per_100g",
    "fat": "fat_g_per_100g",
}


def whole(value: Decimal) -> int:
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def catalog() -> dict[str, dict[str, str]]:
    path = Path(__file__).resolve().parent.parent / "references" / "approved-ingredients.csv"
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    result = {row["key"]: row for row in rows}
    if len(result) != len(rows):
        raise ValueError("Duplicate key in approved ingredient catalog")
    return result


def passes(value: int, bounds: list[int | None]) -> bool:
    low, high = bounds
    return value >= low and (high is None or value <= high)


def validate(plan: dict) -> dict:
    foods = catalog()
    carb_definition = plan.get("carb_definition")
    if carb_definition not in {"net", "total"}:
        raise ValueError("carb_definition must be net or total")
    shopping: defaultdict[str, Decimal] = defaultdict(Decimal)
    errors: list[str] = []
    warnings: set[str] = set()
    days = []

    for day in plan.get("days", []):
        day_total = {metric: 0 for metric in METRICS}
        meals = []
        for meal in day.get("meals", []):
            meal_total = {metric: 0 for metric in METRICS}
            rows = []
            for item in meal.get("ingredients", []):
                key = item.get("key")
                if key not in foods:
                    errors.append(f"{day.get('name')} / {meal.get('name')}: unapproved key {key}")
                    continue
                grams = Decimal(str(item.get("grams", 0)))
                if grams <= 0:
                    errors.append(f"{day.get('name')} / {meal.get('name')} / {key}: grams must be positive")
                    continue
                food = foods[key]
                row = {"key": key, "grams": float(grams), "state": food["state"]}
                for metric in METRICS:
                    per100 = Decimal(food[COLUMNS[metric]])
                    if metric == "carbs" and carb_definition == "net":
                        per100 -= Decimal(food["fiber_g_per_100g"])
                    row[metric] = whole(per100 * grams / 100)
                    meal_total[metric] += row[metric]
                shopping[key] += grams
                rows.append(row)
                if food["fiber_missing"].lower() == "true":
                    warnings.add(f"Missing fiber treated as 0: {key}")
                kcal = Decimal(food["kcal_per_100g"])
                if kcal > 50:
                    macro_kcal = (
                        Decimal(food["protein_g_per_100g"]) * 4
                        + Decimal(food["total_carbs_g_per_100g"]) * 4
                        + Decimal(food["fat_g_per_100g"]) * 9
                    )
                    if abs(kcal - macro_kcal) / kcal > Decimal("0.15"):
                        warnings.add(f"Energy sanity check exceeds 15%: {key}")
            for metric in METRICS:
                day_total[metric] += meal_total[metric]
            meals.append({"name": meal.get("name"), "dish": meal.get("dish"), "rows": rows, "total": meal_total})
        checks = {metric: passes(day_total[metric], plan["ranges"][metric]) for metric in METRICS}
        days.append({
            "name": day.get("name"),
            "meals": meals,
            "total": day_total,
            "difference": {metric: day_total[metric] - plan["targets"][metric] for metric in METRICS},
            "checks": checks,
            "status": "OK" if all(checks.values()) else "CLOSE",
        })

    if not days:
        errors.append("Plan has no days")
    valid = not errors and all(day["status"] == "OK" for day in days)
    return {
        "carb_definition": carb_definition,
        "days": days,
        "shopping_grams": {key: float(value) for key, value in sorted(shopping.items())},
        "warnings": sorted(warnings),
        "errors": errors,
        "valid": valid,
    }


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python validate_plan.py PLAN.json")
    plan = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    result = validate(plan)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    raise SystemExit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()


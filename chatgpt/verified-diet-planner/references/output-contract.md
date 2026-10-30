# Structured plan output and validator input

## Output order

Compute the entire plan before displaying it. Use localized headings and the following order.

### 1. Plan summary

- Goal: current weight to target weight and speed
- Plan length and meals per day
- Carbohydrate definition: net or total
- MyFitnessPal connection status
- Target-setting method and any macro reconciliation

| Item | Daily target | Accepted range |
|---|---:|---:|
| Calories kcal | value | value |
| Protein g | value | target or more |
| Carbs g | value | value |
| Fat g | value | value |

### 2. Days

For every day, show an at-a-glance table:

| Meal | Dish | kcal | Protein g | Carbs g | Fat g |
|---|---|---:|---:|---:|---:|

For every meal, show:

| Ingredient | Amount and state | kcal | Protein g | Carbs g | Fat g |
|---|---:|---:|---:|---:|---:|

End with the displayed meal total and no more than 2 short preparation steps. Include a raw-weighing reminder.

After each day, show target, plan, difference, and `OK` or `CLOSE`. State the exact missed condition for CLOSE.

For plans longer than 3 days, display 3 days per response. End non-final parts with a localized request for `NEXT`. Later messages only display already-calculated results.

### 3. Plan overview

| Day | kcal | Protein g | Carbs g | Fat g | Status |
|---|---:|---:|---:|---:|---|

### 4. MyFitnessPal recommendations

Show no more than five recipes from the single allowed recipe-search call:

| Preferred-food match | Recipe |
|---|---|

Add one localized sentence telling the client to check the recipe cards or images for full details. Do not add time, calorie, or macro columns and do not repeat `Not exposed by connector`. Exclude all recommendation values from plan totals. If the call returns no recipes, replace the table with one localized sentence and do not call the connector again.

### 5. Shopping list

Group protein, carbohydrate foods, vegetables and fruit, fats, and other items. Show total plan grams using the validator output.

### 6. Ingredient sources

| Ingredient | Exact USDA name | FDC ID | Source | State | Reference quantity | kcal | Protein | Carbs | Fat | Fiber | Record |
|---|---|---|---|---|---|---:|---:|---:|---:|---:|---|

Write `100 g` explicitly in every reference-quantity cell rather than leaving the serving basis implicit. For countable foods, add a familiar unit equivalence when it is supported and useful. For the approved whole-egg row, display `100 g edible portion (approximately 2 large eggs)` so the 148 kcal value is not mistaken for the value of one egg.

### 7. Quality check and notes

Show pass/fail for connector, calculation script, ingredient IDs, day statuses, carbohydrate definition, estimated items, missing fiber, and halal verification where applicable. End with a general-guidance-not-medical-advice statement.

## Validator input JSON

Create this as a temporary file and run `scripts/validate_plan.py`:

```json
{
  "carb_definition": "net",
  "targets": {"kcal": 3100, "protein": 140, "carbs": 397, "fat": 106},
  "ranges": {
    "kcal": [2945, 3255],
    "protein": [140, null],
    "carbs": [357, 437],
    "fat": [95, 117]
  },
  "days": [
    {
      "name": "Day 1",
      "meals": [
        {
          "name": "Breakfast",
          "dish": "Eggs, oats, and banana",
          "ingredients": [
            {"key": "egg", "grams": 150},
            {"key": "oats", "grams": 80},
            {"key": "banana", "grams": 180}
          ]
        }
      ]
    }
  ]
}
```

Use catalog keys exactly. The validator calculates row values, meal and day totals, differences, statuses, warnings, and shopping totals. A nonzero exit means the plan is not ready.

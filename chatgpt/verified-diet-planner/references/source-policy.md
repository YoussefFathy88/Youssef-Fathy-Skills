# Nutrient sources and approved catalog policy

## Trusted source order

1. USDA FoodData Central Foundation Foods
2. USDA FoodData Central SR Legacy
3. USDA Branded Foods only for an exact packaged product named by the client
4. FAO/INFOODS or an official national table for a local dish
5. A recipe assembled from verified ingredient records and labeled `ESTIMATED FROM RECIPE`

Do not use blogs, search-result snippets, crowdsourced trackers, or AI memory for plan nutrient values.

## Bundled approved catalog

`approved-ingredients.csv` is a reviewed cache of common ingredients. It records:

- internal key and display name;
- exact USDA name and FDC ID;
- Foundation or SR Legacy source;
- raw or cooked state;
- kcal, protein, total carbohydrate, fat, and fiber per 100 g;
- whether fiber was absent and treated as zero;
- energy nutrient ID and dataset release;
- verification date and direct USDA record URL.

Use an exact catalog row without reopening the web record. This is the main speed optimization. Do not reuse a row for a different food form, cut, cooking state, brand, or draining state.

For net carbohydrates:

```text
net carbs = total carbs − fiber
```

If `fiber_missing` is true, use zero and disclose it.

## Adding a non-catalog ingredient

Open an official record and capture the same fields as the catalog. Prefer nutrient 1008 for kcal when present. For Foundation records without 1008, use nutrient 2047 consistently with the catalog and record that choice. Do not mix energy definitions for the same ingredient.

For each food over 50 kcal per 100 g, compare energy with:

```text
protein × 4 + total carbohydrate × 4 + fat × 9
```

If the difference exceeds 15%, reopen the record, verify the selected nutrients and state, and disclose the discrepancy.

## Official reference links

- FoodData Central: https://fdc.nal.usda.gov/
- Download releases: https://fdc.nal.usda.gov/download-datasets/
- API guide: https://fdc.nal.usda.gov/api-guide/
- Data-type documentation: https://fdc.nal.usda.gov/data-documentation/
- Foundation Foods CSV April 2026: https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_foundation_food_csv_2026-04-30.zip
- SR Legacy CSV April 2018: https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_sr_legacy_food_csv_2018-04.zip
- FAO/INFOODS tables directory: https://www.fao.org/infoods/infoods/tables-and-databases/en/
- FAO/INFOODS Middle East directory: https://www.fao.org/infoods/infoods/tables-and-databases/middle-east/en/

The Middle East directory lists `Food Composition Tables for Egypt - Nutrition Institute (1996)`. If the actual table cannot be opened, do not copy secondary values attributed to it; build the dish from verified ingredients.

## Catalog maintenance

The bundled Foundation snapshot is April 2026 and the verification date is 2026-09-19. Update the catalog as a maintenance task after reviewing a newer official release. Do not interrupt an ordinary plan to search for updates when every selected food has an exact approved match.


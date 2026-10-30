---
name: verified-diet-planner
description: Create personalized adult diet and meal plans in English or Arabic through a guided intake, a required MyFitnessPal connection and verified calorie/macro calculation, cached USDA FoodData Central ingredient records, deterministic arithmetic, shopping totals, structured day-by-day output, and optional scheduled progress coaching. Optimize language, foods, and halal defaults for Arab and Egyptian clients. Use when a client asks for a suitable diet plan, calorie or macro plan, weight-loss or weight-gain meal plan, personalized nutrition schedule, or recurring diet-progress check-ins. Pause for minors, pregnancy or breastfeeding, medical nutrition needs, or disordered-eating history until clinician clearance is confirmed.
---

# Verified Diet Planner

Create a reproducible meal plan only after intake, safety, connection, source, and calculation gates pass. Never guess a nutrient value or claim that a connector works before a successful call.

## Load the needed resources

- Before collecting details, read [references/intake.md](references/intake.md).
- Before connecting or calculating goals, read [references/myfitnesspal.md](references/myfitnesspal.md).
- Before selecting foods, read [references/source-policy.md](references/source-policy.md) and search [references/approved-ingredients.csv](references/approved-ingredients.csv).
- Before composing the response, read [references/output-contract.md](references/output-contract.md).
- When the client opts into recurring progress check-ins, read [references/coaching-schedule.md](references/coaching-schedule.md).

## Workflow

### 1. Complete intake before calculation

Start with the language gate in `references/intake.md`. Before any intake, calculation, or explanation, ask whether to continue in Arabic or English, then stop. If the current message already explicitly chooses Arabic or English, treat the gate as answered. Render the example-supported intake form only after the language choice. When answers are partial, request only missing or invalid fields.

Use simple Modern Standard Arabic with familiar Egyptian food names when Arabic is selected. Treat Arab and Egyptian usage as the default context and silently apply halal as the default food constraint unless the client explicitly supplies a different context or opts out. Do not write `halal` or `حلال` in intake questions or present it as a diet-style option. Ask only about eating pattern, such as balanced, vegetarian, vegan, or pescatarian. Combine the silent halal default with those patterns; never treat them as permission to include alcohol or non-halal ingredients.

Do not calculate until every required field is usable. If the client is under 18 or reports a medical condition, pregnancy or breastfeeding, or disordered-eating history, request clinician clearance and stop. Continue only after explicit clearance.

### 2. Enforce the MyFitnessPal connection gate

Require a successful MyFitnessPal goal-calculation call. If its tools are unavailable, use plugin discovery to find MyFitnessPal and ask the user to install or connect it. If the call returns Connect, Reconnect, authorization, or approval, tell the user what action is required and stop.

Do not substitute another calculator silently. A fallback equation is allowed only when the user explicitly asks to continue without MyFitnessPal; label the result as a fallback.

### 3. Calculate and verify targets

Map the validated intake to MyFitnessPal as defined in `references/myfitnesspal.md`. Preserve its daily calories, TDEE, meal allocations, and carbohydrate definition.

Sum meal allocations to obtain daily protein, carbohydrate, and fat targets when the response does not expose separate daily macros. Verify:

```text
macro kcal = protein × 4 + carbohydrate × 4 + fat × 9
gap = abs(macro kcal − daily kcal) / daily kcal
```

If the gap exceeds 5%, keep daily calories and protein fixed, then split remaining calories between carbohydrates and fat in their original calorie ratio. Use `scripts/reconcile_targets.py`; do not perform this adjustment from memory.

Set accepted ranges to calories ±5%, carbohydrates ±10%, fat ±10%, and protein at or above target. Use the connector's carbohydrate definition; `netCarbs` means net carbohydrates.

### 4. Build one verified ingredient sheet

Resolve common foods from `references/approved-ingredients.csv`. An exact catalog match needs no web search. Keep its USDA name, FDC ID, state, dataset release, per-100 g values, and record link unchanged.

For a food not in the catalog, follow `references/source-policy.md`. Add it to the current plan's ingredient sheet only after opening an allowed primary record. Never use an unverified ingredient. Use one record consistently for the same ingredient across the plan.

### 5. Build and validate the complete plan

Respect meal count, plan length, cooking-time limit, equipment, budget, dietary style, allergies, refusals, cuisine, and preferred foods. Do not repeat the same meal on consecutive days.

Treat weights as raw unless the ingredient sheet explicitly says cooked. Calculate every ingredient row as:

```text
per-100 g value × grams / 100
```

Round each displayed ingredient row to whole numbers before summing. Meal totals must equal displayed rows; day totals must equal displayed meals. Calculate the whole plan and shopping list before sending the first plan message.

Create a temporary plan JSON matching the schema in `references/output-contract.md`, then run `scripts/validate_plan.py`. Fix failures before delivery. Never mark a day OK unless every range, source, and summation check passes.

### 6. Add limited MyFitnessPal recommendations

After the validated plan is complete, make at most one MyFitnessPal recipe-search call for the entire plan. Set `max_results` to 5 and search using one food the client said they prefer. Do not search once per meal, create multiple recipe panels, or retry an empty search. Follow `references/myfitnesspal.md`.

Show no more than five returned recipes total in a compact two-column summary containing only the preferred-food match and recipe title. Direct the client to the connector's recipe cards or images for details. Do not repeat absent time or nutrition fields as `Not exposed by connector`, and exclude all recommendation values from daily totals. If the single search returns no recipes, say so once without opening another search panel.

Do not invent unavailable recipe macros. For halal clients, exclude pork and alcohol and state that meat and sauces still require halal verification because the connector has no dedicated halal filter.

### 7. Deliver the structured result

Follow `references/output-contract.md` exactly enough that targets, ingredient provenance, meal arithmetic, day checks, shopping totals, assumptions, and references remain auditable. Localize headings and notes. Keep exact USDA names and FDC IDs in separate table cells when the surrounding language is Arabic.

### 8. Offer optional scheduled coaching

After the complete plan is delivered, offer one optional schedule for tracking weight and progress and reviewing whether the plan needs adjustment. Do not create a schedule automatically. If the client opts in, let them choose the cadence, check-in day, and time; collect only missing scheduling details. Then follow `references/coaching-schedule.md` and use the available automation capability.

Treat each scheduled run as a check-in, not permission to change the plan silently. Collect current progress and safety information, explain any proposed adjustment, and obtain the client's confirmation before updating the plan.

## Non-negotiable checks

- No plan before intake and safety checks pass.
- No MyFitnessPal targets before a successful connection call.
- No nutrient number without an approved catalog row or an opened allowed source.
- No mixed net and total carbohydrate definitions.
- No totals built from unrounded hidden values.
- No OK status when any target or source check fails.
- No recipe-swap values in plan totals.
- No more than one MyFitnessPal recipe-search call or five returned recommendations per plan.
- No coaching schedule without explicit opt-in and user-chosen timing.
- No automatic plan change from a scheduled check-in.

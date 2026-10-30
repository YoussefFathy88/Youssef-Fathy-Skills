# MyFitnessPal connection, goals, and recipes

## Connection gate

1. Look for the MyFitnessPal goal-calculation capability.
2. If absent, use plugin management to search for `MyFitnessPal`.
3. Ask the client to install or connect the returned plugin and stop.
4. If a tool call requests Connect, Reconnect, authorization, or approval, show that requirement and stop.
5. Treat the connector as available only after a harmless goal-calculation call succeeds.

Never claim the connector is unavailable before plugin discovery. Never proceed with connector-dependent output after a failed or blocked call.

## Goal-call mapping

Map intake to the goal calculator:

- `age`: intake field 3
- `sex`: field 4
- `height`: field 5 with unit `cm`
- `weight`: field 6 with unit `kg`
- `weight_goal`: `lose`, `maintain`, or `gain` from fields 6 and 7
- `diet_speed`: slow → `slow`; moderate → `moderate`; fast → `aggressive`
- `approach`: vegetarian → `veg`; vegan → `vegan`; pescatarian → `pesc`; otherwise `omni`, unless a more specific supported approach was requested

Infer `activity_level` from daily movement and training together:

- `sedentary`: mostly sitting and 0-1 light sessions weekly
- `lightly_active`: mostly sitting with 1-3 sessions, or lightly active with little training
- `moderately_active`: lightly active with 3-5 sessions weekly
- `very_active`: very active work or hard training most days
- `extremely_active`: athlete-level intense or twice-daily training

If two levels are equally plausible, ask the client to choose before calling.

Dietary style such as halal is enforced in meal selection; it is not a supported goal-calculator approach.

## Reading the response

- Record daily target calories and TDEE exactly.
- If only breakfast, lunch, and dinner allocations are returned, sum those allocations for daily protein, carbs, and fat.
- A field named `netCarbs` defines net carbohydrates. Do not relabel it as total carbs.
- Preserve the raw response for audit when possible.
- Run `scripts/reconcile_targets.py` with the derived daily values.

## One-call recipe recommendations

Search only after the complete meal plan passes validation. Make exactly zero or one recipe-search call for the entire plan; never call once per meal slot and never run a retry or fallback ladder. Each call can render a separate MyFitnessPal panel, so multiple calls create unnecessary loading cards.

For the single call:

- set `max_results` to 5;
- use one preferred protein or carbohydrate as the only keyword, favoring a food already used in the plan;
- retain the client's maximum cooking time, allergies, refused foods, and dietary approach;
- omit tight calorie and macro filters so one call has a reasonable chance of returning results;
- add the requested cuisine only when the connector supports it reliably;
- for Arab or Egyptian clients, add `pork` and `alcohol` to dislikes unless the client explicitly opted out of the halal default.

Show at most five returned recipes total in a compact table with only `Preferred-food match` and `Recipe`. Add one localized sentence directing the client to the connector's recipe cards or images for full details. Do not add time, calories, or macro columns, and do not fill the response with `Not exposed by connector`. Recipe nutrition is connector-only information and must not affect plan totals. If the search returns no recipes, report that no verified MyFitnessPal recommendations were found and stop; do not search again.

For halal clients, add a halal-verification note for meat, cheese, sauces, and seasonings because the connector has no dedicated halal filter.

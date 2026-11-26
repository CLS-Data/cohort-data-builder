# Contract change: sweep ages in the manifest

Amends [site-data.md](../../001-cohort-data-builder/contracts/site-data.md). Update that
file, `docs/data-format.md` and the data checks in the same commit.

## `manifest.wave.list[]`

```json
{ "key": "9m", "label": "Sweep 1, 2001–02", "age": 0.75, "ageRange": [0.75, 0.83] }
```

| Field | Required | Meaning |
|---|---|---|
| `age` | no | Cohort members' typical age in years at the sweep; months as a fraction (9 months = 0.75). |
| `ageRange` | no | `[min, max]` years when the sweep spanned ages; `min ≤ age ≤ max`. |

When `age` is absent the site uses the key if it is `<n>y` (n years) or `<n>m` (n months);
otherwise the sweep is drawn in the "age not known" column. Existing manifests stay valid.

## Data checks (added to D3)

- `age`, if present, is a number from 0 to 120.
- `ageRange`, if present, is two numbers, `min ≤ max`, and contains `age` when both exist.
- Ages need not follow the list's order: sub-sweeps share an age (bcs70 `s10_1`–`s10_4` are
  all 50) and can be older than the sweep after them (ncds `s9_1`, 63, before `s10`, 61).
- A warning, not a failure, for a sweep with neither `age` nor an age-shaped key.

## Axis labels

Several sweeps of one cohort at one age sit in adjacent columns of that age, in list order.

An age under 1 is labelled in months (`9m`); otherwise in whole years where whole (`11`)
or one decimal (`2.5`). With a range the tooltip gives it (`ages 33–35`).

## Cluster Column Definition

Use the `cluster` column to filter data based on internal product group clusters.

### What Are Clusters?
- Clusters are **backend groupings** used internally — not customer-facing brand names.
- Example values:
  - `LRAGA`
  - `LWKWR`
  - `GCLSQ`

---

### Rule:
- Always filter using exact values in the `cluster` column.
- Example: `cluster = 'LRAGA'`

Do **not** treat cluster codes as productgroup or brand names.

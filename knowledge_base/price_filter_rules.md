## Price Filtering Rules

Use the `ucp_final` column for all price-based filtering. This is a **numeric field** representing the Unit Consumer Price (selling price per item).

---

###Conversion Logic:
- Convert shorthand formats like `10k`, `25K`, `30k+` into numeric values:
  - `10k` = `10000`
  - `25K` = `25000`
- Do **not** use these values as strings in SQL queries.

---

### 🧾 Valid Filter Formats:
- “10k–12k” → `ucp_final BETWEEN 10000 AND 12000`  
- “under 12k”, “below 12000” → `ucp_final < 12000`  
- “above 25000”, “more than 25k” → `ucp_final > 25000`  
- “10 k to 12 k”, “10k -12k” → also valid range inputs  

---

###Avoid:
- Never write: `ucp_final = '10K–12K'` or use **string comparisons**
- Always use **numeric comparison operators** like `<`, `>`, `BETWEEN`

---

### 📌 Reminder:
All price-related filters must:
- Use the `ucp_final` column
- Be expressed in numeric form (e.g., `10000`, `12000`)
- Avoid string-based representations

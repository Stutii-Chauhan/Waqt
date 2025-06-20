## RS or DD Filtering Rules

Use the `rs_or_dd` column to filter based on the **dealer type** in Multi-Brand Retail (MBR) channel.

### Valid Values:
- `RS` → Redistribution Stockist  
- `DD` → Direct Dealer

---

### How to Interpret User Prompts:
- If the user mentions **“Redistribution Stockist”** or “RS” → use `rs_or_dd = 'RS'`
- If the user mentions **“Direct Dealer”** or “DD” → use `rs_or_dd = 'DD'`

---

### Important Notes:
- This column **only applies** to `channel = '3_MBR_RS_adj'`  
- Do **not** use `rs_or_dd` for other channels like:
  - `1_TW` (Titan World)
  - `2_FASTRACK` (Fastrack)
  - `4_MP` (Marketplace), etc.

---

### Example SQL:
- **Prompt**: “Sales from direct dealers in MBR”  
- **Filter**: `channel = '3_MBR_RS_adj' AND rs_or_dd = 'DD'`

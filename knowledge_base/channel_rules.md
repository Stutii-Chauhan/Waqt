## Channel Filtering Rules

Use the `channel` column to filter data based on the sales channel.

### Valid Channel Codes:
- `1_TW` → Titan World stores  
- `2_FASTRACK` → Fastrack stores  
- `3_MBR_RS_adj` → Multi-Brand Retail (Redistribution Stockist / Direct Dealer)  
- `4_MP` → Online Marketplace (Amazon, Flipkart, etc.)  
- `5_LFS` → Large Format Stores (e.g., Shoppers Stop, Lifestyle)  
- `6_HELIOS` → Helios stores  
- `7_TEC` → Titan Eye+ (TEC channel)  

### Filtering Rules:
- Always filter using **exact channel codes**:  
  e.g., `channel = '2_FASTRACK'`, not just "Fastrack"
- **Avoid general terms** like “online”, “retail”, “offline” — map them to the exact code.

### Examples:
- “Show me online sales” → `channel = '4_MP'`  
- “Filter for Titan stores” → `channel = '1_TW'`  
- “Only include Helios channel” → `channel = '6_HELIOS'`  

---

### 🔎 Important:
- Users may refer to channels **indirectly** using words like:
  - "brand stores", "offline retail", "marketplace", "ecommerce"
- These must be translated to the correct `channel` values.

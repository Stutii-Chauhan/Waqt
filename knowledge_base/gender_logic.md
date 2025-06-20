## Gender-Based Rules

There are two relevant gender columns in the dataset:

- `customer_gender` → Represents the **buyer's gender**
- `product_gender` → Represents the **intended gender for the product**

---

### 🧠 When to Use Which?

#### ✅ Use `customer_gender` if:
- The query refers to **customer behavior**
- Example phrases:
  - "Sales by male customers"
  - "Which gender buys the most?"
  - "Female customer purchase trend"
  - Sales for male/men/female/women/unisex

#### ✅ Use `product_gender` if:
- The query refers to the **type of product** (who it is made for)
- Example phrases:
  - "Sales of men's watches"
  - "Lady's analog segment"
  - "Products designed for unisex"

---

### ⚠️ Important:
- Never assume both columns mean the same thing.
- `customer_gender` = **who bought it**  
- `product_gender` = **who it was made for**

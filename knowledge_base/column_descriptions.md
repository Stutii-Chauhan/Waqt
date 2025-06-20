## Column Descriptions

Here is a list of important columns in the `watches_schema` table, along with their meanings:

- `productgroup`: Brand of the product (e.g., AI, RG, TF, etc.)
- `product_gender`: Gender the product is designed for (G - Gents, L - Ladies, U - Unisex, P - Pair)
- `cluster`: Internal grouping code (e.g., LRAGA, LWKWR, GCLSQ)
- `quantity`: Units sold in the transaction (integer)
- `billdate`: Date of transaction
- `channel`: Sales channel (e.g., 1_TW, 2_FASTRACK, 4_MP, 6_HELIOS)
- `region`: Geographic region (e.g., North, East, South1, West)
- `raw_region`: Special region mapping used for TW, Fastrack, and Helios
- `tier`: City tier classification (e.g., Metro, Tier 1, Tier 2)
- `financial_year`: Financial year (e.g., FY23-24)
- `month_fy`: Fiscal year month label (e.g., Apr FY2425)
- `value`: Total transaction revenue (numeric)
- `itemnumber`: Unique SKU or item code
- `latest_sku`: Parent SKU grouping identifier
- `ucp_final`: Unit consumer price (numeric)
- `dealer_type`: Dealer classification (e.g., EMM, KAM)
- `platform`: Marketplace name (e.g., Amazon, Flipkart)
- `uid`: Customer ID
- `product_segment`: Product segment (e.g., Smart, Premium, Mainline Analog)
- `bill_number`: Unique invoice or bill number
- `store_code`: Internal store identifier
- `city`: City where the transaction occurred
- `lfs_chain`: Chain code for LFS (e.g., SS, LS)
- `rs_or_dd`: Dealer model type (RS or DD)
- `state`: State where the transaction occurred
- `ytd_tag`: Year-to-date tag for recent transactions
- `dob`: Customer’s date of birth
- `anniversary`: Customer’s anniversary date
- `bday_trans`: Was the transaction during customer’s birthday period? (Y/N)
- `anniv_trans`: Was the transaction during anniversary period? (Y/N)
- `customer_gender`: Customer’s gender (e.g., Male, Female, Other)

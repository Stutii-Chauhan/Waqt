import streamlit as st
import pandas as pd
from io import BytesIO
from supabase import create_client
import google.generativeai as genai
import json
import re

# --- Config ---
st.set_page_config(page_title="Excel Auto-Updater for Waqt", layout="wide")

# --- Environment Secrets ---
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]

if not SUPABASE_URL or not SUPABASE_KEY or not GEMINI_API_KEY:
    st.error("❌ Missing Supabase or Gemini credentials.")
    st.stop()

# --- Init Clients ---
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

# --- Title ---
st.title("📊 Excel Auto-Updater for Waqt")

# --- Upload File ---
uploaded_file = st.file_uploader("Step 1️⃣: Upload your Excel file", type=["xlsx"])

if uploaded_file:
    sheets = pd.read_excel(uploaded_file, sheet_name=None)
    sheet_names = list(sheets.keys())
    selected_sheet = st.selectbox("📑 Select a sheet to process", sheet_names)
    df = sheets[selected_sheet]

    if df.empty:
        st.warning("Selected sheet is empty.")
        st.stop()

    # --- Auto-fix unnamed first column ---
    if "unnamed" in df.columns[0].lower():
        df.columns.values[0] = "RowHeader"
    else:
        df.columns.values[0] = df.columns[0].title().replace(" ", "_")

    row_header = df.columns[0]

    # --- Standardize values to title case ---
    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].astype(str).str.title()

    st.subheader(f"🔍 Preview: {selected_sheet}")
    st.dataframe(df.head(10), use_container_width=True)

    # --- Melt the Excel into long format ---
    df_long = df.melt(id_vars=[row_header], var_name="ColumnHeader", value_name="Value")
    df_long.rename(columns={row_header: "RowHeader"}, inplace=True)

    sample = df_long.head(5)

    # --- Prompt Input ---
    user_query = st.text_input("Step 2️⃣: What do you want to update or calculate in this sheet?")

    if user_query and st.button("🚀 Start"):
        column_info = {
            "brand": "Product's brand group (Group 1, Group 2, Group 3)",
            "product_gender": "Product gender (P, O, G, L, U)",
            "billdate": "Date of transaction",
            "channel": "Sales channel (Channel A, Channel B, Channel C)",
            "region": "Geographic region (North, East, South1 etc.)",
            "itemnumber": "SKU or item ID",
            "product_segment": "Watch category (Smart, Premium, Mainline Analog)",
            "price_band": "Price range",
            "ucp_final": "Numerical price value",
            "bday_trans": "Was it a birthday campaign? (Y/N)",
            "anniv_trans": "Was it an anniversary campaign? (Y/N)",
            "customer_gender": "Customer's gender (Male, Female)",
            "enc_ftd": "Customer's first transaction date",
            "channel_ftd": "Date of First transaction on that channel",
            "brand_ftd": "Date of First transaction with brand",
            "customer_masked": "Masked customer ID",
            "value_masked": "Transaction revenue",
            "qty_masked": "Units sold"
        }
        column_description_text = "\n".join([f"- {k}: {v}" for k, v in column_info.items()])

        available_tables = """
        toy_cleaned: [Region, Channel, Product Segment, Value_Masked, Qty_Masked, ...]
        """

        prompt = f"""
You are a smart assistant that maps Excel structures to database tables or calculations.

User Query:
{user_query}

Excel DataFrame (melted format):
{sample.to_csv(index=False)}

Available table:
toy_cleaned

Columns:
{column_description_text}

Return JSON in this format:
{{
  "table": "toy_cleaned",
  "row_header_column": "...",
  "column_header_column": "...",
  "value_column": "...",
  "operation": "sum",
  "filters": {{ optional key-value filters like "Product Segment": "Premium" }}
}}
Only return a JSON object. Do NOT explain.
"""

        with st.spinner("🤖 Sending structure + prompt to Gemini..."):
            response = model.generate_content(prompt)

        try:
            cleaned_json = re.sub(r"^```json|```$", "", response.text.strip(), flags=re.MULTILINE).strip()
            mapping = json.loads(cleaned_json)
            st.success("✅ Gemini extracted the following logic:")
            st.json(mapping)
        except Exception:
            st.error("❌ Gemini returned invalid JSON. Please check prompt.")
            st.stop()

        # --- Query Supabase based on mapping ---
        def fetch_value(row_val, col_val):
            query = (
                supabase.table(mapping["table"])
                .select(mapping["value_column"])
                .eq(mapping["row_header_column"], str(row_val).strip().title())
                .eq(mapping["column_header_column"], str(col_val).strip().title())
            )
            if "filters" in mapping:
                for k, v in mapping["filters"].items():
                    query = query.eq(k, str(v).strip().title())

            try:
                res = query.execute()
            except Exception as e:
                st.error(f"❌ Supabase query failed: {e}")
                return None

            if res.data:
                return sum([r[mapping["value_column"]] for r in res.data])
            return None

        st.warning(f"📡 Querying table: {mapping['table']}")

        df_long[mapping["value_column"]] = df_long.apply(
            lambda row: fetch_value(row["RowHeader"], row["ColumnHeader"]), axis=1
        )

        updated_df = df_long.pivot(index="RowHeader", columns="ColumnHeader", values=mapping["value_column"]).reset_index()

        st.subheader("✅ Updated Excel")
        st.dataframe(updated_df, use_container_width=True)

        # --- Download ---
        def to_excel_download(df):
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            return output.getvalue()

        st.download_button(
            label="📥 Download Updated Excel",
            data=to_excel_download(updated_df),
            file_name="updated_sales.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

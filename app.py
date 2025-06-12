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
    st.error(" Missing Supabase or Gemini credentials.")
    st.stop()

# --- Init Clients ---
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

# --- Title ---
st.title("Excel Auto-Updater for Waqt")

# --- Upload File ---
uploaded_file = st.file_uploader("Step 1: Upload your Excel file", type=["xlsx"])

if uploaded_file:
    sheets = pd.read_excel(uploaded_file, sheet_name=None)
    sheet_names = list(sheets.keys())
    selected_sheet = st.selectbox("Select a sheet to process", sheet_names)
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
    column_headers = df.columns[1:].tolist()

    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].astype(str).str.title()

    st.subheader(f" Preview: {selected_sheet}")
    st.dataframe(df.head(10), use_container_width=True)

    df_long = df.melt(id_vars=[row_header], var_name="ColumnHeader", value_name="Value")
    df_long.rename(columns={row_header: "RowHeader"}, inplace=True)

    sample_csv = df_long.head(5).to_csv(index=False)

    user_query = st.text_input("Step 2: What do you want to update or calculate in this sheet?")

    if user_query and st.button("Start"):
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

        prompt = f"""
You are a smart assistant that maps Excel structures to database tables or calculations.

User Query:
{user_query}

Excel DataFrame (melted format):
{sample_csv}

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

        with st.spinner("Sending structure + prompt to Gemini..."):
            response = model.generate_content(prompt)

        try:
            cleaned_json = re.sub(r"^```json|```$", "", response.text.strip(), flags=re.MULTILINE).strip()
            mapping = json.loads(cleaned_json)
            st.success("Gemini extracted the following logic:")
            st.json(mapping)
        except Exception:
            st.error("Gemini returned invalid JSON. Please check prompt.")
            st.stop()

        with st.spinner("Fetching aggregated data from Supabase..."):
            filters = mapping.get("filters", {})
            operation = mapping.get("operation", "sum").lower()

            row_values = [v.strip() for v in df[row_header].dropna().unique()]
            col_values = [v.strip() for v in column_headers]

            query = supabase.table(mapping["table"]).select(
                f"{mapping['row_header_column']}, {mapping['column_header_column']}, {mapping['value_column']}"
            )

            for key, val in filters.items():
                query = query.eq(key, str(val).strip())

            query = query.in_(mapping["row_header_column"], row_values)
            query = query.in_(mapping["column_header_column"], col_values)

            where_clauses = [f"{k} = '{v}'" for k, v in filters.items()]
            where_clauses.append(f"{mapping['row_header_column']} IN ({', '.join([repr(v) for v in row_values])})")
            where_clauses.append(f"{mapping['column_header_column']} IN ({', '.join([repr(v) for v in col_values])})")

            sql_preview = f"""
SELECT {mapping['row_header_column']}, {mapping['column_header_column']}, {mapping['value_column']}
FROM {mapping['table']}
WHERE {' AND '.join(where_clauses)}
"""
            st.code(sql_preview, language="sql")

            try:
                result = query.execute()
                result_df = pd.DataFrame(result.data)
                st.write("Raw Result from Supabase:", result_df)
            except Exception as e:
                st.error(f"Supabase query failed: {e}")
                st.stop()

            if result_df.empty:
                st.warning("No matching data found in Supabase.")
                st.stop()

            agg_func = "sum" if operation == "sum" else "mean"
            updated_df = result_df.groupby(
                [mapping["row_header_column"], mapping["column_header_column"]]
            )[mapping["value_column"]].agg(agg_func).round(2).reset_index()

            final_df = updated_df.pivot(
                index=mapping["row_header_column"],
                columns=mapping["column_header_column"],
                values=mapping["value_column"]
            ).reset_index()

        st.subheader("Updated Excel")
        st.dataframe(final_df, use_container_width=True)

        def to_excel_download(df):
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            return output.getvalue()

        st.download_button(
            label="Download Updated Excel",
            data=to_excel_download(final_df),
            file_name="updated_sales.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

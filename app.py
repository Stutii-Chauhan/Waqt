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
    st.error("Missing Supabase or Gemini credentials.")
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

    sample_json = json.dumps(df_long.head(5).to_dict(orient="records"), indent=2)

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
column_description_text = "
".join([f"- {k}: {v}" for k, v in column_info.items()])

prompt = f"""
You are a PostgreSQL expert.

Given the user query and the sample Excel structure (in JSON), generate a SQL query to get the required data from the table `toy_cleaned`.

User Query:
{user_query}

Excel Data (JSON preview):
{sample_json}

Table: toy_cleaned

Schema (column names and descriptions):
{column_description_text}

Output only the SQL query. Do NOT explain anything.
"""

        with st.spinner("Sending structure + query to Gemini..."):
            response = model.generate_content(prompt)

        sql_query = response.text.strip().strip("`").strip()

        st.subheader("🧠 Gemini SQL Output")
        st.code(sql_query, language="sql")

        st.warning("⚠️ Ensure your Supabase has an RPC function called 'run_sql' that accepts a 'query' parameter")

        try:
            result = supabase.rpc("run_sql", {"query": sql_query}).execute()
            result_df = pd.DataFrame(result.data)
        except Exception as e:
            st.error(f"SQL execution failed: {e}")
            st.stop()

        if result_df.empty:
            st.warning("No matching data found in Supabase.")
            st.stop()

        # Pivot result to original format if 3 columns returned
        if result_df.shape[1] == 3:
            final_df = result_df.pivot(index=result_df.columns[0], columns=result_df.columns[1], values=result_df.columns[2]).reset_index()
        else:
            final_df = result_df

        st.subheader("📥 Updated Excel Output")
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

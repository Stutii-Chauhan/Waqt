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
    df_raw = pd.read_excel(uploaded_file, sheet_name=selected_sheet, header=None)

    # Detect blank rows and split into multiple tables
    blank_rows = df_raw[df_raw.isnull().all(axis=1)].index.tolist()
    table_starts = [0] + [i + 1 for i in blank_rows]
    table_ends = blank_rows + [len(df_raw)]

    table_dfs = [
        df_raw.iloc[start:end].dropna(how='all').reset_index(drop=True)
        for start, end in zip(table_starts, table_ends)
    ]

    for i, table_df in enumerate(table_dfs, start=1):
        if table_df.empty:
            st.warning(f"⚠️ Table {i} is empty. Skipping.")
            continue

        # --- Auto-fix unnamed first column ---
        if "unnamed" in table_df.columns[0].lower():
            table_df.columns.values[0] = "RowHeader"
        else:
            table_df.columns.values[0] = table_df.columns[0].title().replace(" ", "_")

        row_header = table_df.columns[0]
        column_headers = table_df.columns[1:].tolist()

        for col in table_df.columns:
            if table_df[col].dtype == "object":
                table_df[col] = table_df[col].astype(str).str.title()

        st.subheader(f"🔹 Preview: Table {i} from {selected_sheet}")
        st.dataframe(table_df.head(10), use_container_width=True)

        df_long = table_df.melt(id_vars=[row_header], var_name="ColumnHeader", value_name="Value")
        df_long.rename(columns={row_header: "RowHeader"}, inplace=True)

        # Ensure at least one sample row for each (RowHeader, ColumnHeader) pair
        sample_rows = []
        row_vals = df_long["RowHeader"].unique()
        col_vals = df_long["ColumnHeader"].unique()

        for row in row_vals:
            for col in col_vals:
                match = df_long[(df_long["RowHeader"] == row) & (df_long["ColumnHeader"] == col)]
                if not match.empty:
                    sample_rows.append(match.head(1))

        balanced_sample_df = pd.concat(sample_rows)
        sample_json = json.dumps(balanced_sample_df.to_dict(orient="records"), indent=2)

    # --- User Query Input ---
    user_query = st.text_input("Step 2: Enter prompts for each table (separated by `;`)")
    
    if user_query and st.button("Start"):
        prompts = [p.strip() for p in user_query.split(";")]
        if len(prompts) != len(table_dfs):
            st.error(f"🛑 Found {len(table_dfs)} table(s) but {len(prompts)} prompt(s). Please ensure they match.")
            st.stop()
    
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
        column_description_text = "\n".join([f"- {k}: {v}" for k, v in column_info.items()])
    
        price_filtering_rules = """
        Price Filtering Rules:
    
        - Always use the numeric `ucp_final` column.
        - Convert shorthand like “10k”, “25K” to numeric values (e.g., 10k = 10000).
        - If the user mentions a price range (e.g., “10k–12k”), write: `ucp_final BETWEEN 10000 AND 12000`.
        - If the user says “below 12000”, “under 12k”, write: `ucp_final < 12000`.
        - If the user says “above 25000”, “more than 25k”, write: `ucp_final > 25000`.
        - Handle user typos like “10k -12k”, “10k – 12k”, “10 k to 12 k” as valid ranges.
        - Never use `ucp_final = '10K–12K'` or any string literal comparison for price.
    
        Important:
        - All price-related filtering must be done using the numeric `ucp_final` column only.
        - Convert “10k”, “25K”, etc. to thousands: 10k = 10000.
        - Apply filters using: `ucp_final BETWEEN ...`, `ucp_final < ...`, or `ucp_final > ...` — never as strings.
        """
    
        for i, (table_df, prompt_text) in enumerate(zip(table_dfs, prompts), start=1):
            st.markdown(f"### 🔹 Table {i}")
    
            # Auto-fix unnamed first column
            if "unnamed" in table_df.columns[0].lower():
                table_df.columns.values[0] = "RowHeader"
            else:
                table_df.columns.values[0] = table_df.columns[0].title().replace(" ", "_")
    
            row_header = table_df.columns[0]
    
            for col in table_df.columns:
                if table_df[col].dtype == "object":
                    table_df[col] = table_df[col].astype(str).str.title()
    
            df_long = table_df.melt(id_vars=[row_header], var_name="ColumnHeader", value_name="Value")
            df_long.rename(columns={row_header: "RowHeader"}, inplace=True)
    
            column_sample = []
            for col in df_long["ColumnHeader"].unique():
                sample_rows = df_long[df_long["ColumnHeader"] == col].head(1)
                column_sample.append(sample_rows)
            balanced_sample_df = pd.concat(column_sample)
    
            sample_json = json.dumps(balanced_sample_df.to_dict(orient="records"), indent=2)
    
            prompt = f"""
            You are a PostgreSQL expert.
    
            The user has uploaded an Excel sheet that was converted to a long-form JSON structure where:
            - `RowHeader` contains values from one categorical field (e.g., region, gender, etc.)
            - `ColumnHeader` contains values from another categorical field (e.g., channel, segment, etc.)
            - `Value` is empty, and the user has asked for it to be calculated (e.g., average revenue)
    
            Your job:
            - Interpret the user's query
            - Detect the correct row, column, and value fields in the table `toy_cleaned`
            - Apply `WHERE` clauses to restrict only to the RowHeader and ColumnHeader values present in the Excel
            - Do NOT use JOIN with VALUES. Instead, use simple WHERE ... IN (...) filtering based on the RowHeader and ColumnHeader values.
            - Return a 3-column result (RowHeader, ColumnHeader, Aggregated Value)
            - Write a SQL query using correct table and column names from schema
    
            {price_filtering_rules}
    
            User Query:
            {prompt_text}
    
            Excel JSON Preview:
            {sample_json}
    
            Available Table: toy_cleaned
    
            Schema (column names and descriptions):
            {column_description_text}
    
            Only return a SQL query. Do not explain anything.
            """
    
            with st.spinner("Sending structure + query to Gemini..."):
                response = model.generate_content(prompt)
    
            sql_query = response.text.strip().strip("`").strip()
            if sql_query.lower().startswith("sql"):
                sql_query = sql_query[3:].strip()
            sql_query = sql_query.rstrip(";")
    
            with st.expander("🧠 Gemini SQL Output (click to expand)"):
                st.code(sql_query, language="sql")
    
            try:
                result = supabase.rpc("run_sql", {"query": sql_query}).execute()
                raw_data = result.data
    
                if isinstance(raw_data, list) and "result" in raw_data[0]:
                    flattened_data = raw_data[0]["result"]
                    result_df = pd.DataFrame(flattened_data)
                else:
                    result_df = pd.DataFrame(raw_data)
            except Exception as e:
                st.error(f"SQL execution failed: {e}")
                st.stop()
    
            if result_df.empty:
                st.warning("No matching data found in Supabase.")
                st.stop()
    
            if result_df.shape[1] == 3:
                final_df = result_df.pivot(
                    index=result_df.columns[0],
                    columns=result_df.columns[1],
                    values=result_df.columns[2]
                ).reset_index()
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
                file_name=f"updated_sales_table_{i}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    

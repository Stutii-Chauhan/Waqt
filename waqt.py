import streamlit as st
import pandas as pd
from io import BytesIO
import os
from supabase import create_client
import google.generativeai as genai
import json
import re

st.set_page_config(page_title="Excel Auto-Updater for Waqt", layout="wide")

# --- Load environment variables ---
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]

# --- Fail fast if secrets missing ---
if not SUPABASE_URL or not SUPABASE_KEY or not GEMINI_API_KEY:
    st.error("❌ Missing Supabase or Gemini credentials.")
    st.stop()

# --- Init Supabase and Gemini ---
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

# --- Utility: Split sheet into blocks using blank rows ---
def split_dataframe_by_blank_rows(df):
    split_indices = df[df.isnull().all(axis=1)].index.tolist()
    blocks = []
    start_idx = 0

    for idx in split_indices:
        block = df.iloc[start_idx:idx]
        if not block.dropna(how="all").empty:
            blocks.append(block.reset_index(drop=True))
        start_idx = idx + 1

    if start_idx < len(df):
        block = df.iloc[start_idx:]
        if not block.dropna(how="all").empty:
            blocks.append(block.reset_index(drop=True))

    return blocks

# --- Utility: Gemini + Supabase processing ---
def process_table(df_partial, user_query):
    row_header = df_partial.columns[0]
    df_long = df_partial.melt(id_vars=[row_header], var_name="ColumnHeader", value_name="Value")
    df_long.rename(columns={row_header: "RowHeader"}, inplace=True)

    sample = df_long.head(5)
    available_tables = """
    sales_category_gender_region: [Gender Category, Region, Product Category, Sales]
    region_quarter_category_sales: [Region, Quarter, Product Category, Sales]
    """
    prompt = f"""
You are a smart assistant that maps Excel structures to database tables.

User Query:
{user_query}

Excel DataFrame (melted format):
{sample.to_csv(index=False)}

Available tables:
{available_tables}

Return JSON in this format:
{{
  "table": "...",
  "row_header_column": "...",
  "column_header_column": "...",
  "value_column": "...",
  "filters": {{ optional key-value filters like "Product Category": "Eyewear", "Quarter": "Q1" }}
}}
    """

    with st.spinner("Sending prompt to Gemini..."):
        response = model.generate_content(prompt)

    try:
        cleaned_json = re.sub(r"^```json|```$", "", response.text.strip(), flags=re.MULTILINE).strip()
        mapping = json.loads(cleaned_json)
        st.info(f"Using Supabase table: `{mapping['table']}`")
        st.json(mapping)
    except Exception:
        st.error("Gemini returned invalid JSON. Please check prompt.")
        return None

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
            if res.data:
                return sum([r[mapping["value_column"]] for r in res.data])
        except Exception as e:
            st.error(f"❌ Supabase query failed: {e}")
        return None

    df_long[mapping["value_column"]] = df_long.apply(
        lambda row: fetch_value(row["RowHeader"], row["ColumnHeader"]), axis=1
    )

    return df_long.pivot(index="RowHeader", columns="ColumnHeader", values=mapping["value_column"]).reset_index()

# --- Utility: Convert to downloadable Excel ---
def to_excel_download(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

# --- UI ---
st.title("Enhancement for Waqt")

uploaded_file = st.file_uploader("Upload your Excel file", type=["xlsx"])

if uploaded_file:
    sheets = pd.read_excel(uploaded_file, sheet_name=None)
    sheet_names = list(sheets.keys())
    selected_sheet = st.selectbox("Select a sheet to process", sheet_names)
    df = sheets[selected_sheet]

    if df.empty:
        st.warning("Selected sheet is empty.")
        st.stop()

    # 🔍 Split into multiple blocks
    tables = split_dataframe_by_blank_rows(df)

    if not tables:
        st.warning("No tables detected in the sheet.")
        st.stop()

    # 👤 Show all table blocks and get prompts
    prompts = []
    for i, table in enumerate(tables):
        st.subheader(f"🧾 Table {i+1}")
        st.dataframe(table)
        prompt = st.text_input(f"Prompt for Table {i+1}", key=f"prompt_{i}")
        prompts.append(prompt)

    # ▶️ Start processing
    if all(prompts):
        if st.button("Start Update"):
            for i, (table, prompt) in enumerate(zip(tables, prompts)):
                st.markdown(f"### 🔄 Processing Table {i+1}")
                updated = process_table(table, prompt)
                if updated is not None:
                    st.success(f"✅ Table {i+1} Updated")
                    st.dataframe(updated)
                    st.download_button(
                        f"📥 Download Table {i+1}",
                        data=to_excel_download(updated),
                        file_name=f"table_{i+1}_updated.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

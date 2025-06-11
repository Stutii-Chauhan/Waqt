import streamlit as st
import pandas as pd
from io import BytesIO
from supabase import create_client
import google.generativeai as genai
from openpyxl import load_workbook
from openpyxl.utils.dataframe import dataframe_to_rows
import json
import re

st.set_page_config(page_title="Excel Auto-Updater for Waqt", layout="wide")

# --- Load environment variables ---
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]

if not SUPABASE_URL or not SUPABASE_KEY or not GEMINI_API_KEY:
    st.error("❌ Missing Supabase or Gemini credentials.")
    st.stop()

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

# --- Split by blank rows ---
def split_dataframe_by_blank_rows(df):
    split_indices = df[df.isnull().all(axis=1)].index.tolist()
    blocks = []
    start_idx = 0

    for idx in split_indices:
        block = df.iloc[start_idx:idx]
        if not block.dropna(how="all").empty:
            blocks.append((start_idx, block.reset_index(drop=True)))
        start_idx = idx + 1

    if start_idx < len(df):
        block = df.iloc[start_idx:]
        if not block.dropna(how="all").empty:
            blocks.append((start_idx, block.reset_index(drop=True)))

    return blocks  # list of (start_row_index, df)


def process_table(df_partial, user_query):
    df_partial = df_partial.dropna(axis=1, how="all")
    raw_headers = df_partial.iloc[0].fillna("Unnamed").astype(str).str.strip()
    df_partial.columns = raw_headers
    df_partial = df_partial[1:].reset_index(drop=True)

    if df_partial.columns[0].lower() in ["", "unnamed", "nan", "none"]:
        df_partial.columns = ["RowHeader"] + list(df_partial.columns[1:])

    row_header = df_partial.columns[0]
    df_long = df_partial.melt(id_vars=[row_header], var_name="ColumnHeader", value_name="Value")
    df_long.rename(columns={row_header: "RowHeader"}, inplace=True)

    sample = df_long.head(5)
    available_tables = """
    sales_category_gender_region: [Gender Category, Region, Product Category, Sales]
    region_quarter_category_sales: [Region, Quarter, Product Category, Sales]
    """

    prompt = f"""
You are a smart assistant that maps Excel structures to database tables or calculations.

User Query:
{user_query}

Excel DataFrame (melted format):
{sample.to_csv(index=False)}

Available tables:
{available_tables}

You can also return derived operations like "growth", "difference", or "average".

If an average is needed, you may omit 'row_header_column' and 'column_header_column', and instead return:

{{
  "table": "...",
  "group_by": ["...", "..."],        ← fields to group by (e.g., Region, Gender)
  "value_column": "...",             ← field to aggregate (e.g., Sales)
  "agg_function": "average",         ← allowed: average, sum, max, etc.
  "filters": {{ optional key-value filters }}
}}
"""

    with st.spinner("Sending prompt to Gemini..."):
        response = model.generate_content(prompt)

    try:
        cleaned_json = re.sub(r"^```json|```$", "", response.text.strip(), flags=re.MULTILINE).strip()
        mapping = json.loads(cleaned_json)
        st.info("Gemini JSON Output:")
        st.json(mapping)
    except Exception:
        st.error("Gemini returned invalid JSON. Please check prompt.")
        return None

    # ✅ Option 2: Supabase-based grouped aggregation
    if "agg_function" in mapping and "group_by" in mapping:
        try:
            query = supabase.table(mapping["table"]).select("*")

            if "filters" in mapping:
                for k, v in mapping["filters"].items():
                    query = query.eq(k, str(v).strip().title())

            result = query.execute()
            df_result = pd.DataFrame(result.data)

            if df_result.empty:
                st.warning("No data found for aggregation.")
                return None

            grouped_df = (
                df_result
                .groupby(mapping["group_by"])[mapping["value_column"]]
                .mean()  # Extendable: .sum(), .max(), etc.
                .round(2)
                .unstack()
                .fillna(0)
                .reset_index()
            )
            return grouped_df

        except Exception as e:
            st.error(f"❌ Supabase aggregation failed: {e}")
            return None

    # 🧮 Option 1: Growth / Difference from Excel-based structure
    if "calculation" in mapping and mapping["calculation"] in ["growth", "difference"]:
        # Generate lookup grid
        unique_rows = df_long["RowHeader"].unique()
        unique_cols = df_long["ColumnHeader"].unique()
        lookup_grid = pd.DataFrame([(r, c) for r in unique_rows for c in unique_cols], columns=["RowHeader", "ColumnHeader"])

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
            except:
                return None
            return None

        lookup_grid["Value"] = lookup_grid.apply(lambda row: fetch_value(row["RowHeader"], row["ColumnHeader"]), axis=1)
        derived_df = lookup_grid.pivot(index="RowHeader", columns="ColumnHeader", values="Value")
        derived_df_numeric = derived_df.apply(pd.to_numeric, errors='coerce')

        if mapping["calculation"] == "growth":
            result_df = derived_df_numeric.pct_change(axis=1).fillna(0).round(2)
        elif mapping["calculation"] == "difference":
            result_df = derived_df_numeric.diff(axis=1).fillna(0).round(2)

        result_df.reset_index(inplace=True)
        return result_df

    # 🧱 Default: Fetch values for each cell from Supabase
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



# --- Excel download ---
def to_excel_download(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

# --- UI ---
st.title("Enhancement for Waqt")

uploaded_file = st.file_uploader("Upload your Excel file", type=["xlsx"])

if uploaded_file:
    sheets = pd.read_excel(uploaded_file, sheet_name=None, header=None)
    sheet_names = list(sheets.keys())
    selected_sheet = st.selectbox("Select a sheet to process", sheet_names)
    df = sheets[selected_sheet]
    st.subheader(f"📄 Preview of Template - `{selected_sheet}`")
    st.dataframe(df, use_container_width=True)

    if df.empty:
        st.warning("Selected sheet is empty.")
        st.stop()

    tables = split_dataframe_by_blank_rows(df)

    if not tables:
        st.warning("No tables detected in the sheet.")
        st.stop()
    
    user_prompt_input = st.text_input(
        "Enter prompts for all tables (separated by `;`)", 
        placeholder="e.g. Sales by Region; Sales by Gender; Sales by Type"
    )
    prompts = [p.strip() for p in user_prompt_input.split(";") if p.strip()]
    positions = [start_row for (start_row, _) in tables]
    
    if len(prompts) != len(tables):
        st.warning(f"You entered {len(prompts)} prompts for {len(tables)} tables. Please match the count.")
    else:
        st.markdown("### 🧾 Prompt Mappings")
        for i, prompt in enumerate(prompts):
            st.markdown(f"**Prompt {i+1} → Table {i+1}:** `{prompt}`")

    
    # 🔁 Process on button click
    if len(prompts) == len(tables):
        start_triggered = st.button("Start Update")
    
        if start_triggered:
            results = []
    
            for i, ((start_row, table), prompt) in enumerate(zip(tables, prompts)):
                with st.spinner(f"Processing Table {i+1}..."):
                    updated = process_table(table, prompt)
                    results.append((start_row, updated))
                    st.success(f"✅ Table {i+1} Updated")
                    st.dataframe(updated)
    
            # 📥 Write updated tables into the original workbook
            from io import BytesIO
            wb = load_workbook(uploaded_file)
            ws = wb[selected_sheet]
    
            for (start_row, updated_df) in results:
                for r_idx, row in enumerate(dataframe_to_rows(updated_df, index=False, header=True)):
                    for c_idx, value in enumerate(row):
                        ws.cell(row=start_row + r_idx + 1, column=c_idx + 1, value=value)
    
            output = BytesIO()
            wb.save(output)
    
            st.download_button(
                "📥 Download Updated Excel (Original Layout)",
                data=output.getvalue(),
                file_name="updated_template_style.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

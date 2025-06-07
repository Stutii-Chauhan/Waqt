import streamlit as st
import pandas as pd
from io import BytesIO
import os
from supabase import create_client
import google.generativeai as genai
import json
import re

st.set_page_config(page_title="Excel Auto-Updater for Waqt", layout="wide")

# --- Load environment variables from Streamlit Secrets ---
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]

# --- Fail fast if secrets missing ---
if not SUPABASE_URL or not SUPABASE_KEY or not GEMINI_API_KEY:
    st.error("❌ Missing Supabase or Gemini credentials. Set SUPABASE_URL, SUPABASE_KEY, GEMINI_API_KEY.")
    st.stop()

# --- Init Supabase and Gemini ---
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

# --- Streamlit UI ---
st.title("Enhancement for Waqt")

user_query = st.text_input("What should I fill in? (e.g., Sales for Eyewear category)")
uploaded_file = st.file_uploader("Upload your Excel file", type=["xlsx"])

if uploaded_file and user_query:
    # Read all sheets
    sheets = pd.read_excel(uploaded_file, sheet_name=None)
    sheet_names = list(sheets.keys())
    selected_sheet = st.selectbox("📑 Select a sheet to process", sheet_names)
    df = sheets[selected_sheet]

    if df.empty:
        st.warning("Selected sheet is empty.")
        st.stop()

    st.subheader(f"Preview: {selected_sheet}")
    st.dataframe(df)

    row_header = df.columns[0]
    df_long = df.melt(id_vars=[row_header], var_name="ColumnHeader", value_name="Value")
    df_long.rename(columns={row_header: "RowHeader"}, inplace=True)

    with st.spinner("🤖 Sending structure + prompt to Gemini..."):
        response = model.generate_content(prompt)

    st.success("Prompt processed by Gemini!")

    sample = df_long.head(5)
    available_tables = """
    Sales_Category_Gender_Region: [Gender Category, Region, Product Category, Sales]
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
  "filters": {{ optional key-value filters like "Product Category": "Eyewear" }}
}}
    """
    response = model.generate_content(prompt)
    #st.code(response.text, language='json')

    try:
        cleaned_json = re.sub(r"^```json|```$", "", response.text.strip(), flags=re.MULTILINE).strip()
        mapping = json.loads(cleaned_json)
        mapping["table"] = "sales_category_gender_region"
        
    except:
        st.error("Gemini returned invalid JSON. Please check prompt.")
        st.stop()

    # --- Fill values from Supabase ---
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

        res = query.execute()
        if res.data:
            return sum([r[mapping["value_column"]] for r in res.data])
        return None

    # # 🧪 Check if Supabase returns any data without filters
    # st.markdown("### 🧪 Sanity Check: Preview Raw Supabase Data")

    # try:
    #     test_query = supabase.table(mapping["table"]).select("*").limit(10).execute()
    #     if test_query.data:
    #         st.success("✅ Supabase data fetched successfully")
    #         st.dataframe(pd.DataFrame(test_query.data))
    #     else:
    #         st.warning("⚠️ Supabase returned 0 rows. Table may be empty or misnamed.")
    # except Exception as e:
    #     st.error(f"❌ Error fetching Supabase data: {e}")

    df_long[mapping["value_column"]] = df_long.apply(
        lambda row: fetch_value(row["RowHeader"], row["ColumnHeader"]), axis=1
    )

    updated_df = df_long.pivot(index="RowHeader", columns="ColumnHeader", values=mapping["value_column"]).reset_index()
    st.subheader("✅ Updated Excel")
    st.dataframe(updated_df)

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

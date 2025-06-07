import streamlit as st
import pandas as pd
from io import BytesIO
import os
from supabase import create_client
import google.generativeai as genai

st.write("Available secrets:", list(st.secrets.keys()))

# --- Load environment variables ---
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# --- Fail fast if secrets missing ---
if not SUPABASE_URL or not SUPABASE_KEY or not GEMINI_API_KEY:
    st.error("❌ Missing Supabase or Gemini credentials. Set SUPABASE_URL, SUPABASE_KEY, GEMINI_API_KEY.")
    st.stop()

# --- Init Supabase and Gemini ---
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-pro")

# --- Streamlit UI ---
st.set_page_config(page_title="LLM Excel Auto-Updater", layout="wide")
st.title("📊 LLM-Powered Excel Updater")

uploaded_file = st.file_uploader("Upload your Excel file", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.subheader("🔍 Uploaded File Preview")
    st.dataframe(df)

    row_header = df.columns[0]
    df_long = df.melt(id_vars=[row_header], var_name="ColumnHeader", value_name="Value")
    df_long.rename(columns={row_header: "RowHeader"}, inplace=True)

    st.markdown("### 🤖 Sending structure to Gemini...")

    sample = df_long.head(5)
    available_tables = """
    Sales_Category_Gender_Region: [Gender Category, Region, Product Category, Sales]
    """
    prompt = f"""
You are a smart assistant that maps Excel structures to database tables.

Excel DataFrame (melted format):
{sample.to_markdown(index=False)}

Available tables:
{available_tables}

Return JSON in this format:
{{
  "table": "...",
  "row_header_column": "...",
  "column_header_column": "...",
  "value_column": "..."
}}
    """
    response = model.generate_content(prompt)
    st.code(response.text, language='json')

    try:
        import json
        mapping = json.loads(response.text)
    except:
        st.error("Gemini returned invalid JSON. Please check prompt.")
        st.stop()

    # --- Fill values from Supabase ---
    def fetch_value(row_val, col_val):
        res = (
            supabase.table(mapping["table"])
            .select(mapping["value_column"])
            .eq(mapping["row_header_column"], row_val)
            .eq(mapping["column_header_column"], col_val)
            .execute()
        )
        if res.data and len(res.data) > 0:
            return res.data[0][mapping["value_column"]]
        return None

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

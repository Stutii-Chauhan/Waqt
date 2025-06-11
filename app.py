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
    st.error("❌ Missing Supabase or Gemini credentials.")
    st.stop()

# --- Init Supabase and Gemini ---
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

# --- Title ---
st.title("📊 Excel Auto-Updater for Waqt")

# --- Upload Excel File ---
uploaded_file = st.file_uploader("Step 1️⃣: Upload your Excel file", type=["xlsx"])

if uploaded_file:
    xls = pd.ExcelFile(uploaded_file)
    sheet_names = xls.sheet_names

    # --- Sheet Selection ---
    selected_sheet = st.selectbox("Step 2️⃣: Select a sheet", sheet_names)
    df = pd.read_excel(xls, sheet_name=selected_sheet)

    # --- Apply Title Case to headers and values ---
    def standardize_to_title_case(df):
        df.columns = [col.replace('_', ' ').title().replace(' ', '_') for col in df.columns]
        for col in df.columns:
            if df[col].dtype == "object":
                df[col] = df[col].astype(str).str.title()
        return df

    df = standardize_to_title_case(df)

    # --- Show Preview ---
    st.subheader("🔍 Preview of Uploaded Data")
    st.dataframe(df.head(10), use_container_width=True)

    # --- User Prompt ---
    user_prompt = st.text_input("Step 3️⃣: What do you want to update or calculate in this sheet?")

    if user_prompt:
        st.markdown("🧠 Calling Gemini to interpret your prompt...")

        # --- Use updated schema with examples ---
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

        gemini_instruction = f"""
You are a data assistant for an Excel auto-updater tool.

The available Supabase table is 'toy_cleaned'. It contains the following columns:

{column_description_text}

Based on this user prompt:
\"{user_prompt}\"

Return only a JSON object with:
- table: always 'toy_cleaned'
- group_by: list of columns to group by (use exact names from the above list)
- metric: column to aggregate
- operation: one of ["sum", "average", "growth", "difference"]
- filters: optional column:value pairs to filter the data

Important:
- Do NOT make up any column names
- Use only the exact column names listed above
- Format response as raw JSON without extra text
"""

        try:
            gemini_response = model.generate_content(gemini_instruction)
            structured_json = json.loads(gemini_response.text)

            st.success("✅ Gemini extracted the following logic:")
            st.json(structured_json)

        except Exception as e:
            st.error(f"⚠️ Gemini failed: {e}")



        # TODO:
        # - Parse Gemini response into structured format
        # - Validate fields against Supabase schema
        # - Query Supabase
        # - Update DataFrame
        # - Show and allow download of updated Excel

else:
    st.info("📁 Please upload an Excel file to begin.")

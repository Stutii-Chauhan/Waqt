import streamlit as st
from utils.gemini_handler import get_prompt_response
from utils.file_processor import extract_metadata, flatten_if_matrix
from utils.supabase_handler import fetch_sales_data

# Read secrets from Streamlit Cloud
SUPABASE_URL = st.secrets["supabase"]["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["supabase"]["SUPABASE_KEY"]
GEMINI_API_KEY = st.secrets["gcp"]["GEMINI_API_KEY"]

st.title("Excel Updator functionality for Waqt")

uploaded_file = st.file_uploader("Upload your Excel file", type=["xlsx"])
user_prompt = st.text_input("What would you like to do with this file?")

if uploaded_file and user_prompt:
    df = extract_metadata(uploaded_file)
    structured_df = flatten_if_matrix(df)
    
    # Pass GEMINI_API_KEY into Gemini function
    enriched_df = get_prompt_response(structured_df, user_prompt, GEMINI_API_KEY)

    # Pass Supabase credentials into Supabase function
    sales_filled_df = fetch_sales_data(enriched_df, SUPABASE_URL, SUPABASE_KEY)

    st.dataframe(sales_filled_df)

    st.download_button(
        "Download Updated File",
        data=sales_filled_df.to_excel(index=False),
        file_name="updated_file.xlsx"
    )

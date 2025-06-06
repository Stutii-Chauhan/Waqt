import streamlit as st
from utils.gemini_handler import get_prompt_response
from utils.file_processor import extract_metadata, flatten_if_matrix
from utils.supabase_handler import fetch_sales_data

st.title("Smart File Enrichment Platform \U0001F680")

uploaded_file = st.file_uploader("Upload your Excel file", type=["xlsx"])
user_prompt = st.text_input("What would you like to do with this file?")

if uploaded_file and user_prompt:
    df = extract_metadata(uploaded_file)
    structured_df = flatten_if_matrix(df)
    enriched_df = get_prompt_response(structured_df, user_prompt)
    sales_filled_df = fetch_sales_data(enriched_df)

    st.dataframe(sales_filled_df)

    st.download_button(
        "Download Updated File",
        data=sales_filled_df.to_excel(index=False),
        file_name="updated_file.xlsx"
    )

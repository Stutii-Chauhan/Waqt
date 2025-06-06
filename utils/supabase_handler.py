import os
import pandas as pd
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def fetch_sales_data(df: pd.DataFrame) -> pd.DataFrame:
    results = []

    for _, row in df.iterrows():
        match_criteria = {
            "gender_category": row["gender_category"],
            "region": row["region"],
            "product_category": row["product_category"]
        }
        response = supabase.table("Sales_Category_Gender_Region").select("*").match(match_criteria).execute()
        sales = response.data[0]["sales"] if response.data else None
        results.append({**row, "sales": sales})

    return pd.DataFrame(results)

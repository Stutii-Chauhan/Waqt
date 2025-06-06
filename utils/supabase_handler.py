import os
import pandas as pd
from supabase import create_client

SUPABASE_URL = os.getenv("https://futedzabfmyozxcsgqmc.supabase.co")
SUPABASE_KEY = os.getenv("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZ1dGVkemFiZm15b3p4Y3NncW1jIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDkyMTk2OTIsImV4cCI6MjA2NDc5NTY5Mn0.XzEA4TYyeIwfTteg1R5dhobjp0bIR_61-io-59Qc8OM")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def fetch_sales_data(df: pd.DataFrame) -> pd.DataFrame:
    results = []

    for _, row in df.iterrows():
        match_criteria = {}
        for col in ["gender_category", "region", "product_category", "fiscal_year"]:
            if col in row and pd.notna(row[col]):
                match_criteria[col] = row[col]

        if not match_criteria:
            results.append({**row, "sales": None})
            continue

        response = supabase.table("Sales_Category_Gender_Region").select("*").match(match_criteria).execute()
        sales = response.data[0]["sales"] if response.data else None
        results.append({**row, "sales": sales})

    return pd.DataFrame(results)

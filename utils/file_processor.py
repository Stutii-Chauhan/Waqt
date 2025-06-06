import pandas as pd
from io import BytesIO

def extract_metadata(uploaded_file):
    return pd.read_excel(uploaded_file)

def flatten_if_matrix(df: pd.DataFrame) -> pd.DataFrame:
    # Detect and handle matrix-style format generically
    if df.shape[1] > 1 and df.columns[0].lower() not in ["gender_category", "region", "product_category"]:
        df = df.set_index(df.columns[0])
        df_reset = df.reset_index().melt(id_vars=df.index.name, var_name="column_header", value_name="value")
        df_reset.rename(columns={df.index.name: "row_header"}, inplace=True)
        return df_reset.drop(columns=["value"])  # Gemini will infer the correct columns
    return df

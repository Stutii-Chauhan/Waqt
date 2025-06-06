import pandas as pd
from io import BytesIO

def extract_metadata(uploaded_file):
    return pd.read_excel(uploaded_file)

def flatten_if_matrix(df: pd.DataFrame) -> pd.DataFrame:
    if df.columns[0].lower() in ["men", "women", "unisex"]:
        df = df.set_index(df.columns[0])
        df_reset = df.reset_index().melt(id_vars=df.index.name, var_name="region", value_name="value")
        df_reset.rename(columns={df.index.name: "gender_category"}, inplace=True)
        df_reset["product_category"] = "Watches"  # default fallback
        return df_reset.drop(columns=["value"])  # we'll fill this later
    return df

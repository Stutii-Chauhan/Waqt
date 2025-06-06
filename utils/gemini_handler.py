import google.generativeai as genai
import pandas as pd
import json

def get_prompt_response(df: pd.DataFrame, user_prompt: str, api_key: str) -> pd.DataFrame:
    genai.configure(api_key=api_key)

    sample_data = df.head(10).to_dict(orient="records")
    prompt = f"""
You are a smart data transformation agent.

The user uploaded a table with the following data sample:
{json.dumps(sample_data, indent=2)}

User request:
\"{user_prompt}\"

Based on the request and data structure, return a structured list of rows in JSON.
Each row should include fields like gender_category, region, product_category, fiscal_year, etc. if applicable.

Only return the JSON list of rows.
"""

    try:
        model = genai.GenerativeModel("gemini-pro")
        response = model.generate_content(prompt)
        json_start = response.text.find("[")
        json_data = json.loads(response.text[json_start:])
        return pd.DataFrame(json_data)
    except Exception as e:
        print("Gemini Error:", e)
        raise RuntimeError("Gemini response failed. Check API key, prompt, or data.") from e

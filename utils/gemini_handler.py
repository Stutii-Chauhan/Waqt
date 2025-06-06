import os
import google.generativeai as genai
import pandas as pd
import json

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

def get_prompt_response(df: pd.DataFrame, user_prompt: str) -> pd.DataFrame:
    prompt = f"""
You are a smart data transformation agent.

A user uploaded a file with the following structure:

{df.head(10).to_string(index=False)}

User instruction:
\"{user_prompt}\"

Please infer what each row and column represents, and return a structured table in JSON format where each row contains:
- All relevant metadata fields (e.g., gender_category, region, product_category, fiscal_year, etc.)
- No unnecessary fields

Return only the JSON list.
"""
    model = genai.GenerativeModel("gemini-pro")
    response = model.generate_content(prompt)

    try:
        json_start = response.text.find("[")
        json_data = json.loads(response.text[json_start:])
        return pd.DataFrame(json_data)
    except Exception as e:
        raise ValueError("Could not parse Gemini response into DataFrame") from e

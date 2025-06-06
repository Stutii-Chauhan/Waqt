import os
import google.generativeai as genai
import pandas as pd
import json

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

def get_prompt_response(df: pd.DataFrame, user_prompt: str) -> pd.DataFrame:
    prompt = f"""
You are a data transformation agent. A user has uploaded a file and given a request.
User Request: {user_prompt}

The file has the following structure (first 10 rows):
{df.head(10).to_string(index=False)}

Based on the request and this data, return a JSON list of rows with fields:
- gender_category
- region
- product_category

Assume missing values as required. If product_category is not in the data, infer it from the prompt.
"""
    model = genai.GenerativeModel("gemini-pro")
    response = model.generate_content(prompt)

    try:
        json_start = response.text.find("[")
        json_data = json.loads(response.text[json_start:])
        return pd.DataFrame(json_data)
    except Exception as e:
        raise ValueError("Could not parse Gemini response into DataFrame") from e

import requests
from .excel_service import load_dataframe

OLLAMA_API_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "mistral"

def answer_generative_query(file_path: str, query: str) -> str:
    df = load_dataframe(file_path)
    
    # For MVP, send a representative sample of rows
    # Mistral 7B has an 8k context window, keeping it concise
    sample_df = df.head(30)
    data_csv = sample_df.to_csv(index=False)
    
    prompt = f"""
You are an expert data analyst AI assistant helping a user answer questions based on their Excel data.
Here is a sample of the data (in CSV format) to give you context:

{data_csv}

User Question: {query}

Please answer the user's question clearly and concisely based on the data provided. 
If the question asks about data beyond the sample provided, mention that you are only 
analyzing a sample of {len(sample_df)} rows.
"""
    
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False
    }
    
    try:
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=120)
        response.raise_for_status()
        result = response.json()
        return result.get("response", "No response from model.")
    except requests.exceptions.ConnectionError:
        return "Error: Could not connect to local Ollama. Make sure Ollama is running and accessible."
    except Exception as e:
        return f"Error communicating with local Ollama model: {str(e)}"

def generate_pandas_filter(query: str, columns: list) -> str:
    prompt = f"""
You are an expert Python data scientist.
Given the following pandas dataframe columns: {columns}
And the user's query: "{query}"

Write a valid Pandas `df.query()` string to filter the dataframe to answer the user's question.
If the query doesn't require filtering, just output: None
Map the user's terms to the closest matching column names.
ONLY return the query string itself, without quotes around the whole string. No markdown formatting, no explanations.
For example, if the user asks "how many open risks", and columns are ['Status', 'Risk'], output: Status == 'Open'
"""
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False
    }
    try:
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json().get("response", "").strip()
        # Strip code formatting if the LLM includes it
        if result.startswith("```"):
            result = result.split("\n", 1)[-1].rsplit("\n", 1)[0]
        
        result = result.strip()
        if result.startswith("`") and result.endswith("`"):
            result = result[1:-1].strip()
        elif result.startswith('"') and result.endswith('"'):
            result = result[1:-1].strip()
            
        return result
    except Exception:
        return "None"

def generate_graph_config(query: str, columns: list) -> dict:
    prompt = f"""
You are a data visualization assistant.
Given the pandas columns: {columns}
And the user's graph request: "{query}"

Extract the parameters needed to plot this chart.
Output exactly and ONLY a JSON object with the following keys:
- "x_col": the exact name of the column for the x-axis (e.g. categorical grouping). Must be from the given list.
- "y_col": the exact name of the numeric column for the y-axis, or null if counting occurrences.
- "aggregation": one of "count", "sum", "mean", "min", "max".
- "graph_type": one of "bar", "line", "pie".

Example Output:
{{"x_col": "Department", "y_col": null, "aggregation": "count", "graph_type": "bar"}}

DO NOT return any Markdown formatting (no ` ```json ` blocks), only the raw JSON.
"""
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "format": "json"
    }
    import json
    try:
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=30)
        response.raise_for_status()
        result_text = response.json().get("response", "").strip()
        result_json = json.loads(result_text)
        return result_json
    except Exception:
        return {}


import requests
import json
import time

OLLAMA_API_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "mistral"
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

# ---------- Internal helpers ----------

def _ollama_available():
    """Quick check if Ollama is reachable."""
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=2)
        return r.status_code == 200
    except Exception:
        return False


def _call_ollama(prompt: str, format_json: bool = False, timeout: int = 60) -> str:
    """Call the local Ollama API and return the raw text response."""
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False
    }
    if format_json:
        payload["format"] = "json"
    response = requests.post(OLLAMA_API_URL, json=payload, timeout=timeout)
    response.raise_for_status()
    return response.json().get("response", "").strip()


def _call_gemini(prompt: str, api_key: str, timeout: int = 60, max_retries: int = 3) -> str:
    """Call Google Gemini API with retry logic for rate limits."""
    url = f"{GEMINI_BASE_URL}/{GEMINI_MODEL}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    
    for attempt in range(max_retries):
        response = requests.post(url, json=payload, timeout=timeout)
        if response.status_code == 429:
            wait_time = 2 ** (attempt + 1)  # 2s, 4s, 8s
            time.sleep(wait_time)
            continue
        response.raise_for_status()
        result = response.json()
        candidates = result.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts:
                return parts[0].get("text", "").strip()
        return ""
    
    raise Exception("Gemini API rate limit exceeded. Please wait a moment and try again.")


def _call_llm(prompt: str, api_key: str = "", format_json: bool = False, timeout: int = 60) -> str:
    """Try Ollama first, fall back to Gemini if unavailable."""
    if _ollama_available():
        return _call_ollama(prompt, format_json=format_json, timeout=timeout)
    elif api_key:
        return _call_gemini(prompt, api_key, timeout=timeout)
    else:
        raise ConnectionError(
            "Ollama is not running and no Gemini API key is configured. "
            "Please enter your Gemini API key in Settings (sidebar)."
        )


# ---------- Public functions ----------

def answer_generative_query(file_path: str, query: str, api_key: str = "") -> str:
    from .excel_service import load_dataframe
    df = load_dataframe(file_path)

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
    try:
        return _call_llm(prompt, api_key=api_key, timeout=120)
    except ConnectionError as e:
        return str(e)
    except Exception as e:
        return f"Error communicating with AI model: {str(e)}"


def generate_pandas_filter(query: str, columns: list, api_key: str = "") -> str:
    prompt = f"""
You are an expert Python data scientist.
Given the following pandas dataframe columns: {columns}
And the user's query: "{query}"

Write a valid Pandas `df.query()` string to filter the dataframe to answer the user's question.
If the query doesn't require filtering, just output: None
Map the user's terms to the closest matching column names.
CRITICAL MANDATORY RULES:
1. ONLY return the query string itself, without quotes around the whole string. No markdown formatting, no explanations.
2. If a column name contains spaces or special characters, you MUST wrap the column name in backticks (`).
3. The query MUST be a full boolean condition (e.g. `Column Name` == 'Yes' or `Column Name` > 5). DO NOT just return the column name.
For example, if columns are ['Incident Response', 'Status'] and query is "open incidents": `Incident Response` == 'Yes' and Status == 'Open'
"""
    try:
        result = _call_llm(prompt, api_key=api_key, timeout=30)
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


def generate_graph_config(query: str, columns: list, api_key: str = "") -> list:
    """Returns a list of graph config dicts. Each has x_col, y_col, aggregation, graph_type."""
    prompt = f"""
You are a data visualization assistant.
Given the pandas columns: {columns}
And the user's graph request: "{query}"

Extract the parameters needed to plot chart(s) that fully answer the user's request.
If the request involves MULTIPLE aspects or columns (e.g. multiple security controls, comparing several metrics), 
generate MULTIPLE chart configs — one for each relevant aspect.

Output a JSON ARRAY of objects. Each object must have these keys:
- "x_col": the exact column name for the x-axis grouping. Must be from the given list.
- "y_col": the exact column name for the y-axis, or null if counting occurrences.
- "aggregation": one of "count", "sum", "mean", "min", "max".
- "graph_type": one of "bar", "line", "pie".
- "title": a short descriptive title for this specific chart.

Example for a single chart:
[{{"x_col": "Department", "y_col": null, "aggregation": "count", "graph_type": "bar", "title": "Vendors by Department"}}]

Example for multiple charts:
[
  {{"x_col": "Formal InfoSec Policy", "y_col": null, "aggregation": "count", "graph_type": "pie", "title": "InfoSec Policy Coverage"}},
  {{"x_col": "Data Encryption", "y_col": null, "aggregation": "count", "graph_type": "bar", "title": "Data Encryption Methods"}},
  {{"x_col": "Incident Response Plan", "y_col": null, "aggregation": "count", "graph_type": "pie", "title": "Incident Response Coverage"}}
]

DO NOT return any Markdown formatting, only the raw JSON array.
"""
    try:
        result_text = _call_llm(prompt, api_key=api_key, format_json=True, timeout=45)
        if result_text.startswith("```"):
            result_text = result_text.split("\n", 1)[-1].rsplit("\n", 1)[0]
        parsed = json.loads(result_text)
        # Normalize: if LLM returns a single dict, wrap it in a list
        if isinstance(parsed, dict):
            parsed = [parsed]
        if isinstance(parsed, list) and len(parsed) > 0:
            return parsed
        return []
    except Exception:
        return []


def call_generative(prompt: str, api_key: str = "", timeout: int = 60) -> str:
    """Generic generative call used by the dashboard copilot."""
    try:
        return _call_llm(prompt, api_key=api_key, timeout=timeout)
    except ConnectionError as e:
        return str(e)
    except Exception as e:
        return f"Error: {str(e)}"

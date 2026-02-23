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


def _call_gemini(prompt: str, api_key: str, timeout: int = 60, max_retries: int = 3, format_json: bool = False) -> str:
    """Call Google Gemini API with retry logic for rate limits."""
    url = f"{GEMINI_BASE_URL}/{GEMINI_MODEL}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    if format_json:
        payload["generationConfig"] = {"responseMimeType": "application/json"}
    
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
    """Try Ollama first, fall back to Gemini if unavailable or on error."""
    if _ollama_available():
        try:
            return _call_ollama(prompt, format_json=format_json, timeout=timeout)
        except Exception:
            # Ollama timed out or errored — fall back to Gemini
            if api_key:
                return _call_gemini(prompt, api_key, timeout=timeout, format_json=format_json)
            raise
    elif api_key:
        return _call_gemini(prompt, api_key, timeout=timeout, format_json=format_json)
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


def generate_graph_config(query: str, columns: list, api_key: str = "", df=None) -> list:
    """Returns a list of graph config dicts. Each has x_col, y_col, aggregation, graph_type."""
    
    # Build a column reference with sample values
    col_ref = ""
    if df is not None:
        col_lines = []
        for col in columns:
            try:
                samples = df[col].dropna().unique()[:4]
                sample_str = ", ".join([str(s) for s in samples])
                col_lines.append(f"  - \"{col}\" (e.g. {sample_str})")
            except Exception:
                col_lines.append(f"  - \"{col}\"")
        col_ref = "\n".join(col_lines)
    else:
        col_ref = "\n".join([f"  - \"{col}\"" for col in columns])
    
    prompt = f"""
You are a data visualization assistant.
Here are the available columns with sample values:
{col_ref}

User's request: "{query}"

Map the user's request to the EXACT column names listed above.
Choose the BEST visualization for each aspect:

RULES:
1. If a column has only 2-3 unique values (like Yes/No/Partial), use "metric" to show counts.
2. If a column contains dates or time periods, use "line" (trend chart), NEVER "pie".
3. If a column has many categories (5+), use "bar".
4. If a column has 3-6 categories, use "pie".
5. If the request mentions multiple topics, generate MULTIPLE items.

Output a JSON ARRAY. Each object must have:
- "x_col": EXACT column name from the list above (REQUIRED, never null)
- "y_col": column name for y-axis, or null if counting
- "aggregation": "count", "sum", "mean", "min", or "max"
- "graph_type": "bar", "line", "pie", or "metric"
- "title": descriptive title
- "description": 1-2 sentence insight explaining WHY this matters or what the gap/concern is

For "metric" type: x_col is the column to count, the dashboard will show value counts as KPI widgets.

CRITICAL: x_col MUST be one of the exact column names listed above. Never return null for x_col.

DO NOT return Markdown, only raw JSON array.
"""
    try:
        result_text = _call_llm(prompt, api_key=api_key, format_json=True, timeout=45)
        if result_text.startswith("```"):
            result_text = result_text.split("\n", 1)[-1].rsplit("\n", 1)[0]
        parsed = json.loads(result_text)
        # Normalize: if LLM returns a single dict, wrap it in a list
        if isinstance(parsed, dict):
            parsed = [parsed]
        if isinstance(parsed, list):
            # Filter out configs with invalid/null x_col
            valid = [c for c in parsed if c.get("x_col") and c["x_col"] in columns]
            if valid:
                return valid
    except Exception:
        pass
    
    # Fallback: keyword-match columns from the query
    query_lower = query.lower()
    matched_configs = []
    for col in columns:
        col_lower = col.lower()
        # Check if any word in the column name appears in the query
        col_words = [w for w in col_lower.replace("_", " ").split() if len(w) > 3]
        if any(word in query_lower for word in col_words):
            matched_configs.append({
                "x_col": col,
                "y_col": None,
                "aggregation": "count",
                "graph_type": "pie" if len(matched_configs) % 2 == 0 else "bar",
                "title": f"Distribution: {col}"
            })
    
    return matched_configs[:8]  # Cap at 8 charts max


def call_generative(prompt: str, api_key: str = "", timeout: int = 60) -> str:
    """Generic generative call used by the dashboard copilot."""
    try:
        return _call_llm(prompt, api_key=api_key, timeout=timeout)
    except ConnectionError as e:
        return str(e)
    except Exception as e:
        return f"Error: {str(e)}"

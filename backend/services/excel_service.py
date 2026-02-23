import pandas as pd

def load_dataframe(file_path: str) -> pd.DataFrame:
    return pd.read_excel(file_path)

def load_excel_and_get_summary(file_path: str) -> dict:
    df = load_dataframe(file_path)
    return {
        "columns": df.columns.tolist(),
        "rows_count": len(df)
    }

def is_count_query(query: str) -> bool:
    query_lower = query.lower()
    return any(kw in query_lower for kw in ["how many", "count", "number of", "total"])

def run_count_query(file_path: str, query: str) -> str:
    # MVP: placeholder logic. Next step: integrate Gemini to generate pandas filter!
    df = load_dataframe(file_path)
    return f"Total rows based on query: {len(df)}. (Placeholder logic - implementing real count soon)"

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

def is_graph_query(query: str) -> bool:
    query_lower = query.lower()
    return any(kw in query_lower for kw in ["plot", "graph", "chart", "visualize", "draw"])

def run_count_query(file_path: str, query: str) -> str:
    df = load_dataframe(file_path)
    from .llm_service import generate_pandas_filter
    
    filter_string = generate_pandas_filter(query, df.columns.tolist())
    
    if filter_string and filter_string.lower() != "none":
        try:
            # Some safety/cleanup for common LLM query string errors
            # E.g. replacing '==' with '==' if already correct, but just in case
            filtered_df = df.query(filter_string)
            return f"Count based on filter `{filter_string}`: {len(filtered_df)}"
        except Exception as e:
            return f"Could not count. LLM generated invalid filter: `{filter_string}`. Error: {str(e)}"
    
    return f"Total rows in dataset: {len(df)} (No specific filter detected)"

def run_graph_query(file_path: str, query: str) -> dict:
    df = load_dataframe(file_path)
    from .llm_service import generate_graph_config
    
    try:
        config = generate_graph_config(query, df.columns.tolist())
        # The LLM gives us a dict specifying x_col, y_col, aggregation, graph_type
        # e.g., {'x_col': 'Department', 'y_col': None, 'aggregation': 'count', 'graph_type': 'bar'}
        
        if not config:
            return {"error": "Could not understand the graph request parameters."}
            
        x_col = config.get("x_col")
        y_col = config.get("y_col") 
        aggr = config.get("aggregation", "count")
        graph_type = config.get("graph_type", "bar")
        
        if x_col not in df.columns:
            return {"error": f"Column '{x_col}' not found in data."}
            
        # Execute grouping safely in pandas and return the serializable payload
        if aggr == 'count':
            grouped = df.groupby(x_col).size().reset_index(name='count')
            y_col_out = 'count'
        else:
            if not y_col or y_col not in df.columns:
                return {"error": f"A valid numeric y_col is required for aggregation '{aggr}'"}
            grouped = df.groupby(x_col)[y_col].agg(aggr).reset_index()
            y_col_out = y_col
            
        # Convert df to dictionary format that Streamlit can easily plot: 
        # {'x': [List of X values], 'y': [List of Y values], 'type': 'bar'}
        response_data = {
            "x": grouped[x_col].tolist(),
            "y": grouped[y_col_out].tolist(),
            "x_label": x_col,
            "y_label": y_col_out,
            "graph_type": graph_type
        }
        return response_data
    except Exception as e:
        return {"error": f"Error generating graph: {str(e)}"}

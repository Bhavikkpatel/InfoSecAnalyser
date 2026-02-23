import os
import google.generativeai as genai
from dotenv import load_dotenv
from .excel_service import load_dataframe

load_dotenv()

# Configure Gemini
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
    
model = genai.GenerativeModel('gemini-1.5-flash')

def answer_generative_query(file_path: str, query: str) -> str:
    if not api_key:
        return "Error: GEMINI_API_KEY is not set."
        
    df = load_dataframe(file_path)
    
    # For MVP, send schema and a sample of rows, or convert interesting rows to string
    # Warning: Don't send massive dataframes directly.
    # Let's send the first 50 rows as a representative sample for general questions.
    sample_df = df.head(50)
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
    
    response = model.generate_content(prompt)
    return response.text

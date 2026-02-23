import os
import shutil
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from .services.excel_service import load_excel_and_get_summary, is_count_query, run_count_query
from .services.llm_service import answer_generative_query

router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

class QueryRequest(BaseModel):
    filename: str
    query: str

@router.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename.endswith(('.xls', '.xlsx')):
        raise HTTPException(status_code=400, detail="Only Excel files are supported")
    
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    try:
        summary = load_excel_and_get_summary(file_path)
        return {"filename": file.filename, "message": "File uploaded successfully", "summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing Excel file: {str(e)}")

@router.post("/query/")
async def query_excel(request: QueryRequest):
    file_path = os.path.join(UPLOAD_DIR, request.filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
        
    if is_count_query(request.query):
        try:
            result = run_count_query(file_path, request.query)
            return {"answer": result, "type": "count"}
        except Exception as e:
            return {"answer": f"Error: {str(e)}", "type": "error"}
    else:
        try:
            answer = answer_generative_query(file_path, request.query)
            return {"answer": answer, "type": "generative"}
        except Exception as e:
            return {"answer": f"Error: {str(e)}", "type": "error"}

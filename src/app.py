from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
import uvicorn
import shutil
import os
import io

from src.models import AssignmentType
from src.ingestion.loader import IngestionEngine
from src.ingestion.rubric_parser import RubricParser
from src.grading.evaluator import GradingEngine

app = FastAPI(title="Grader Agent")

# Mount static folders
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
static_dir = os.path.join(BASE_DIR, "static")
templates_dir = os.path.join(BASE_DIR, "templates")

# Mount static folders
app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=templates_dir)

# Initialize Engines
ingestion = IngestionEngine()
grader = GradingEngine()

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/viewer", response_class=HTMLResponse)
async def viewer(request: Request):
    return templates.TemplateResponse("pdf_viewer.html", {"request": request})

@app.post("/grade")
async def grade_assignment(
    mode: str = Form(...),
    submission_file: UploadFile = File(...),
    rubric_file: UploadFile = File(...)
):
    # 1. Save upload files 
    # Persist submission to static/uploads so frontend can access it
    upload_dir = os.path.join(static_dir, "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    temp_dir = os.path.join(BASE_DIR, "temp_uploads")
    os.makedirs(temp_dir, exist_ok=True)
    
    sub_filename = f"{submission_file.filename}"
    sub_path = os.path.join(upload_dir, sub_filename)
    rub_path = os.path.join(temp_dir, rubric_file.filename)
    
    try:
        with open(sub_path, "wb") as f:
            shutil.copyfileobj(submission_file.file, f)
        with open(rub_path, "wb") as f:
            shutil.copyfileobj(rubric_file.file, f)
            
        # 2. Ingest
        content = ingestion.load_submission(sub_path)
        rubric_obj = RubricParser.parse(rub_path)
        
        # 3. Grade
        result = grader.evaluate(content, rubric_obj, mode, student_id=submission_file.filename)
        
        # Read raw rubric content
        with open(rub_path, "r", encoding="utf-8", errors="replace") as f:
            rubric_content = f.read()

        return {
            "result": result,
            "submission_content": content,
            "rubric_content": rubric_content,
            "file_url": f"/static/uploads/{sub_filename}",
            "file_type": submission_file.filename.split('.')[-1].lower()
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Cleanup rubric only
        if os.path.exists(rub_path): os.remove(rub_path)


# Validating Canvas Import
from src.integrations.canvas_client import CanvasClient
from pydantic import BaseModel

class CanvasConnectRequest(BaseModel):
    api_url: str
    api_key: str

class CanvasImportRequest(BaseModel):
    course_id: int
    assignment_id: int
    api_url: str
    api_key: str

@app.post("/canvas/connect")
async def connect_canvas(req: CanvasConnectRequest):
    try:
        client = CanvasClient(req.api_url, req.api_key)
        courses = client.get_courses()
        return {"status": "success", "courses": courses}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/canvas/assignments/{course_id}")
async def get_canvas_assignments(course_id: int, api_url: str, api_key: str):
    try:
        client = CanvasClient(api_url, api_key)
        assignments = client.get_assignments(course_id)
        return assignments
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/canvas/import")
async def import_canvas_submissions(req: CanvasImportRequest):
    """
    Imports submissions from Canvas. 
    For prototype: We just list them and return metadata. 
    In real app: We'd download files to temp_uploads.
    """
    try:
        client = CanvasClient(req.api_url, req.api_key)
        submissions = client.get_submissions(req.course_id, req.assignment_id)
        
        # Simplified metadata for UI
        subs_meta = []
        for sub in submissions:
            # Check for attachments or text entry
            content_type = "unknown"
            if hasattr(sub, 'attachments') and sub.attachments:
                content_type = "file"
            elif hasattr(sub, 'body') and sub.body:
                content_type = "text"
                
            student_name = "Unknown"
            if hasattr(sub, 'user') and hasattr(sub.user, 'name'):
                student_name = sub.user['name']
            elif hasattr(sub, 'user_id'):
                 student_name = f"Student {sub.user_id}"

            subs_meta.append({
                "id": sub.id,
                "student_name": student_name,
                "content_type": content_type,
                "workflow_state": sub.workflow_state
            })
            
        return {"status": "success", "submissions": subs_meta}
    except Exception as e:
        print(f"Canvas Import Error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


class CanvasPostGradeRequest(BaseModel):
    course_id: int
    assignment_id: int
    student_id: int
    grade: float
    comment: str
    api_url: str
    api_key: str

@app.post("/canvas/post_grade")
async def post_canvas_grade(req: CanvasPostGradeRequest):
    try:
        client = CanvasClient(req.api_url, req.api_key)
        client.post_grade(req.course_id, req.assignment_id, req.student_id, req.grade, req.comment)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)

import shutil
import uuid
import os
import asyncio
import json
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from src.persistence import Persistence, SubmissionMetadata
from src.ingestion.loader import IngestionEngine
from src.ingestion.rubric_parser import RubricParser
from src.grading.evaluator import GradingEngine
from src.models import AssignmentType, Rubric

app = FastAPI(title="Grader Agent API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Persistence
db = Persistence()

# Engines
ingestion = IngestionEngine()
grader = GradingEngine()
DEFAULT_RUBRIC_PATH = "test_rubric.txt" 

# Templates
templates = Jinja2Templates(directory="templates")

# Serve static files (uploaded PDFs)
app.mount("/files", StaticFiles(directory=db.uploads_dir), name="files")
# Also serve static assets if any (css/js) - making a static dir
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- UI Routes ---
@app.get("/")
def read_root():
    return RedirectResponse(url="/dashboard")

@app.get("/dashboard")
def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/review/{sub_id}")
def review(request: Request, sub_id: str):
    sub = db.get_submission(sub_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    ext = os.path.splitext(sub.filename)[1]
    stored_filename = f"{sub.id}{ext}"
    
    # Ensure file is available locally for the viewer
    # get_file_path will checking existence or download from Supabase
    db.get_file_path(stored_filename)
    
    return templates.TemplateResponse("review.html", {"request": request, "sub_id": sub_id, "filename": stored_filename})

@app.get("/viewer_frame")
def viewer_frame(request: Request):
    return templates.TemplateResponse("pdf_viewer.html", {"request": request})


# --- Background Tasks ---
def save_detailed_result(sub_id: str, result: GradingEngine): 
    # Store detailed result in a separate file
    results_dir = os.path.join(db.data_dir, "results")
    os.makedirs(results_dir, exist_ok=True)
    path = os.path.join(results_dir, f"{sub_id}.json")
    with open(path, 'w') as f:
        f.write(result.json())

def load_detailed_result(sub_id: str) -> Optional[dict]:
    path = os.path.join(db.data_dir, "results", f"{sub_id}.json")
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return None

def process_grading_task(sub_id: str, file_path: str, mode: str):
    # Retrieve latest metadata to check for rubric_path (since it might not be passed directly if we only use args)
    # Actually, simplest is to re-fetch metadata inside or pass it.
    # The current persistent db is thread-safe enough for this simple read.
    sub = db.get_submission(sub_id)
    if not sub:
        print(f"Submission {sub_id} not found during processing")
        return
    print(f"Starting grading for {sub_id}...")
    # Ensure file is available locally (downloads from Supabase if needed)
    local_path = db.get_file_path(file_path)
    
    if not local_path:
        print(f"File not found or failed to download: {file_path}")
        return

    try:
        db.update_status(sub_id, "PROCESSING")
        
        # Load content
        content = ingestion.load_submission(local_path)
        
        # Load rubric
        if hasattr(sub, 'rubric_path') and sub.rubric_path:
             # Rubric might also need downloading!
             rubric_path = db.get_file_path(sub.rubric_path)
             if not rubric_path:
                 print("Failed to download custom rubric")
                 rubric_path = DEFAULT_RUBRIC_PATH
             else:
                 print(f"Using custom rubric: {rubric_path}")
        else:
             rubric_path = DEFAULT_RUBRIC_PATH
             
        rubric_obj = RubricParser.parse(rubric_path)
        
        # Grade
        result = grader.evaluate(content, rubric_obj, mode, student_id=sub_id)
        
        # Save details
        save_detailed_result(sub_id, result)

        # Update DB
        db.update_status(
            sub_id, 
            status="GRADED", 
            score=result.total_score, 
            max_score=result.max_score, 
            feedback=result.feedback
        )
        print(f"Finished grading {sub_id}")
        
    except Exception as e:
        print(f"Error grading {sub_id}: {e}")
        import traceback
        traceback.print_exc()
        db.update_status(sub_id, "ERROR", feedback=str(e))

# --- Endpoints ---

@app.post("/api/upload")
async def upload_files(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...), 
    mode: str = "essay",
    rubric: Optional[UploadFile] = File(None)
):
    rubric_path_ref = None
    if rubric:
        # Save rubric
        rubric_filename = f"rubric_{uuid.uuid4()}.txt"
        content = await rubric.read()
        rubric_path_ref = db.save_file(content, rubric_filename)

    uploaded_ids = []
    for file in files:
        sub_id = str(uuid.uuid4())
        ext = os.path.splitext(file.filename)[1]
        filename = f"{sub_id}{ext}"
        
        # Save file via persistence layer
        content = await file.read()
        saved_path_ref = db.save_file(content, filename)
            
        metadata = SubmissionMetadata(
            id=sub_id,
            filename=file.filename, # Original name
            upload_time=datetime.now().isoformat(),
            assignment_type=mode,
            # Placeholder student ID logic
            student_id=os.path.splitext(file.filename)[0],
            rubric_path=rubric_path_ref 
        )
        db.add_submission(metadata)
        uploaded_ids.append(sub_id)
        
        # Trigger background processing
        # We pass the saved_path_ref (which is either a local path or filename)
        # The background task will resolve it.
        background_tasks.add_task(process_grading_task, sub_id, saved_path_ref, mode)
        
    return {"message": f"Uploaded {len(files)} files", "ids": uploaded_ids}

@app.get("/api/submissions", response_model=List[SubmissionMetadata])
def list_submissions():
    return db.get_all()

@app.get("/api/submissions/{sub_id}")
def get_submission_details(sub_id: str):
    meta = db.get_submission(sub_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    details = load_detailed_result(sub_id)
    return {
        "metadata": meta,
        "details": details
    }

class UpdateScoreRequest(BaseModel):
    score: float
    feedback: str

@app.put("/api/submissions/{sub_id}")
def update_submission(sub_id: str, req: UpdateScoreRequest):
    meta = db.get_submission(sub_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    # Update metadata
    db.update_status(sub_id, meta.status, score=req.score, feedback=req.feedback)
    
    # Update details file if it exists
    details = load_detailed_result(sub_id)
    if details:
        details['total_score'] = req.score
        details['feedback'] = req.feedback
        # We don't necessarily update criteria scores here unless UI sends them, 
        # but for now we just override the top level.
        
        results_dir = os.path.join(db.data_dir, "results")
        path = os.path.join(results_dir, f"{sub_id}.json")
        with open(path, 'w') as f:
            json.dump(details, f)

    return {"message": "Updated"}

@app.post("/api/submissions/{sub_id}/process")
async def process_submission(sub_id: str, background_tasks: BackgroundTasks):
    sub = db.get_submission(sub_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    # The file_path for process_grading_task should be the identifier used by db.save_file
    # which is typically the filename itself (e.g., "{sub_id}.ext")
    # We can reconstruct this from metadata.
    file_identifier = f"{sub.id}{os.path.splitext(sub.filename)[1]}"
    
    background_tasks.add_task(process_grading_task, sub_id, file_identifier, sub.assignment_type)
    return {"message": "Grading queued"}

@app.post("/api/process-all")
async def process_all(background_tasks: BackgroundTasks):
    subs = db.get_all()
    count = 0
    for sub in subs:
        if sub.status in ["UPLOADED", "ERROR"]:
            # Re-run logic...
            # Warning: found_file calculation in original code was:
            # found_file = os.path.join(db.uploads_dir, f"{sub.id}.pdf") ...
            # We should update this to use db.get_file_path logic or just reconstruct the filename if we know the convention.
            # Our convention: filename is stored as "{id}.ext" in `saved_path_ref` passed to background task.
            # BUT, we didn't store the extension in metadata explicitly (except in filename).
            # Let's try to infer it from the 'rubric_path' or just check valid extensions.
            
            # Actually, process_grading_task expects a path/identifier.
            # Since we store uniform filenames in uploads (sub_id + ext), we can try to find it.
            
            # Simple fix: Use the original filename extension from metadata (risky if modified) 
            # OR check local/remote.
            
            # Let's rely on db.uploads_dir check for legacy local or try standard extensions.
            # possible_exts = ['.pdf', '.txt', '.ipynb', '.docx'] # This comment block is from the instruction, not actual code.
            target_ext = os.path.splitext(sub.filename)[1]
            
            # Construct the identifier we likely used
            file_identifier = f"{sub.id}{target_ext}"
            
            background_tasks.add_task(process_grading_task, sub.id, file_identifier, sub.assignment_type)
            count += 1
    return {"message": f"Queued {count} submissions for grading"}

@app.get("/api/export")
def export_csv():
    import csv
    import io
    from fastapi.responses import StreamingResponse
    
    subs = db.get_all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Student ID", "Filename", "Status", "Score", "Max Score", "Feedback"])
    
    for sub in subs:
        writer.writerow([
            sub.student_id,
            sub.filename,
            sub.status,
            sub.score if sub.score is not None else "",
            sub.max_score if sub.max_score is not None else "",
            sub.feedback_summary if sub.feedback_summary is not None else ""
        ])
        
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=grades.csv"}
    )


@app.get("/")
def read_root():
    return {"message": "Grader Agent API is running"}

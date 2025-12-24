import json
import os
from typing import List, Optional, Dict
from datetime import datetime
from pydantic import BaseModel, Field

class SubmissionMetadata(BaseModel):
    id: str
    filename: str
    upload_time: str
    status: str = "UPLOADED" # UPLOADED, PROCESSING, GRADED, ERROR
    score: Optional[float] = None
    max_score: Optional[float] = None
    feedback_summary: Optional[str] = None
    assignment_type: str = "essay" # Default
    student_id: str = "Unknown"
    rubric_path: Optional[str] = None

class Persistence:
    def __init__(self, data_dir: str = "data"):
        # Check for Vercel environment
        if os.environ.get("VERCEL"):
            self.data_dir = "/tmp/data"
        else:
            self.data_dir = data_dir
            
        self.submissions_file = os.path.join(self.data_dir, "submissions.json")
        self.uploads_dir = os.path.join(self.data_dir, "uploads")
        
        # Ensure directories exist (critical for /tmp which is empty on start)
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.uploads_dir, exist_ok=True)
        
        self._ensure_db()

    def _ensure_db(self):
        if not os.path.exists(self.submissions_file):
            with open(self.submissions_file, 'w') as f:
                json.dump([], f)

    def _load(self) -> List[dict]:
        with open(self.submissions_file, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []

    def _save(self, data: List[dict]):
        with open(self.submissions_file, 'w') as f:
            json.dump(data, f, indent=2)

    def add_submission(self, metadata: SubmissionMetadata):
        data = self._load()
        # Check if exists, update if so (rare for id collision unless intent)
        existing = next((item for item in data if item['id'] == metadata.id), None)
        if existing:
            data.remove(existing)
        data.append(metadata.dict())
        self._save(data)

    def get_all(self) -> List[SubmissionMetadata]:
        data = self._load()
        return [SubmissionMetadata(**item) for item in data]

    def get_submission(self, sub_id: str) -> Optional[SubmissionMetadata]:
        data = self._load()
        item = next((i for i in data if i['id'] == sub_id), None)
        if item:
            return SubmissionMetadata(**item)
        return None

    def update_status(self, sub_id: str, status: str, score: float = None, max_score: float = None, feedback: str = None):
        data = self._load()
        for item in data:
            if item['id'] == sub_id:
                item['status'] = status
                if score is not None: item['score'] = score
                if max_score is not None: item['max_score'] = max_score
                if feedback is not None: item['feedback_summary'] = feedback
                break
        self._save(data)

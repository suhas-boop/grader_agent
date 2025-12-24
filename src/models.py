from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class AssignmentType(str, Enum):
    ESSAY = "essay"
    QA = "qa"
    MC = "mc"
    CODING = "coding"

class RubricCriteria(BaseModel):
    name: str
    description: str
    max_points: float

class Rubric(BaseModel):
    criteria: List[RubricCriteria]
    total_points: float

class Submission(BaseModel):
    student_id: str
    content: Any  # Subtypes will handle specific content types
    file_path: Optional[str] = None

class GradingFeedback(BaseModel):
    score: float
    feedback: str
    citations: List[str] = Field(default_factory=list)
    criteria_scores: Dict[str, float] = Field(default_factory=dict)

class GradingResult(BaseModel):
    submission_id: str
    student_id: str
    assignment_type: AssignmentType
    total_score: float
    max_score: float
    feedback: str
    detailed_results: Optional[List[GradingFeedback]] = None
    raw_response: Optional[str] = None # For debugging LLM output

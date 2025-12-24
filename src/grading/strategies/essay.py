from src.grading.strategy import GradingStrategy
from src.models import GradingResult, Rubric, AssignmentType, GradingFeedback
from src.utils.llm_client import LLMClient
import json

class EssayGradingStrategy(GradingStrategy):
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def grade(self, content: str, rubric: Rubric, student_id: str) -> GradingResult:
        print(f"DEBUG: Grading essay for {student_id}...")
        
        # 1. Construct Prompt
        rubric_str = "\n".join([f"- {c.name}: {c.description} (Max: {c.max_points})" for c in rubric.criteria])
        
        prompt = f"""
        You are an expert academic grader. Grade the following essay based strictly on the provided rubric.
        
        ## RUBRIC
        {rubric_str}
        
        ## STUDENT ESSAY
        {content}
        
        ## INSTRUCTIONS
        1. Evaluate the essay for each rubric criteria.
        2. Provide a specific score and constructive feedback for each.
        3. Identify EXACT QUOTES from the essay that support your evaluation for each criteria. These must be verbatim strings from the text.
        4. Calculate the total score.
        5. Provide an overall summary feedback.
        """

        # 2. Call LLM (expecting structure match)
        # Note: We are mocking the structure return for now by asking for JSON and parsing into our internal Pydantic model
        # ideally we'd have a specific Pydantic model just for the LLM output 
        
        response_model = GradingResult # Reuse the main model for simplicity or define a specific localized one
        
        # For this prototype, let's ask for the raw evaluation and map it manually or try the direct generate_json
        # We need to ensure the LLM output matches the GradingResult fields: 
        # submission_id, student_id, assignment_type, total_score, max_score, feedback, detailed_results
        
        # To make it easier for the LLM, let's define a simpler intermediate schema
        from pydantic import BaseModel
        from typing import List, Dict
        
        class LLMEvaluation(BaseModel):
            criteria_scores: Dict[str, float]
            criteria_feedback: Dict[str, str]
            criteria_citations: Dict[str, List[str]]
            overall_feedback: str
            
        result_content = self.llm.generate_json(prompt, LLMEvaluation)
        
        if not result_content:
            return GradingResult(
                submission_id="error",
                student_id=student_id,
                assignment_type=AssignmentType.ESSAY,
                total_score=0,
                max_score=rubric.total_points,
                feedback="Error generating grade from LLM."
            )

        # 3. Map to Domain Model
        detailed_results = []
        total_score = 0.0
        
        for criterion in rubric.criteria:
            score = result_content.criteria_scores.get(criterion.name, 0.0)
            feedback = result_content.criteria_feedback.get(criterion.name, "")
            citations = result_content.criteria_citations.get(criterion.name, [])
            total_score += score
            
            detailed_results.append(GradingFeedback(
                score=score,
                feedback=feedback,
                citations=citations,
                criteria_scores={criterion.name: score}
            ))

        return GradingResult(
            submission_id="generated_id", # Placeholder
            student_id=student_id,
            assignment_type=AssignmentType.ESSAY,
            total_score=total_score,
            max_score=rubric.total_points,
            feedback=result_content.overall_feedback,
            detailed_results=detailed_results
        )

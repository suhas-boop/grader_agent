from src.grading.strategy import GradingStrategy
from src.models import GradingResult, Rubric, AssignmentType, GradingFeedback
from src.utils.llm_client import LLMClient
import json

class EssayGradingStrategy(GradingStrategy):
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def grade(self, content: str, rubric: Rubric, student_id: str) -> GradingResult:
        print(f"DEBUG: Content Length: {len(content)}")
        
        # 1. Construct Prompt with Ephemeral IDs
        # We assign an ID like "id_0", "id_1" to each criterion for reliable matching
        criteria_map = {f"id_{i}": c for i, c in enumerate(rubric.criteria)}
        
        rubric_str = "\n".join([f"- ID: id_{i} | Name: {c.name}: {c.description} (Max: {c.max_points})" for i, c in enumerate(rubric.criteria)])
        
        prompt = f"""
        You are an expert academic grader. Grade the following essay based strictly on the provided rubric.
        
        ## RUBRIC
        {rubric_str}
        
        ## STUDENT ESSAY
        {content}
        
        ## INSTRUCTIONS
        1. Evaluate the essay for EVERY rubric criteria listed above. Do not skip any.
        2. You MUST use the associated "ID" (e.g. id_0) for each evaluation item.
        3. Provide a specific score and constructive feedback for each.
        4. Identify EXACT QUOTES from the essay that support your evaluation for each criteria. These must be verbatim strings from the text.
        5. Calculate the total score.
        6. Provide an overall summary feedback.
        """

        # 2. Call LLM (expecting structure match)
        
        from pydantic import BaseModel, ConfigDict
        from typing import List
        
        class CriterionEval(BaseModel):
            criteria_id: str
            score: float
            feedback: str
            citations: List[str]
            model_config = ConfigDict(extra='forbid')

        class LLMEvaluation(BaseModel):
            criteria_evaluations: List[CriterionEval]
            overall_feedback: str
            model_config = ConfigDict(extra='forbid')
            
        result_content = self.llm.generate_json(prompt, LLMEvaluation)

        # Debug: Log returned IDs
        try:
             if result_content:
                 ids = [e.criteria_id for e in result_content.criteria_evaluations]
                 with open("debug_llm_ids.txt", "w") as f:
                     f.write(str(ids))
             else:
                 with open("debug_llm_ids.txt", "w") as f:
                     f.write("None returned")
        except Exception as e:
             print(f"Error logging ids: {e}")
        
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
        
        # Helper to find eval by ID
        def find_eval(cid):
             for e in result_content.criteria_evaluations:
                 if e.criteria_id == cid: return e
             return None

        from src.models import CriterionScore

        for cid, criterion in criteria_map.items():
            eval_item = find_eval(cid)
            score = eval_item.score if eval_item else 0.0
            feedback = eval_item.feedback if eval_item else "No feedback provided."
            citations = eval_item.citations if eval_item else []
            
            total_score += score
            
            detailed_results.append(GradingFeedback(
                score=score,
                feedback=feedback,
                citations=citations,
                criteria_scores=[CriterionScore(criteria_name=criterion.name, score=score)]
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

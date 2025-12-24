from src.grading.strategy import GradingStrategy
from src.models import GradingResult, Rubric, AssignmentType, GradingFeedback
from src.utils.llm_client import LLMClient
import sys
import io
import contextlib

class CodeGradingStrategy(GradingStrategy):
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def grade(self, content: str, rubric: Rubric, student_id: str) -> GradingResult:
        print(f"DEBUG: Grading Coding assignment for {student_id}...")
        
        # content comes from IngestionEngine. 
        # For Notebooks, it's a string with "CODE:\n..." and "MARKDOWN:\n..." blocks.
        # We need to extract just the code for execution, or usage.
        
        code_lines = []
        full_context = "" # Code + Markdowns for LLM
        
        lines = content.split('\n')
        in_code_block = False
        
        current_block = []
        
        for line in lines:
            if line.startswith("CODE:"):
                in_code_block = True
                continue
            elif line.startswith("MARKDOWN:"):
                in_code_block = False
                continue
            
            if in_code_block:
                code_lines.append(line)
            
            full_context += line + "\n"
            
        executable_code = "\n".join(code_lines)
        
        # 1. Execution (Simple/Unsafe for Prototype)
        # We capture stdout checking for errors
        execution_output = ""
        execution_error = ""
        
        f = io.StringIO()
        try:
            with contextlib.redirect_stdout(f):
                # Using a fresh dictionary for locals/globals to catch defined vars
                exec_globals = {}
                exec(executable_code, exec_globals)
            execution_output = f.getvalue()
        except Exception as e:
            execution_error = str(e)
            
        print(f"DEBUG: Execution Output: {execution_output[:100]}...")
        if execution_error:
            print(f"DEBUG: Execution Error: {execution_error}")

        # 2. LLM Evaluation
        # We send Code + Output + Rubric
        
        prompt = f"""
        You are an expert Computer Science TA. Grade the following coding assignment.
        
        ## RUBRIC
        {rubric.json()}
        
        ## STUDENT CODE
        ```python
        {executable_code}
        ```
        
        ## EXECUTION OUTPUT
        {execution_output}
        
        ## EXECUTION ERROR (If any)
        {execution_error}
        
        ## INSTRUCTIONS
        1. Check if the code runs successfully and produces expected outputs (implied by rubric).
        2. Check code quality, style, and logic.
        3. Provide structured grading feedback.
        """
        
        # Reuse the schema-based generation from Essay strategy concept
        from pydantic import BaseModel
        from typing import Dict
        class LLMEvaluation(BaseModel):
            criteria_scores: Dict[str, float]
            criteria_feedback: Dict[str, str]
            overall_feedback: str
            
        result_content = self.llm.generate_json(prompt, LLMEvaluation)
        
        if not result_content:
             return GradingResult(
                submission_id="error",
                student_id=student_id,
                assignment_type=AssignmentType.CODING,
                total_score=0,
                max_score=rubric.total_points,
                feedback="Error generating grade from LLM."
            )

        detailed_results = []
        total_score = 0.0
        
        for criterion in rubric.criteria:
            score = result_content.criteria_scores.get(criterion.name, 0.0)
            feedback = result_content.criteria_feedback.get(criterion.name, "")
            total_score += score
            
            detailed_results.append(GradingFeedback(
                score=score,
                feedback=feedback,
                criteria_scores={criterion.name: score}
            ))

        return GradingResult(
            submission_id="generated_code_id",
            student_id=student_id,
            assignment_type=AssignmentType.CODING,
            total_score=total_score,
            max_score=rubric.total_points,
            feedback=result_content.overall_feedback,
            detailed_results=detailed_results
        )

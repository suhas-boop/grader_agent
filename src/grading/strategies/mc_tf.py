from src.grading.strategy import GradingStrategy
from src.models import GradingResult, Rubric, AssignmentType, GradingFeedback
import json

class MCTFGradingStrategy(GradingStrategy):
    """
    Rule-based grading for Multiple Choice and True/False.
    Expects submission content to be a JSON string or dict mapping Question ID -> Answer.
    Expects Rubric to contain the answer key in criteria description or a separate key field (simplified here).
    """
    
    def grade(self, content: str, rubric: Rubric, student_id: str) -> GradingResult:
        print(f"DEBUG: Grading MC/TF for {student_id}...")
        
        # 1. Parse Submission
        try:
            # Flexible parsing: Try JSON, else assume line-separated "Q1: A" format
            if content.strip().startswith('{'):
                answers = json.loads(content)
            else:
                answers = {}
                for line in content.split('\n'):
                    if ':' in line:
                        q, a = line.split(':', 1)
                        answers[q.strip()] = a.strip()
        except Exception as e:
            return GradingResult(
                submission_id="error",
                student_id=student_id,
                assignment_type=AssignmentType.MC,
                total_score=0,
                max_score=rubric.total_points,
                feedback=f"Failed to parse submission: {str(e)}"
            )

        # 2. Grade against Rubric (which acts as Answer Key)
        # We assume RubricCriteria.name is the Question ID and Description contains the correct answer.
        # This is a simplification for the prototype.
        
        detailed_results = []
        total_score = 0.0
        
        correct_count = 0
        
        for criterion in rubric.criteria:
            qid = criterion.name
            expected_answer = criterion.description.strip() # Assuming description IS the answer key
            student_answer = answers.get(qid, "").strip()
            
            # Simple exact match (case insensitive)
            is_correct = student_answer.lower() == expected_answer.lower()
            
            score = criterion.max_points if is_correct else 0.0
            total_score += score
            if is_correct: correct_count += 1
            
            feedback = "Correct" if is_correct else f"Incorrect. Expected: {expected_answer}, Got: {student_answer}"
            
            detailed_results.append(GradingFeedback(
                score=score,
                feedback=feedback,
                criteria_scores={qid: score}
            ))

        return GradingResult(
            submission_id="generated_mc_id",
            student_id=student_id,
            assignment_type=AssignmentType.MC,
            total_score=total_score,
            max_score=rubric.total_points,
            feedback=f"Graded {len(rubric.criteria)} questions. Correct: {correct_count}/{len(rubric.criteria)}.",
            detailed_results=detailed_results
        )

from src.models import AssignmentType, Rubric, GradingResult
from src.grading.strategies.essay import EssayGradingStrategy
from src.grading.strategies.mc_tf import MCTFGradingStrategy
from src.grading.strategies.coding import CodeGradingStrategy
from src.utils.llm_client import LLMClient

class GradingEngine:
    """Main grading engine that dispatches to specific strategies."""
    
    def __init__(self):
        self.llm_client = LLMClient()
        self.strategies = {
            AssignmentType.ESSAY: EssayGradingStrategy(self.llm_client),
            AssignmentType.MC: MCTFGradingStrategy(),
            AssignmentType.QA: EssayGradingStrategy(self.llm_client),
            AssignmentType.CODING: CodeGradingStrategy(self.llm_client),
        }

    def evaluate(self, content: str, rubric: Rubric, mode: str, student_id: str = "student_default") -> GradingResult:
        """
        Evaluates the submission based on the mode.
        """
        assignment_type = AssignmentType(mode)
        strategy = self.strategies.get(assignment_type)
        
        if not strategy:
            raise ValueError(f"No strategy found for assignment type: {mode}")
            
        return strategy.grade(content, rubric, student_id)

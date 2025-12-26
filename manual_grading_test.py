
import os
import sys
sys.path.append(os.getcwd())

from src.utils.llm_client import LLMClient
from src.grading.strategies.essay import EssayGradingStrategy
from src.models import Rubric, RubricCriteria

def test_grading():
    print("Initializing components...")
    client = LLMClient()
    strategy = EssayGradingStrategy(client)
    
    # Mock Rubric
    rubric = Rubric(
        criteria=[
            RubricCriteria(name="Q1", description="Overview", max_points=10),
            RubricCriteria(name="Q2", description="Learnings", max_points=10)
        ],
        total_points=20
    )
    
    # Mock Content
    content = """
    My internship was great. I worked 400 hours as an ESG intern.
    Q2: I learned about carbon emissions and B-Corp certification. 
    It was surprising how tracking scopes works.
    """
    
    print("Running grade()...")
    result = strategy.grade(content, rubric, "student_123")
    
    print("\n--- Result ---")
    print(f"Total Score: {result.total_score}")
    for item in result.detailed_results:
        # Check criteria scores list
        c_score = item.criteria_scores[0]
        print(f"Criteria: {c_score.criteria_name}, ID_Match: ?, Score: {c_score.score}, Feedback: {item.feedback[:50]}...")

if __name__ == "__main__":
    try:
        test_grading()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

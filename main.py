import argparse
import sys
import os
from src.ingestion.loader import IngestionEngine
from src.grading.evaluator import GradingEngine

from src.ingestion.rubric_parser import RubricParser

def main():
    parser = argparse.ArgumentParser(description="Grader Agent - AI Teaching Assistant")
    parser.add_argument("--mode", choices=["essay", "qa", "mc", "coding"], required=True, help="Type of assignment to grade")
    parser.add_argument("--submission", required=True, help="Path to student submission file/dir")
    parser.add_argument("--rubric", required=True, help="Path to rubric/key file")
    
    args = parser.parse_args()
    
    print(f"Starting Grader Agent in {args.mode} mode...")
    
    # 1. Ingestion
    print("Loading submission...")
    ingestion = IngestionEngine()
    try:
        content = ingestion.load_submission(args.submission)
        print("Submission loaded successfully.")
    except Exception as e:
        print(f"Error loading submission: {e}")
        sys.exit(1)

    print("Loading rubric...")
    try:
        rubric_obj = RubricParser.parse(args.rubric)
    except Exception as e:
        print(f"Error parsing rubric: {e}")
        sys.exit(1)

    # 2. Grading
    print("Grading submission...")
    grader = GradingEngine()
    try:
        result = grader.evaluate(content, rubric_obj, args.mode)
    except Exception as e:
        print(f"Error during grading: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # 3. Report
    print("\n--- Grading Report ---")
    print(f"Student: {result.student_id}")
    print(f"Score: {result.total_score} / {result.max_score}")
    print(f"Feedback: {result.feedback}")
    if result.detailed_results:
        print("\nDetails:")
        for res in result.detailed_results:
             print(f"- {list(res.criteria_scores.keys())[0]}: {res.score} (Feedback: {res.feedback})")

if __name__ == "__main__":
    main()

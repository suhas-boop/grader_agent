
import os
import sys
sys.path.append(os.getcwd())

from src.ingestion.rubric_parser import RubricParser

def test_parser():
    rubric_path = "test_rubric.txt"
    rubric = RubricParser.parse(rubric_path)
    
    print(f"Total Criteria: {len(rubric.criteria)}")
    print(f"Total Points: {rubric.total_points}")
    print("-" * 20)
    for c in rubric.criteria:
        print(f"Name: {c.name}")
        print(f"Max Points: {c.max_points}")
        print(f"Description Length: {len(c.description)}")
        print(f"Description Start: {c.description[:50]}...")
        print("-" * 20)

if __name__ == "__main__":
    try:
        test_parser()
    except Exception as e:
        print(f"Error: {e}")

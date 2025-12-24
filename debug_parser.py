from src.ingestion.rubric_parser import RubricParser
import os

# Create a temporary test file matching the user's issue
with open("temp_debug_rubric.txt", "w") as f:
    f.write("Q1. Internship overview: role + hours + what you did (10 pts)\n")
    f.write("9–10: Clear org/team/context...\n")

rubric = RubricParser.parse("temp_debug_rubric.txt")
print(f"Total Points: {rubric.total_points}")
print(f"Criteria Count: {len(rubric.criteria)}") 
for c in rubric.criteria:
    print(f"- {c.name}: {c.max_points}")

os.remove("temp_debug_rubric.txt")

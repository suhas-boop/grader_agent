from src.models import Rubric, RubricCriteria
import json

class RubricParser:
    @staticmethod
    def parse(file_path: str) -> Rubric:
        # Simple parser for prototype: expects JSON or assumes a default simple format
        # For now, let's strictly require JSON for the Strategy implementation to work smoothly
        # Or parse the simple text format we made earlier (Criteria: \n 1. Name (points))
        
        with open(file_path, 'r') as f:
            content = f.read()
            
        if file_path.endswith('.json'):
            return Rubric.model_validate_json(content)
        else:
            # Fallback simple text parser
            criteria = []
            total = 0
            lines = content.split('\n')
            import re
            # Regex to match: "1. Name (5 points) Description" or "Q1. Name (5 pts): Description"
            # Captures: Name, Points, Description (optional)
            # Updated to handle Q prefix and pts/points
            pattern = re.compile(r"^(?:Q)?\d+\.\s+(.+?)\s+\((\d+(?:\.\d+)?)\s+(?:points|pts)\)(.*)$", re.IGNORECASE)
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                # Relaxed check: Allow digit start or 'Q' start
                if not (line[0].isdigit() or line.upper().startswith('Q')):
                    continue
                    
                match = pattern.match(line)
                if match:
                    name = match.group(1).strip()
                    points = float(match.group(2))
                    description = match.group(3).strip().lstrip(':').strip()
                    if not description: description = name # Fallback
                    
                    criteria.append(RubricCriteria(name=name, description=description, max_points=points))
                    total += points
            
            return Rubric(criteria=criteria, total_points=total)

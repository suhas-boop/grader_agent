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
            
            current_criteria = None
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Check if line is a new criterion header
                match = pattern.match(line)
                if match:
                    # Save previous if exists
                    if current_criteria:
                        criteria.append(current_criteria)
                    
                    name = match.group(1).strip()
                    points = float(match.group(2))
                    # Group 3 might capture inline description if any, but usually it's empty in this format
                    inline_desc = match.group(3).strip().lstrip(':').strip()
                    
                    current_criteria = RubricCriteria(name=name, description=inline_desc, max_points=points)
                else:
                    # Append strictly to description if we have an active criterion
                    if current_criteria:
                         # Append line to description
                         if current_criteria.description:
                             current_criteria.description += " " + line
                         else:
                             current_criteria.description = line
            
            # Append last one
            if current_criteria:
                criteria.append(current_criteria)
            
            # Recalculate total
            total = sum(c.max_points for c in criteria)
            
            return Rubric(criteria=criteria, total_points=total)

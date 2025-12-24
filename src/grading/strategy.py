from abc import ABC, abstractmethod
from typing import Any
from src.models import GradingResult, Rubric

class GradingStrategy(ABC):
    @abstractmethod
    def grade(self, content: Any, rubric: Rubric, student_id: str) -> GradingResult:
        pass

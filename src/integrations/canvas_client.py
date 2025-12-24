from canvasapi import Canvas
from typing import List, Dict, Any
import os

class CanvasClient:
    """Wrapper for Canvas LMS API interactions."""
    
    def __init__(self, api_url: str, api_key: str):
        self.canvas = Canvas(api_url, api_key)
        self.user = self.canvas.get_current_user()

    def get_courses(self) -> List[Dict[str, Any]]:
        """Returns a list of active courses for the current user."""
        courses = self.user.get_courses(enrollment_state='active')
        return [{"id": c.id, "name": c.name} for c in courses if hasattr(c, 'name')]

    def get_assignments(self, course_id: int) -> List[Dict[str, Any]]:
        """Returns a list of assignments for a course."""
        course = self.canvas.get_course(course_id)
        assignments = course.get_assignments()
        return [{"id": a.id, "name": a.name} for a in assignments]

    def get_submissions(self, course_id: int, assignment_id: int) -> List[Any]:
        """Fetches submissions for a specific assignment."""
        course = self.canvas.get_course(course_id)
        assignment = course.get_assignment(assignment_id)
        # Fetching submissions with 'user' include to get student names (if allowed)
        return list(assignment.get_submissions(include=['user']))
        
    def post_grade(self, course_id: int, assignment_id: int, student_id: int, grade: float, comment: str):
        """Posts a grade and comment to Canvas."""
        course = self.canvas.get_course(course_id)
        assignment = course.get_assignment(assignment_id)
    def get_submission_content(self, course_id: int, assignment_id: int, student_id: int) -> str:
        """Fetches the content of a submission (body or file text)."""
        course = self.canvas.get_course(course_id)
        assignment = course.get_assignment(assignment_id)
        sub = assignment.get_submission(student_id)
        
        if hasattr(sub, 'body') and sub.body:
             return sub.body
        
        # TODO: Handle file downloads (attachments)
        # For now, return empty or placeholder
        if hasattr(sub, 'attachments') and sub.attachments:
            # In a real app, we'd download sub.attachments[0]['url']
            return "FILE_CONTENT_PLACEHOLDER"
            
        return ""

    def post_grade(self, course_id: int, assignment_id: int, student_id: int, grade: float, comment: str):
        """Posts a grade and comment to Canvas."""
        course = self.canvas.get_course(course_id)
        assignment = course.get_assignment(assignment_id)
        # student_id must be the Canvas User ID (int)
        submission = assignment.get_submission(student_id)
        submission.edit(submission={'posted_grade': grade}, comment={'text_comment': comment})

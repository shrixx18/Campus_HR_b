from enum import Enum


class UserRole(str, Enum):
    STUDENT = "student"
    COORDINATOR = "coordinator"


class ApplicationStatus(str, Enum):
    APPLIED = "Applied"
    SHORTLISTED = "Shortlisted"
    ASSESSMENT = "Assessment"
    TECHNICAL_INTERVIEW = "Technical Interview"
    HR_INTERVIEW = "HR Interview"
    SELECTED = "Selected"
    REJECTED = "Rejected"


class QueryStatus(str, Enum):
    OPEN = "Open"
    IN_PROGRESS = "In Progress"
    RESOLVED = "Resolved"
    CLOSED = "Closed"


class FormFieldType(str, Enum):
    TEXT = "text"
    NUMBER = "number"
    EMAIL = "email"
    DROPDOWN = "dropdown"
    CHECKBOX = "checkbox"
    FILE = "file"
    DEADLINE = "deadline"

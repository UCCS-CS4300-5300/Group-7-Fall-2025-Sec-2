from django.db import models
from datetime import datetime
from typing import List, Optional
from dataclasses import dataclass
from enum import Enum


class SubmissionStatus(Enum):
    """Enum for tracking submission status"""
    SUBMITTED = "submitted"
    NOT_SUBMITTED = "not_submitted"


@dataclass
class User:
    """User model representing a group member"""
    id: int
    name: str
    email: str
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class Trip:
    """Trip model representing a group trip"""
    id: int
    name: str
    description: str
    group_members: List[User]
    created_at: datetime = None
    deadline: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class PreferenceSubmission:
    """Model for tracking user preference submissions"""
    id: int
    user_id: int
    trip_id: int
    preferences: dict  # JSON-like structure for preferences
    submitted_at: datetime = None
    status: SubmissionStatus = SubmissionStatus.SUBMITTED
    
    def __post_init__(self):
        if self.submitted_at is None:
            self.submitted_at = datetime.now()


@dataclass
class UserSubmissionStatus:
    """Model for displaying user submission status"""
    user: User
    status: SubmissionStatus
    submitted_at: Optional[datetime] = None
    days_remaining: Optional[int] = None

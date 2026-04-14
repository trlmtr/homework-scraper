"""Data models for Teamie scraper."""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field


class Course(BaseModel):
    """Model for a course."""

    id: str
    name: str
    code: Optional[str] = None
    instructor: Optional[str] = None


class Assignment(BaseModel):
    """Model for an assignment."""

    id: str
    title: str
    course_name: str
    course_id: Optional[str] = None
    description: Optional[str] = None
    deadline: Optional[datetime] = None
    status: str  # submitted, pending, overdue
    total_points: Optional[float] = None
    submission_url: Optional[str] = None
    attachments: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)


class Homework(BaseModel):
    """Model for a homework task."""

    id: str
    title: str
    course_name: str
    course_id: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: Optional[str] = None  # high, medium, low
    status: str  # completed, pending, overdue
    attachments: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)


class CourseMaterial(BaseModel):
    """Model for course material metadata."""

    id: str
    title: str
    course_name: str
    course_id: Optional[str] = None
    material_type: str  # pdf, video, link, document
    url: Optional[str] = None
    size: Optional[str] = None
    uploaded_date: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)


class ScrapedData(BaseModel):
    """Container for all scraped data."""

    scrape_timestamp: datetime = Field(default_factory=datetime.now)
    user: Optional[str] = None
    courses: List[Course] = Field(default_factory=list)
    assignments: List[Assignment] = Field(default_factory=list)
    homework: List[Homework] = Field(default_factory=list)
    materials: List[CourseMaterial] = Field(default_factory=list)

    def to_json_file(self, filepath: Path) -> None:
        """Save scraped data to a JSON file with pretty formatting.

        Args:
            filepath: Path where the JSON file should be saved
        """
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(
                self.model_dump(mode="json"),
                f,
                indent=2,
                ensure_ascii=False,
                default=str,  # Handle datetime serialization
            )

    def summary(self) -> str:
        """Generate a summary string of the scraped data.

        Returns:
            Summary string with counts of each data type
        """
        return (
            f"Scraping Summary:\n"
            f"  Courses: {len(self.courses)}\n"
            f"  Assignments: {len(self.assignments)}\n"
            f"  Homework: {len(self.homework)}\n"
            f"  Materials: {len(self.materials)}"
        )

"""Parsers for extracting data from Teamie HTML."""

from typing import List, Optional
from datetime import datetime

from playwright.async_api import ElementHandle, Page
from loguru import logger

from .models import Assignment, Homework, CourseMaterial, Course
from .utils import parse_date
from .exceptions import ParsingError


class CourseParser:
    """Parser for course information."""

    @staticmethod
    async def parse_course_card(element: ElementHandle) -> Optional[Course]:
        """Parse a single course card element.

        Args:
            element: Playwright element handle for course card

        Returns:
            Course object or None if parsing fails
        """
        try:
            # Extract course name (UPDATED - Real selector)
            name_elem = await element.query_selector(".classroom-name, .course-title, .course-name")
            name = await name_elem.inner_text() if name_elem else "Unknown Course"
            name = name.strip()

            # Extract course ID from href attribute
            href = await element.get_attribute("href")
            course_id = href.split("/")[-1] if href and "/classroom/" in href else name.replace(" ", "_").lower()[:50]

            # Try to extract course code (part of classroom name in Teamie)
            code_elem = await element.query_selector(".classroom-name")
            code = await code_elem.inner_text() if code_elem else None
            if code:
                code = code.strip()

            # Try to extract instructor (not available in sidebar)
            instructor_elem = await element.query_selector(".instructor, .teacher-name, .teacher")
            instructor = await instructor_elem.inner_text() if instructor_elem else None
            if instructor:
                instructor = instructor.strip()

            return Course(
                id=course_id,
                name=name,
                code=code,
                instructor=instructor,
            )

        except Exception as e:
            logger.warning(f"Failed to parse course card: {e}")
            return None


class AssignmentParser:
    """Parser for assignment information."""

    @staticmethod
    async def parse_assignment_card(
        element: ElementHandle, course_name: str, course_id: str
    ) -> Optional[Assignment]:
        """Parse a single assignment card element.

        Args:
            element: Playwright element handle for assignment card
            course_name: Name of the course this assignment belongs to
            course_id: ID of the course

        Returns:
            Assignment object or None if parsing fails
        """
        try:
            # Extract title
            title_elem = await element.query_selector(
                ".assignment-title, .title, h3, h4"
            )
            title = await title_elem.inner_text() if title_elem else "Untitled Assignment"
            title = title.strip()

            # Extract description
            desc_elem = await element.query_selector(".description, .assignment-desc, p")
            description = await desc_elem.inner_text() if desc_elem else None
            if description:
                description = description.strip()

            # Extract deadline
            deadline = None
            deadline_elem = await element.query_selector(
                ".deadline, .due-date, [class*='date']"
            )
            if deadline_elem:
                deadline_text = await deadline_elem.inner_text()
                try:
                    deadline = parse_date(deadline_text.strip())
                except ValueError as e:
                    logger.debug(f"Could not parse deadline '{deadline_text}': {e}")

            # Extract status
            status_elem = await element.query_selector(".status, .submission-status")
            status = "pending"  # default
            if status_elem:
                status_text = (await status_elem.inner_text()).lower()
                if "submit" in status_text:
                    status = "submitted"
                elif "overdue" in status_text or "late" in status_text:
                    status = "overdue"

            # Extract points
            points = None
            points_elem = await element.query_selector(".points, .grade, .score")
            if points_elem:
                points_text = await points_elem.inner_text()
                try:
                    # Extract numeric value
                    import re

                    match = re.search(r"(\d+(?:\.\d+)?)", points_text)
                    if match:
                        points = float(match.group(1))
                except Exception:
                    pass

            # Extract submission URL
            link_elem = await element.query_selector("a[href]")
            submission_url = None
            if link_elem:
                submission_url = await link_elem.get_attribute("href")

            # Generate ID
            assignment_id = f"{course_id}_{title.replace(' ', '_').lower()[:30]}"

            # Extract attachments
            attachment_elems = await element.query_selector_all(
                ".attachment, .file, a[href*='download']"
            )
            attachments = []
            for att_elem in attachment_elems:
                att_text = await att_elem.inner_text()
                attachments.append(att_text.strip())

            return Assignment(
                id=assignment_id,
                title=title,
                course_name=course_name,
                course_id=course_id,
                description=description,
                deadline=deadline,
                status=status,
                total_points=points,
                submission_url=submission_url,
                attachments=attachments,
            )

        except Exception as e:
            logger.warning(f"Failed to parse assignment card: {e}")
            return None


class HomeworkParser:
    """Parser for homework information."""

    @staticmethod
    async def parse_homework_item(
        element: ElementHandle, course_name: str, course_id: str
    ) -> Optional[Homework]:
        """Parse a single homework item element.

        Args:
            element: Playwright element handle for homework item
            course_name: Name of the course this homework belongs to
            course_id: ID of the course

        Returns:
            Homework object or None if parsing fails
        """
        try:
            # Extract title
            title_elem = await element.query_selector(".homework-title, .title, h3, h4")
            title = await title_elem.inner_text() if title_elem else "Untitled Homework"
            title = title.strip()

            # Extract description
            desc_elem = await element.query_selector(".description, .hw-desc, p")
            description = await desc_elem.inner_text() if desc_elem else None
            if description:
                description = description.strip()

            # Extract due date
            due_date = None
            date_elem = await element.query_selector(".due-date, .deadline, [class*='date']")
            if date_elem:
                date_text = await date_elem.inner_text()
                try:
                    due_date = parse_date(date_text.strip())
                except ValueError as e:
                    logger.debug(f"Could not parse due date '{date_text}': {e}")

            # Extract status
            status_elem = await element.query_selector(".status, .completion-status")
            status = "pending"  # default
            if status_elem:
                status_text = (await status_elem.inner_text()).lower()
                if "complete" in status_text:
                    status = "completed"
                elif "overdue" in status_text or "late" in status_text:
                    status = "overdue"

            # Extract priority
            priority = None
            priority_elem = await element.query_selector(".priority, [class*='priority']")
            if priority_elem:
                priority_text = (await priority_elem.inner_text()).lower()
                if "high" in priority_text:
                    priority = "high"
                elif "medium" in priority_text:
                    priority = "medium"
                elif "low" in priority_text:
                    priority = "low"

            # Generate ID
            homework_id = f"{course_id}_hw_{title.replace(' ', '_').lower()[:30]}"

            # Extract attachments
            attachment_elems = await element.query_selector_all(
                ".attachment, .file, a[href*='download']"
            )
            attachments = []
            for att_elem in attachment_elems:
                att_text = await att_elem.inner_text()
                attachments.append(att_text.strip())

            return Homework(
                id=homework_id,
                title=title,
                course_name=course_name,
                course_id=course_id,
                description=description,
                due_date=due_date,
                priority=priority,
                status=status,
                attachments=attachments,
            )

        except Exception as e:
            logger.warning(f"Failed to parse homework item: {e}")
            return None


class MaterialParser:
    """Parser for course material information."""

    @staticmethod
    async def parse_material_item(
        element: ElementHandle, course_name: str, course_id: str
    ) -> Optional[CourseMaterial]:
        """Parse a single material item element.

        Args:
            element: Playwright element handle for material item
            course_name: Name of the course this material belongs to
            course_id: ID of the course

        Returns:
            CourseMaterial object or None if parsing fails
        """
        try:
            # Extract title
            title_elem = await element.query_selector(
                ".material-title, .file-name, .title, a"
            )
            title = await title_elem.inner_text() if title_elem else "Untitled Material"
            title = title.strip()

            # Extract material type from file extension or icon
            material_type = "document"  # default
            type_elem = await element.query_selector(".file-type, .material-type, .icon")
            if type_elem:
                type_text = (await type_elem.inner_text()).lower()
                if "pdf" in type_text or title.lower().endswith(".pdf"):
                    material_type = "pdf"
                elif "video" in type_text or any(
                    ext in title.lower() for ext in [".mp4", ".mov", ".avi"]
                ):
                    material_type = "video"
                elif "link" in type_text or "url" in type_text:
                    material_type = "link"

            # Extract URL
            link_elem = await element.query_selector("a[href]")
            url = None
            if link_elem:
                url = await link_elem.get_attribute("href")

            # Extract file size
            size = None
            size_elem = await element.query_selector(".file-size, .size")
            if size_elem:
                size = (await size_elem.inner_text()).strip()

            # Extract upload date
            uploaded_date = None
            date_elem = await element.query_selector(".upload-date, .date, time")
            if date_elem:
                date_text = await date_elem.inner_text()
                try:
                    uploaded_date = parse_date(date_text.strip())
                except ValueError as e:
                    logger.debug(f"Could not parse upload date '{date_text}': {e}")

            # Generate ID
            material_id = f"{course_id}_mat_{title.replace(' ', '_').lower()[:30]}"

            return CourseMaterial(
                id=material_id,
                title=title,
                course_name=course_name,
                course_id=course_id,
                material_type=material_type,
                url=url,
                size=size,
                uploaded_date=uploaded_date,
            )

        except Exception as e:
            logger.warning(f"Failed to parse material item: {e}")
            return None

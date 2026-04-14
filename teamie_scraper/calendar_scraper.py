"""Calendar-based scraper for Teamie tasks and assignments."""

from typing import List, Optional
from datetime import datetime, timedelta
from loguru import logger

from playwright.async_api import Page
from .models import Assignment
from .exceptions import ParsingError


class CalendarScraper:
    """Scrapes tasks and assignments from Teamie calendar view."""

    def __init__(self, page: Page):
        """Initialize calendar scraper.

        Args:
            page: Playwright page object
        """
        self.page = page

    async def scrape_calendar_tasks(self, user_id: str = "207", course_map: dict = None) -> List[Assignment]:
        """Scrape all tasks from calendar view (shows all future and overdue events).

        Args:
            user_id: User ID for calendar URL (default: 207)
            course_map: Optional dict mapping course IDs to course info (id, name, code)

        Returns:
            List of Assignment objects from calendar

        Raises:
            ParsingError: If calendar parsing fails
        """
        try:
            # Navigate to calendar view
            calendar_url = f"https://lms.asl.org/dash/#/user/{user_id}/calendar/default"
            logger.info(f"Navigating to calendar: {calendar_url}")

            await self.page.goto(calendar_url, wait_until="load")

            # Wait longer for Vue.js to fully render calendar events
            # The page loads in stages: spinner -> calendar container -> events
            await self.page.wait_for_timeout(8000)  # Increased from 3s to 8s
            logger.info("Waited for Vue.js calendar to render")

            # Click "All events" tab to expand view (if available)
            try:
                all_events_btn = await self.page.query_selector("button:has-text('All events')")
                if all_events_btn:
                    await all_events_btn.click()
                    await self.page.wait_for_timeout(1000)
                    logger.info("Clicked 'All events' to show all todos")
            except:
                pass  # If button not found, continue with default view

            # Try to expand all event categories (Overdue, This Week, etc.)
            try:
                category_headers = await self.page.query_selector_all(".event-category-heading")
                for header in category_headers:
                    # Check if category is collapsed
                    parent = await header.evaluate_handle("el => el.parentElement")
                    is_collapsed = await parent.query_selector(".collapse:not(.in)")
                    if is_collapsed:
                        await header.click()
                        await self.page.wait_for_timeout(200)
                logger.info(f"Expanded {len(category_headers)} event categories")
            except Exception as e:
                logger.debug(f"Could not expand categories: {e}")

            # Scroll down multiple times to load all events (infinite scroll)
            try:
                for i in range(5):  # Scroll 5 times to load more events
                    await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await self.page.wait_for_timeout(500)
                logger.info("Scrolled to load all future events")
            except Exception as e:
                logger.debug(f"Scroll failed: {e}")

            # Find all event wrappers (should now include all events)
            event_wrappers = await self.page.query_selector_all(".event-wrapper")

            if not event_wrappers:
                logger.warning("No calendar events found")
                return []

            logger.info(f"Found {len(event_wrappers)} calendar events (all future & overdue)")

            assignments = []
            for idx, event in enumerate(event_wrappers):
                try:
                    assignment = await self._parse_calendar_event(event, idx, course_map)
                    if assignment:
                        assignments.append(assignment)
                except Exception as e:
                    logger.warning(f"Failed to parse calendar event {idx}: {e}")
                    continue

            logger.success(f"Parsed {len(assignments)} assignments from calendar")
            return assignments

        except Exception as e:
            logger.error(f"Calendar scraping failed: {e}")
            raise ParsingError(f"Failed to scrape calendar: {e}")

    async def _parse_calendar_event(
        self, event_element, index: int, course_map: dict = None
    ) -> Optional[Assignment]:
        """Parse a single calendar event into Assignment.

        Args:
            event_element: Playwright element handle for .event-wrapper
            index: Event index for generating ID
            course_map: Optional dict mapping course IDs to course info

        Returns:
            Assignment object or None if parsing fails
        """
        try:
            # Extract title
            title_element = await event_element.query_selector(".event-tile .title span")
            title = (
                await title_element.text_content() if title_element else f"Unknown Task {index}"
            )
            title = title.strip()

            # Extract date
            date_element = await event_element.query_selector(".date-block .date")
            day_element = await event_element.query_selector(".date-block .day")

            date_text = await date_element.text_content() if date_element else None
            day_text = await day_element.text_content() if day_element else None

            # Parse deadline from date
            deadline = self._parse_date(date_text, day_text)

            # Extract status from todo indicator
            indicator = await event_element.query_selector(".todo-indicator")
            status = "pending"
            if indicator:
                indicator_classes = await indicator.get_attribute("class")
                if "mdi-checkbox-marked-circle" in indicator_classes:
                    status = "completed"
                elif "mdi-circle" in indicator_classes:
                    if "text-danger" in indicator_classes:
                        status = "overdue"
                    else:
                        status = "pending"

            # Extract course ID from event icon image and match with course list
            course_name = "Unknown Course"
            course_id = "unknown"
            course_img = await event_element.query_selector(".event-icons img")

            if course_img:
                img_src = await course_img.get_attribute("src")
                # Extract classroom ID from image URL (e.g., classroom-picture-1138863.png)
                if img_src and "classroom-picture-" in img_src:
                    try:
                        # Extract ID from URL like "classroom-picture-1138863.png"
                        import re
                        match = re.search(r'classroom-picture-(\d+)', img_src)
                        if match:
                            classroom_id = match.group(1)
                            # Look up course name from course_map
                            if course_map and classroom_id in course_map:
                                course_info = course_map[classroom_id]
                                course_name = course_info.get("name", "Unknown Course")
                                course_id = classroom_id
                            else:
                                course_id = classroom_id
                                course_name = f"Classroom {classroom_id}"
                    except Exception as e:
                        logger.debug(f"Failed to extract classroom ID from {img_src}: {e}")

            # Fallback: try to extract course from meta section if not found
            if course_name == "Unknown Course":
                meta_element = await event_element.query_selector(".meta")
                if meta_element:
                    meta_text = await meta_element.text_content()
                    if meta_text:
                        # Meta might contain course name or other details
                        course_name = meta_text.strip()

            # Generate ID from title
            assignment_id = f"calendar_{index}_{title[:30].replace(' ', '_')}"

            return Assignment(
                id=assignment_id,
                title=title,
                course_name=course_name,
                course_id=course_id,
                description="",  # Not available in calendar view
                deadline=deadline,
                status=status,
                total_points=None,  # Not shown in calendar
                submission_url="",
                attachments=[],
                created_at=datetime.now(),
            )

        except Exception as e:
            logger.debug(f"Error parsing calendar event {index}: {e}")
            return None

    def _parse_date(self, date_text: Optional[str], day_text: Optional[str]) -> Optional[datetime]:
        """Parse date from calendar event.

        Args:
            date_text: Date number (e.g., "05")
            day_text: Day name (e.g., "Thu")

        Returns:
            datetime object or None if parsing fails
        """
        if not date_text:
            return None

        try:
            # Get current date
            now = datetime.now()
            day_num = int(date_text)

            # Assume date is in current month or next month
            # If date is less than current day, assume next month
            if day_num < now.day:
                # Next month
                if now.month == 12:
                    year = now.year + 1
                    month = 1
                else:
                    year = now.year
                    month = now.month + 1
            else:
                # Current month
                year = now.year
                month = now.month

            # Create deadline at end of day
            deadline = datetime(year, month, day_num, 23, 59, 0)
            return deadline

        except Exception as e:
            logger.debug(f"Failed to parse date '{date_text}' '{day_text}': {e}")
            return None

    async def scrape_course_todos(self, course_name: str, course_id: str) -> List[Assignment]:
        """Scrape ToDos widget from a course page (already navigated to).

        Args:
            course_name: Name of the course
            course_id: ID of the course

        Returns:
            List of Assignment objects from the course ToDos widget
        """
        try:
            # Click "All events" link if available to show all todos
            try:
                all_events_link = await self.page.query_selector("a:has-text('All events')")
                if all_events_link:
                    await all_events_link.click()
                    await self.page.wait_for_timeout(2000)
            except Exception:
                pass

            # Find event wrappers in the ToDos panel
            event_wrappers = await self.page.query_selector_all(".event-wrapper")

            if not event_wrappers:
                return []

            assignments = []
            for idx, event in enumerate(event_wrappers):
                try:
                    # Extract title
                    title_element = await event.query_selector(".event-tile .title span")
                    if not title_element:
                        title_element = await event.query_selector(".title span")
                    title = await title_element.text_content() if title_element else None
                    if not title:
                        continue
                    title = title.strip()

                    # Extract date
                    date_element = await event.query_selector(".date-block .date")
                    day_element = await event.query_selector(".date-block .day")
                    date_text = await date_element.text_content() if date_element else None
                    day_text = await day_element.text_content() if day_element else None
                    deadline = self._parse_date(date_text, day_text)

                    # Extract status
                    indicator = await event.query_selector(".todo-indicator")
                    status = "pending"
                    if indicator:
                        indicator_classes = await indicator.get_attribute("class") or ""
                        if "mdi-checkbox-marked-circle" in indicator_classes:
                            status = "completed"
                        elif "text-danger" in indicator_classes:
                            status = "overdue"

                    assignment_id = f"course_{course_id}_{idx}_{title[:30].replace(' ', '_')}"

                    assignments.append(Assignment(
                        id=assignment_id,
                        title=title,
                        course_name=course_name,
                        course_id=course_id,
                        description="",
                        deadline=deadline,
                        status=status,
                        total_points=None,
                        submission_url="",
                        attachments=[],
                        created_at=datetime.now(),
                    ))
                except Exception as e:
                    logger.debug(f"Failed to parse course todo {idx}: {e}")
                    continue

            logger.info(f"Found {len(assignments)} todos for {course_name}")
            return assignments

        except Exception as e:
            logger.debug(f"Failed to scrape course todos for {course_name}: {e}")
            return []

    async def get_todo_count(self) -> int:
        """Get count of pending todos from navbar.

        Returns:
            Number of pending todos
        """
        try:
            todo_badge = await self.page.query_selector(".user-todo-count.navbar-badge")
            if todo_badge:
                count_text = await todo_badge.text_content()
                return int(count_text.strip())
            return 0
        except Exception:
            return 0

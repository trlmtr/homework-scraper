"""Main scraper orchestration for Teamie platform."""

from typing import List, Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from config.settings import Settings
from .models import ScrapedData, Course, Assignment, Homework, CourseMaterial
from .authenticator import TeamieAuthenticator
from .parsers import CourseParser, AssignmentParser, HomeworkParser, MaterialParser
from .selectors import TeamieSelectors, FALLBACK_SELECTORS
from .exceptions import NavigationError, ParsingError


class TeamieScraper:
    """Main scraper class for Teamie platform.

    Uses Playwright with persistent browser context for Google OAuth authentication.
    """

    def __init__(self, config: Settings):
        """Initialize scraper.

        Args:
            config: Application settings
        """
        self.config = config
        self.playwright = None
        self.context = None
        self.page = None
        self.authenticator = None
        self.selectors = TeamieSelectors()

    async def __aenter__(self):
        """Context manager entry - setup browser with persistent context."""
        logger.info("Initializing Playwright browser...")

        self.playwright = await async_playwright().start()

        # Use persistent context to save/load browser session (for Google OAuth)
        logger.info(f"Using persistent session directory: {self.config.SESSION_DIR}")

        self.context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=str(self.config.SESSION_DIR),
            headless=self.config.HEADLESS,
            viewport={"width": 1920, "height": 1080},
            slow_mo=self.config.SLOW_MO,
        )

        # Get or create page
        if self.context.pages:
            self.page = self.context.pages[0]
        else:
            self.page = await self.context.new_page()

        # Initialize authenticator
        self.authenticator = TeamieAuthenticator(self.page, self.config)

        logger.success("Browser initialized")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup browser."""
        logger.info("Closing browser...")
        if self.context:
            await self.context.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("Browser closed")

    async def scrape_all(self) -> ScrapedData:
        """Main orchestration method to scrape all data from Teamie.

        Returns:
            ScrapedData object containing all scraped information

        Raises:
            AuthenticationError: If authentication fails
            NavigationError: If page navigation fails
        """
        logger.info("Starting Teamie scrape...")

        # 1. Authenticate
        logger.info("Authenticating...")
        auth_success = await self.authenticator.login()
        if not auth_success:
            raise NavigationError("Authentication failed")

        # 2. Get list of courses
        logger.info("Fetching course list...")
        courses = await self.get_courses()
        logger.info(f"Found {len(courses)} courses")

        # 3. Initialize data container
        scraped_data = ScrapedData(courses=courses)

        # 4. For each course, scrape assignments, homework, and materials
        for course in courses:
            logger.info(f"Scraping course: {course.name}")

            try:
                # Scrape assignments
                assignments = await self.scrape_assignments(course)
                scraped_data.assignments.extend(assignments)
                logger.info(f"  - Found {len(assignments)} assignments")

                # Scrape homework
                homework = await self.scrape_homework(course)
                scraped_data.homework.extend(homework)
                logger.info(f"  - Found {len(homework)} homework tasks")

                # Scrape materials
                materials = await self.scrape_materials(course)
                scraped_data.materials.extend(materials)
                logger.info(f"  - Found {len(materials)} materials")

            except Exception as e:
                logger.error(f"Error scraping course {course.name}: {e}")
                # Continue with other courses
                continue

        logger.success(f"Scraping complete! Total items collected:")
        logger.success(f"  - Courses: {len(scraped_data.courses)}")
        logger.success(f"  - Assignments: {len(scraped_data.assignments)}")
        logger.success(f"  - Homework: {len(scraped_data.homework)}")
        logger.success(f"  - Materials: {len(scraped_data.materials)}")

        return scraped_data

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    async def get_courses(self) -> List[Course]:
        """Get list of all courses from dashboard.

        Returns:
            List of Course objects

        Raises:
            NavigationError: If navigation fails
            ParsingError: If course parsing fails
        """
        try:
            # Ensure we're on the dashboard
            await self.authenticator.ensure_authenticated()

            # Wait for course list to load
            await self.page.wait_for_load_state("load")
            await self.page.wait_for_timeout(3000)  # Additional wait for SPA content to render

            # Try to find course cards with multiple selectors
            course_elements = None
            for selector in FALLBACK_SELECTORS["course_card"]:
                course_elements = await self.page.query_selector_all(selector)
                if course_elements:
                    logger.debug(f"Found {len(course_elements)} courses with selector: {selector}")
                    break

            if not course_elements:
                logger.warning("No course elements found. Taking screenshot for debugging...")
                await self.page.screenshot(
                    path=str(self.config.LOG_DIR / "no_courses_found.png")
                )
                return []

            # Parse each course card
            courses = []
            for element in course_elements:
                course = await CourseParser.parse_course_card(element)
                if course:
                    courses.append(course)

            return courses

        except Exception as e:
            logger.error(f"Failed to get courses: {e}")
            await self.page.screenshot(
                path=str(self.config.LOG_DIR / "get_courses_error.png")
            )
            raise NavigationError(f"Failed to get courses: {e}")

    async def scrape_assignments(self, course: Course) -> List[Assignment]:
        """Scrape assignments for a specific course.

        Args:
            course: Course object to scrape assignments for

        Returns:
            List of Assignment objects
        """
        try:
            logger.debug(f"Navigating to assignments for {course.name}...")

            # Try to find and click assignments tab/link
            # This will need to be adjusted based on actual Teamie UI structure
            assignment_tab = await self.page.query_selector(self.selectors.ASSIGNMENTS_TAB)
            if assignment_tab:
                await assignment_tab.click()
                await self.page.wait_for_load_state("load")
                await self.page.wait_for_timeout(2000)  # Wait for SPA content

            # Find assignment elements
            assignment_elements = None
            for selector in FALLBACK_SELECTORS["assignment_card"]:
                assignment_elements = await self.page.query_selector_all(selector)
                if assignment_elements:
                    break

            if not assignment_elements:
                logger.debug(f"No assignments found for {course.name}")
                return []

            # Parse assignments
            assignments = []
            for element in assignment_elements:
                assignment = await AssignmentParser.parse_assignment_card(
                    element, course.name, course.id
                )
                if assignment:
                    assignments.append(assignment)

            return assignments

        except Exception as e:
            logger.warning(f"Failed to scrape assignments for {course.name}: {e}")
            return []

    async def scrape_homework(self, course: Course) -> List[Homework]:
        """Scrape homework for a specific course.

        Args:
            course: Course object to scrape homework for

        Returns:
            List of Homework objects
        """
        try:
            logger.debug(f"Navigating to homework for {course.name}...")

            # Try to find and click homework tab/link
            homework_tab = await self.page.query_selector(self.selectors.HOMEWORK_TAB)
            if homework_tab:
                await homework_tab.click()
                await self.page.wait_for_load_state("load")
                await self.page.wait_for_timeout(2000)  # Wait for SPA content

            # Find homework elements
            homework_elements = None
            for selector in FALLBACK_SELECTORS["homework_item"]:
                homework_elements = await self.page.query_selector_all(selector)
                if homework_elements:
                    break

            if not homework_elements:
                logger.debug(f"No homework found for {course.name}")
                return []

            # Parse homework
            homework_list = []
            for element in homework_elements:
                homework = await HomeworkParser.parse_homework_item(
                    element, course.name, course.id
                )
                if homework:
                    homework_list.append(homework)

            return homework_list

        except Exception as e:
            logger.warning(f"Failed to scrape homework for {course.name}: {e}")
            return []

    async def scrape_materials(self, course: Course) -> List[CourseMaterial]:
        """Scrape course materials for a specific course.

        Args:
            course: Course object to scrape materials for

        Returns:
            List of CourseMaterial objects
        """
        try:
            logger.debug(f"Navigating to materials for {course.name}...")

            # Try to find and click materials tab/link
            materials_tab = await self.page.query_selector(self.selectors.MATERIALS_TAB)
            if materials_tab:
                await materials_tab.click()
                await self.page.wait_for_load_state("load")
                await self.page.wait_for_timeout(2000)  # Wait for SPA content

            # Find material elements
            material_elements = None
            for selector in FALLBACK_SELECTORS["material_item"]:
                material_elements = await self.page.query_selector_all(selector)
                if material_elements:
                    break

            if not material_elements:
                logger.debug(f"No materials found for {course.name}")
                return []

            # Parse materials
            materials = []
            for element in material_elements:
                material = await MaterialParser.parse_material_item(
                    element, course.name, course.id
                )
                if material:
                    materials.append(material)

            return materials

        except Exception as e:
            logger.warning(f"Failed to scrape materials for {course.name}: {e}")
            return []

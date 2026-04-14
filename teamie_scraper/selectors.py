"""CSS/XPath selectors for Teamie platform.

UPDATED with real selectors discovered from https://lms.asl.org/dash/#/
Last updated: 2026-03-04
"""


class TeamieSelectors:
    """Centralized selectors for Teamie web scraping.

    All selectors should be updated based on actual HTML inspection
    of https://lms.asl.org/dash/#/
    """

    # ==================== Authentication ====================
    # Google OAuth selectors (may not be needed if using persistent context)
    GOOGLE_SIGNIN_BUTTON = "button:has-text('Sign in with Google')"  # Placeholder
    LOGIN_INDICATOR = "[data-testid='user-profile'], .user-menu, .profile-icon"  # Placeholder

    # ==================== Dashboard ====================
    DASHBOARD_CONTAINER = ".user-sidebar-classrooms"  # REAL - Sidebar with all classrooms
    COURSE_LIST_CONTAINER = ".user-sidebar-classrooms"  # REAL - Same as dashboard container
    COURSE_CARD = "a.classroom.list-group-item"  # REAL - Individual classroom link
    COURSE_NAME = ".classroom-name"  # REAL - Classroom name span
    COURSE_IMAGE = ".classroom-image"  # REAL - Classroom thumbnail image
    COURSE_CODE = ".classroom-name"  # REAL - Code is part of name (e.g., "English 9 P1 HN [25-26]")
    COURSE_INSTRUCTOR = ""  # Not visible in sidebar - need to visit course page

    # ==================== Assignments ====================
    ASSIGNMENTS_TAB = "a:has-text('Assignments'), [href*='assignments']"  # Placeholder
    ASSIGNMENTS_CONTAINER = ".assignments-list, .assignments-container"  # Placeholder
    ASSIGNMENT_CARD = ".assignment-item, .assignment-card"  # Placeholder
    ASSIGNMENT_TITLE = ".assignment-title, .title, h3"  # Placeholder
    ASSIGNMENT_DESCRIPTION = ".description, .assignment-desc"  # Placeholder
    ASSIGNMENT_DEADLINE = ".deadline, .due-date, [class*='date']"  # Placeholder
    ASSIGNMENT_STATUS = ".status, .submission-status"  # Placeholder
    ASSIGNMENT_POINTS = ".points, .grade"  # Placeholder
    ASSIGNMENT_LINK = "a[href*='assignment']"  # Placeholder

    # ==================== Homework ====================
    HOMEWORK_TAB = "a:has-text('Homework'), [href*='homework']"  # Placeholder
    HOMEWORK_CONTAINER = ".homework-list, .homework-container"  # Placeholder
    HOMEWORK_ITEM = ".homework-item, .hw-card"  # Placeholder
    HOMEWORK_TITLE = ".homework-title, .title, h3"  # Placeholder
    HOMEWORK_DESCRIPTION = ".description, .hw-desc"  # Placeholder
    HOMEWORK_DUE_DATE = ".due-date, .deadline"  # Placeholder
    HOMEWORK_STATUS = ".status, .completion-status"  # Placeholder
    HOMEWORK_PRIORITY = ".priority"  # Placeholder

    # ==================== Course Materials ====================
    MATERIALS_TAB = "a:has-text('Materials'), a:has-text('Resources'), [href*='materials']"  # Placeholder
    MATERIALS_CONTAINER = ".materials-list, .resources-container"  # Placeholder
    MATERIAL_ITEM = ".material-item, .resource-card"  # Placeholder
    MATERIAL_TITLE = ".material-title, .file-name, .title"  # Placeholder
    MATERIAL_TYPE = ".file-type, .material-type"  # Placeholder
    MATERIAL_LINK = "a[href*='download'], a[href*='file']"  # Placeholder
    MATERIAL_SIZE = ".file-size, .size"  # Placeholder
    MATERIAL_DATE = ".upload-date, .date"  # Placeholder

    # ==================== Navigation ====================
    NEXT_PAGE_BUTTON = ".next-page, button:has-text('Next'), [aria-label='Next']"  # Placeholder
    PAGINATION_CONTAINER = ".pagination"  # Placeholder

    # ==================== Common ====================
    LOADING_INDICATOR = ".loading, .spinner, [role='progressbar']"  # Placeholder
    ERROR_MESSAGE = ".error, .alert-danger"  # Placeholder


# Fallback selectors for each primary selector
# These will be tried if the primary selector doesn't work
FALLBACK_SELECTORS = {
    "course_card": [
        "a.classroom.list-group-item",  # REAL - Primary selector
        ".classroom.list-group-item",
        "[class*='classroom']",
        ".course-card",
        ".course-item",
    ],
    "assignment_card": [
        ".assignment-item",
        ".assignment-card",
        "[class*='assignment']",
        "div[role='listitem']",
    ],
    "homework_item": [
        ".homework-item",
        ".hw-card",
        "[class*='homework']",
        "[class*='hw']",
    ],
    "material_item": [
        ".material-item",
        ".resource-card",
        "[class*='material']",
        "[class*='resource']",
    ],
}

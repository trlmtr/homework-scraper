"""Authentication handler for Teamie with Google OAuth support."""

from playwright.async_api import Page
from loguru import logger

from config.settings import Settings
from .selectors import TeamieSelectors


class TeamieAuthenticator:
    """Handles Google OAuth authentication for Teamie platform.

    Uses Playwright persistent context to save browser session,
    allowing for one-time manual Google login followed by automatic
    session reuse in subsequent runs.
    """

    def __init__(self, page: Page, config: Settings):
        """Initialize authenticator.

        Args:
            page: Playwright page object
            config: Application settings
        """
        self.page = page
        self.config = config
        self.selectors = TeamieSelectors()

    async def login(self) -> bool:
        """Authenticate with Teamie using Google OAuth.

        For first run, user must manually complete Google login in browser.
        For subsequent runs, session is loaded from persistent context.

        Returns:
            True if authentication successful, False otherwise

        Raises:
            AuthenticationError: If authentication fails
        """
        logger.info(f"Navigating to Teamie: {self.config.TEAMIE_URL}")

        try:
            # Navigate to Teamie
            await self.page.goto(
                self.config.TEAMIE_URL,
                wait_until="load",  # Changed from networkidle for better reliability
                timeout=self.config.TIMEOUT,
            )

            # Wait a moment for page to load
            await self.page.wait_for_timeout(2000)

            # Check if already authenticated
            if await self.is_authenticated():
                logger.success("Already authenticated (session loaded)")
                return True

            # Not authenticated - need manual Google login
            logger.warning(
                "Not authenticated. Please complete Google OAuth login in the browser."
            )

            if self.config.HEADLESS:
                logger.error(
                    "Cannot authenticate in headless mode. "
                    "Please set HEADLESS=false in .env for first run."
                )
                return False

            # Wait for user to complete Google OAuth login
            # We'll wait for authentication indicators to appear
            logger.info(
                "Waiting for manual Google login... "
                "(Please sign in with your Google account)"
            )

            # Wait up to 5 minutes for user to complete login
            try:
                await self.page.wait_for_selector(
                    self.selectors.LOGIN_INDICATOR,
                    timeout=300000,  # 5 minutes
                    state="visible",
                )
            except Exception as e:
                logger.error(f"Login timeout: {e}")
                return False

            # Verify authentication
            if await self.is_authenticated():
                logger.success(
                    "Authentication successful! Session will be saved for future runs."
                )
                # Save a screenshot for reference
                await self.page.screenshot(
                    path=str(self.config.LOG_DIR / "authenticated_dashboard.png")
                )
                return True
            else:
                logger.error("Authentication verification failed")
                return False

        except Exception as e:
            logger.error(f"Login failed: {e}")
            # Save screenshot for debugging
            await self.page.screenshot(
                path=str(self.config.LOG_DIR / "login_error.png")
            )
            raise

    async def is_authenticated(self) -> bool:
        """Check if current session is authenticated.

        Returns:
            True if authenticated, False otherwise
        """
        try:
            # Try multiple indicators of being logged in
            # These selectors should be updated based on actual Teamie UI

            # Check for login indicator
            login_element = await self.page.query_selector(
                self.selectors.LOGIN_INDICATOR
            )
            if login_element:
                logger.debug("Authentication confirmed via login indicator")
                return True

            # Check for dashboard/course content
            dashboard = await self.page.query_selector(
                self.selectors.DASHBOARD_CONTAINER
            )
            if dashboard:
                logger.debug("Authentication confirmed via dashboard presence")
                return True

            # Check if URL contains 'dash' (logged in area)
            current_url = self.page.url
            if "/dash" in current_url or "dashboard" in current_url.lower():
                logger.debug("Authentication confirmed via URL pattern")
                return True

            # Check for presence of Google Sign-in button (not logged in)
            signin_button = await self.page.query_selector(
                self.selectors.GOOGLE_SIGNIN_BUTTON
            )
            if signin_button:
                logger.debug("Not authenticated (sign-in button present)")
                return False

            # If we're unsure, log the current URL and page title for debugging
            title = await self.page.title()
            logger.debug(f"Current page - URL: {current_url}, Title: {title}")

            # Default to false if can't confirm
            return False

        except Exception as e:
            logger.warning(f"Error checking authentication status: {e}")
            return False

    async def ensure_authenticated(self) -> None:
        """Ensure the session is authenticated, login if needed.

        Raises:
            AuthenticationError: If authentication fails
        """
        if not await self.is_authenticated():
            logger.warning("Session appears to be expired, re-authenticating...")
            success = await self.login()
            if not success:
                from .exceptions import AuthenticationError

                raise AuthenticationError("Failed to authenticate with Teamie")

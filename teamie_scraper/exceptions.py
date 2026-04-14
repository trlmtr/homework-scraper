"""Custom exceptions for Teamie scraper."""


class TeamieScraperError(Exception):
    """Base exception for all Teamie scraper errors."""

    pass


class AuthenticationError(TeamieScraperError):
    """Raised when authentication fails."""

    pass


class NavigationError(TeamieScraperError):
    """Raised when page navigation fails."""

    pass


class ParsingError(TeamieScraperError):
    """Raised when data parsing fails."""

    pass


class SessionExpiredError(AuthenticationError):
    """Raised when the session has expired."""

    pass

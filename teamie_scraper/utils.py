"""Utility functions for Teamie scraper."""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from loguru import logger


def setup_logging(log_dir: Path, log_level: str = "INFO") -> None:
    """Configure loguru logger for the application.

    Args:
        log_dir: Directory where log files should be saved
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    # Ensure log directory exists
    log_dir.mkdir(parents=True, exist_ok=True)

    # Remove default logger
    logger.remove()

    # Add console logger with color
    logger.add(
        sink=lambda msg: print(msg, end=""),
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level=log_level,
        colorize=True,
    )

    # Add file logger with rotation
    log_file = log_dir / f"teamie_scraper_{datetime.now().strftime('%Y%m%d')}.log"
    logger.add(
        sink=str(log_file),
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        level="DEBUG",  # Log everything to file
        rotation="10 MB",
        retention="7 days",
        compression="zip",
    )

    logger.info(f"Logging initialized. Log file: {log_file}")


def save_json(data: Dict[str, Any], output_dir: Path, prefix: str = "teamie_data") -> Path:
    """Save data to timestamped JSON file.

    Args:
        data: Dictionary data to save
        output_dir: Directory where JSON should be saved
        prefix: Prefix for the filename

    Returns:
        Path to the saved JSON file
    """
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create timestamped filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{prefix}_{timestamp}.json"
    filepath = output_dir / filename

    # Save with pretty formatting
    import json

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    logger.success(f"Data saved to {filepath}")
    return filepath


def parse_relative_date(date_str: str) -> datetime:
    """Parse relative date strings like 'Due in 2 days' or 'Tomorrow'.

    Args:
        date_str: Date string to parse

    Returns:
        Parsed datetime object

    Raises:
        ValueError: If date string cannot be parsed
    """
    from datetime import timedelta

    date_str = date_str.lower().strip()
    now = datetime.now()

    if "today" in date_str:
        return now.replace(hour=23, minute=59, second=59)
    elif "tomorrow" in date_str:
        return (now + timedelta(days=1)).replace(hour=23, minute=59, second=59)
    elif "in" in date_str and "day" in date_str:
        # Extract number from "in X days"
        import re

        match = re.search(r"in\s+(\d+)\s+day", date_str)
        if match:
            days = int(match.group(1))
            return (now + timedelta(days=days)).replace(hour=23, minute=59, second=59)

    raise ValueError(f"Unable to parse relative date: {date_str}")


def parse_date(date_str: str) -> datetime:
    """Parse date string in various formats.

    Args:
        date_str: Date string to parse

    Returns:
        Parsed datetime object

    Raises:
        ValueError: If date string cannot be parsed
    """
    if not date_str:
        raise ValueError("Empty date string")

    # Try relative dates first
    if any(word in date_str.lower() for word in ["today", "tomorrow", "in", "day"]):
        try:
            return parse_relative_date(date_str)
        except ValueError:
            pass

    # Try common date formats
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%m/%d/%Y %H:%M",
        "%m/%d/%Y",
        "%b %d, %Y %H:%M",
        "%b %d, %Y",
        "%B %d, %Y %H:%M",
        "%B %d, %Y",
        "%d %b %Y",
        "%d %B %Y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue

    raise ValueError(f"Unable to parse date: {date_str}")

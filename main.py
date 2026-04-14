"""Main entry point for Teamie web scraper.

Uses CalendarScraper for assignments and per-course ToDos.
"""

import asyncio
import json
import sys
from datetime import datetime

from loguru import logger
from playwright.async_api import async_playwright

from config.settings import Settings
from teamie_scraper.calendar_scraper import CalendarScraper
from teamie_scraper.authenticator import TeamieAuthenticator
from teamie_scraper.utils import setup_logging
from teamie_scraper.exceptions import AuthenticationError


async def main():
    """Main function to run the Teamie scraper."""
    print("=" * 60)
    print("Teamie Web Scraper (ASL)")
    print("=" * 60)
    print()

    try:
        config = Settings()
        setup_logging(config.LOG_DIR, config.LOG_LEVEL)

        logger.info("Starting Teamie scraper...")
        logger.info(f"Target URL: {config.TEAMIE_URL}")
        logger.info(f"Headless mode: {config.HEADLESS}")

        # Check if first run (no session data)
        session_exists = config.SESSION_DIR.exists() and any(config.SESSION_DIR.iterdir())

        if not session_exists:
            print("\n" + "!" * 60)
            print("FIRST RUN DETECTED")
            print("!" * 60)
            print()
            print("You will need to manually log in with your Google account.")
            print("A browser window will open. Please:")
            print("  1. Click 'Sign in with Google'")
            print("  2. Complete the Google OAuth login")
            print("  3. Wait for redirect back to Teamie dashboard")
            print()
            print("Your session will be saved for future runs.")
            print()

            if config.HEADLESS:
                logger.error(
                    "HEADLESS mode is enabled, but this is the first run. "
                    "Please set HEADLESS=false in your .env file."
                )
                print("\nERROR: Cannot authenticate in headless mode on first run.")
                print("Please set HEADLESS=false in .env")
                return 1

            input("Press Enter to continue...")

        async with async_playwright() as p:
            context = await p.chromium.launch_persistent_context(
                user_data_dir=str(config.SESSION_DIR),
                headless=config.HEADLESS,
                viewport={"width": 1920, "height": 1080},
            )

            page = context.pages[0] if context.pages else await context.new_page()

            try:
                # Authenticate
                authenticator = TeamieAuthenticator(page, config)
                logger.info("Authenticating...")
                success = await authenticator.login()

                if not success:
                    logger.error("Authentication failed!")
                    print("\nAuthentication failed. Check logs for details.")
                    return 1

                # === Get course list ===
                print("\nGetting course list...")
                await page.goto("https://lms.asl.org/dash/#/", wait_until="load")
                await page.wait_for_timeout(3000)

                course_elements = await page.query_selector_all(
                    "a.classroom.list-group-item"
                )
                print(f"  Found {len(course_elements)} total courses")

                # Filter for starred courses (current term)
                starred_courses = []
                for elem in course_elements:
                    star_icon = await elem.query_selector(".star-action")
                    if star_icon:
                        star_classes = await star_icon.get_attribute("class")
                        if (
                            star_classes
                            and "mdi-star" in star_classes
                            and "mdi-star-outline" not in star_classes
                        ):
                            starred_courses.append(elem)

                print(
                    f"  Filtering to {len(starred_courses)} starred courses (current term)"
                )

                # Build course map
                course_map = {}

                for idx, course_elem in enumerate(starred_courses):
                    try:
                        name_elem = await course_elem.query_selector(".classroom-name")
                        name = (
                            await name_elem.inner_text()
                            if name_elem
                            else f"Course {idx}"
                        )
                        name = name.strip()

                        href = await course_elem.get_attribute("href")
                        course_id = (
                            href.split("/")[-1]
                            if href and "/classroom/" in href
                            else str(idx)
                        )

                        course_map[course_id] = {
                            "id": course_id,
                            "name": name,
                        }

                    except Exception as e:
                        logger.warning(f"Failed to parse course {idx}: {e}")

                # === Scrape calendar tasks/assignments ===
                print("\nScraping calendar tasks...")
                calendar_scraper = CalendarScraper(page)

                todo_count = await calendar_scraper.get_todo_count()
                logger.info(f"Pending todos: {todo_count}")

                assignments = await calendar_scraper.scrape_calendar_tasks(
                    user_id=config.TEAMIE_USER_ID, course_map=course_map
                )
                print(f"  Found {len(assignments)} tasks/assignments")

                # === Scrape per-course ToDos ===
                print("\nScraping course todos...")
                existing_keys = {
                    (a.title, a.deadline.date() if a.deadline else None)
                    for a in assignments
                }

                for idx, (course_id, course_info) in enumerate(course_map.items()):
                    try:
                        name = course_info["name"]
                        print(f"  - {name[:50]}...", end=" ")

                        try:
                            classroom_url = (
                                f"https://lms.asl.org/dash/#/classroom/{course_id}"
                            )
                            await page.goto(
                                classroom_url, wait_until="load", timeout=30000
                            )
                            await page.wait_for_timeout(2000)

                            # Scrape ToDos from this course page
                            course_todos = await calendar_scraper.scrape_course_todos(
                                name, course_id
                            )
                            new_todos = [
                                t for t in course_todos
                                if (t.title, t.deadline.date() if t.deadline else None)
                                not in existing_keys
                            ]
                            for t in new_todos:
                                existing_keys.add(
                                    (t.title, t.deadline.date() if t.deadline else None)
                                )
                            assignments.extend(new_todos)
                            print(f"({len(new_todos)} new todos)")

                        except Exception as e:
                            logger.debug(
                                f"Failed to scrape todos for {name}: {e}"
                            )
                            print("(failed)")

                    except Exception as e:
                        logger.warning(f"Failed to parse course {idx}: {e}")

                # === Build output ===
                status_summary = []
                for status in ["pending", "overdue", "completed"]:
                    count = sum(1 for a in assignments if a.status == status)
                    if count > 0:
                        icon = (
                            "done"
                            if status == "completed"
                            else "overdue"
                            if status == "overdue"
                            else "pending"
                        )
                        status_summary.append(f"{icon}: {count}")

                upcoming = sorted(
                    [a for a in assignments if a.deadline],
                    key=lambda x: x.deadline,
                )[:10]

                upcoming_tasks = []
                for a in upcoming:
                    deadline_str = (
                        a.deadline.strftime("%b %d") if a.deadline else "No date"
                    )
                    status_icon = (
                        "done"
                        if a.status == "completed"
                        else "OVERDUE"
                        if a.status == "overdue"
                        else "pending"
                    )

                    class_name = a.course_name
                    if "[" in class_name:
                        class_name = class_name.split("[")[0].strip()

                    upcoming_tasks.append(
                        {
                            "date": deadline_str,
                            "deadline": (
                                a.deadline.isoformat() if a.deadline else None
                            ),
                            "class": class_name,
                            "task": a.title,
                            "status": a.status,
                            "status_icon": status_icon,
                        }
                    )

                output = {
                    "scrape_timestamp": datetime.now().isoformat(),
                    "user": config.GOOGLE_EMAIL,
                    "todo_count": todo_count,
                    "summary": {
                        "assignments": len(assignments),
                        "status_breakdown": status_summary,
                    },
                    "upcoming_tasks": upcoming_tasks,
                    "assignments": [
                        {
                            "id": a.id,
                            "title": a.title,
                            "course_name": a.course_name,
                            "course_id": a.course_id,
                            "deadline": (
                                a.deadline.isoformat() if a.deadline else None
                            ),
                            "status": a.status,
                            "created_at": a.created_at.isoformat(),
                        }
                        for a in assignments
                    ],
                }

                # Save to JSON
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = config.OUTPUT_DIR / f"teamie_data_{timestamp}.json"
                output_file.write_text(json.dumps(output, indent=2))

                # Print summary
                print()
                print("=" * 60)
                print("SCRAPING COMPLETE!")
                print("=" * 60)
                print(f"\nTasks/Assignments: {len(assignments)}")
                print(f"Pending todos: {todo_count}")

                if status_summary:
                    print("\nTasks by status:")
                    for s in status_summary:
                        print(f"  {s}")

                if upcoming_tasks:
                    print("\nUpcoming tasks:")
                    for task in upcoming_tasks:
                        print(
                            f"  {task['status_icon']} {task['date']} | "
                            f"{task['class'][:30]}: {task['task'][:40]}"
                        )

                print(f"\nOutput saved to: {output_file}")

                if not session_exists:
                    print("\nYour Google session has been saved!")
                    print(
                        "  Next time you can run in headless mode by setting"
                    )
                    print("  HEADLESS=true in your .env file.")

                print()
                logger.success("Teamie scraper completed successfully")
                return 0

            finally:
                await context.close()

    except AuthenticationError as e:
        logger.error(f"Authentication failed: {e}")
        print()
        print("=" * 60)
        print("AUTHENTICATION ERROR")
        print("=" * 60)
        print()
        print(str(e))
        print()
        print("Troubleshooting:")
        print("  - Make sure you completed the Google login")
        print("  - Try deleting the session directory and running again")
        print("  - Set HEADLESS=false in .env for first run")
        return 1

    except KeyboardInterrupt:
        logger.warning("Scraper interrupted by user")
        print("\nScraping interrupted. Exiting...")
        return 130

    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        print()
        print("=" * 60)
        print("UNEXPECTED ERROR")
        print("=" * 60)
        print()
        print(str(e))
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

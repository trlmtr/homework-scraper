"""Combined scraper: Calendar tasks + Course materials."""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright
from loguru import logger

from config.settings import Settings
from teamie_scraper.calendar_scraper import CalendarScraper
from teamie_scraper.authenticator import TeamieAuthenticator
from teamie_scraper.parsers import CourseParser, MaterialParser
from teamie_scraper.selectors import FALLBACK_SELECTORS
from teamie_scraper.utils import setup_logging


async def main():
    """Scrape both calendar tasks and course materials."""

    config = Settings()
    setup_logging(config.LOG_DIR, config.LOG_LEVEL)

    print("\n" + "="*60)
    print("TEAMIE COMBINED SCRAPER")
    print("="*60 + "\n")

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(config.SESSION_DIR),
            headless=config.HEADLESS,
            viewport={'width': 1920, 'height': 1080}
        )

        page = context.pages[0] if context.pages else await context.new_page()

        try:
            # Authenticate
            authenticator = TeamieAuthenticator(page, config)
            logger.info("Authenticating...")
            success = await authenticator.login()

            if not success:
                logger.error("Authentication failed!")
                return

            # === PART 1: Get course list first (needed for calendar course matching) ===
            print("\n📚 Getting course list...")

            # Go to dashboard
            await page.goto("https://lms.asl.org/dash/#/", wait_until="load")
            await page.wait_for_timeout(3000)

            # Get courses
            course_elements = await page.query_selector_all("a.classroom.list-group-item")
            print(f"  ✓ Found {len(course_elements)} total courses")

            # Filter for starred courses only
            starred_courses = []
            for elem in course_elements:
                star_icon = await elem.query_selector(".star-action")
                if star_icon:
                    star_classes = await star_icon.get_attribute("class")
                    if star_classes and "mdi-star" in star_classes and "mdi-star-outline" not in star_classes:
                        starred_courses.append(elem)

            print(f"  ✓ Filtering to {len(starred_courses)} starred courses (current term)")

            # Build course map and course list
            courses = []
            course_map = {}  # Maps course ID to course info

            for idx, course_elem in enumerate(starred_courses):
                try:
                    # Parse course info
                    name_elem = await course_elem.query_selector(".classroom-name")
                    name = await name_elem.inner_text() if name_elem else f"Course {idx}"
                    name = name.strip()

                    href = await course_elem.get_attribute("href")
                    course_id = href.split("/")[-1] if href and "/classroom/" in href else str(idx)

                    course_info = {
                        "id": course_id,
                        "name": name,
                        "code": name,  # Code is part of name in Teamie
                        "instructor": None
                    }
                    courses.append(course_info)
                    course_map[course_id] = course_info

                except Exception as e:
                    logger.warning(f"Failed to parse course {idx}: {e}")

            # === PART 2: Scrape calendar tasks/assignments ===
            print("\n📅 Scraping calendar tasks...")
            calendar_scraper = CalendarScraper(page)

            todo_count = await calendar_scraper.get_todo_count()
            logger.info(f"Pending todos: {todo_count}")

            # Pass course_map to calendar scraper for proper course name matching
            assignments = await calendar_scraper.scrape_calendar_tasks(user_id=config.TEAMIE_USER_ID, course_map=course_map)
            print(f"  ✓ Found {len(assignments)} tasks/assignments")

            # === PART 3: Scrape course materials ===
            print("\n📦 Scraping course materials...")

            all_materials = []

            for idx, (course_id, course_info) in enumerate(course_map.items()):
                try:
                    name = course_info["name"]
                    print(f"  - {name[:50]}...", end=" ")

                    # Navigate to course to get materials
                    try:
                        classroom_url = f"https://lms.asl.org/dash/#/classroom/{course_id}"
                        await page.goto(classroom_url, wait_until="load", timeout=30000)
                        await page.wait_for_timeout(2000)

                        # Find material elements
                        material_elements = None
                        for selector in FALLBACK_SELECTORS["material_item"]:
                            material_elements = await page.query_selector_all(selector)
                            if material_elements:
                                break

                        # Parse materials
                        course_materials = []
                        if material_elements:
                            for mat_elem in material_elements:
                                try:
                                    material = await MaterialParser.parse_material_item(
                                        mat_elem, name, course_id
                                    )
                                    if material:
                                        course_materials.append(material)
                                except Exception:
                                    pass

                        all_materials.extend(course_materials)
                        print(f"({len(course_materials)} materials)")

                    except Exception as e:
                        logger.debug(f"Failed to scrape materials for {name}: {e}")
                        print("(materials failed)")

                except Exception as e:
                    logger.warning(f"Failed to parse course {idx}: {e}")

            # Build status summary
            status_summary = []
            for status in ["pending", "overdue", "completed"]:
                count = sum(1 for a in assignments if a.status == status)
                if count > 0:
                    icon = "✅" if status == "completed" else "🔴" if status == "overdue" else "⏳"
                    status_line = f"{icon} {status.capitalize()}: {count}"
                    status_summary.append(status_line)

            # Build upcoming tasks with class names
            upcoming = sorted(
                [a for a in assignments if a.deadline],
                key=lambda x: x.deadline
            )[:10]

            upcoming_tasks = []
            for a in upcoming:
                deadline_str = a.deadline.strftime("%b %d") if a.deadline else "No date"
                status_icon = "✅" if a.status == "completed" else "🔴" if a.status == "overdue" else "⏳"

                # Get short class name (remove year suffix like [25-26])
                class_name = a.course_name
                if "[" in class_name:
                    class_name = class_name.split("[")[0].strip()

                upcoming_tasks.append({
                    "date": deadline_str,
                    "deadline": a.deadline.isoformat() if a.deadline else None,
                    "class": class_name,
                    "task": a.title,
                    "status": a.status,
                    "status_icon": status_icon
                })

            # Prepare combined output
            output = {
                "scrape_timestamp": datetime.now().isoformat(),
                "source": "combined_scraper",
                "user": config.GOOGLE_EMAIL,
                "todo_count": todo_count,
                "summary": {
                    "courses": len(courses),
                    "assignments": len(assignments),
                    "materials": len(all_materials)
                },
                "summary_text": {
                    "courses": len(courses),
                    "assignments": len(assignments),
                    "materials": len(all_materials),
                    "pending_todos": todo_count,
                    "status_breakdown": status_summary,
                    "upcoming_tasks": upcoming_tasks
                },
                "courses": courses,
                "assignments": [
                    {
                        "id": a.id,
                        "title": a.title,
                        "course_name": a.course_name,
                        "course_id": a.course_id,
                        "deadline": a.deadline.isoformat() if a.deadline else None,
                        "status": a.status,
                        "created_at": a.created_at.isoformat(),
                    }
                    for a in assignments
                ],
                "materials": [
                    {
                        "id": m.id,
                        "title": m.title,
                        "course_name": m.course_name,
                        "course_id": m.course_id,
                        "material_type": m.material_type,
                        "url": m.url,
                        "size": m.size,
                        "uploaded_date": m.uploaded_date.isoformat() if m.uploaded_date else None,
                        "created_at": m.created_at.isoformat(),
                    }
                    for m in all_materials
                ],
            }

            # Save to JSON
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = config.OUTPUT_DIR / f"teamie_combined_{timestamp}.json"
            output_file.write_text(json.dumps(output, indent=2))

            # Print summary (using data already built above)
            print("\n" + "="*60)
            print("SCRAPING COMPLETE!")
            print("="*60)
            print(f"\nCourses: {len(courses)}")
            print(f"Tasks/Assignments: {len(assignments)}")
            print(f"Course Materials: {len(all_materials)}")
            print(f"Pending todos: {todo_count}")

            print("\nTasks by status:")
            for status_line in status_summary:
                print(f"  {status_line}")

            print(f"\nOutput saved to: {output_file}")

            print("\nUpcoming tasks:")
            for task in upcoming_tasks:
                task_line = f"{task['status_icon']} {task['date']} | {task['class'][:30]}: {task['task'][:40]}"
                print(f"  {task_line}")

            print("\n" + "="*60 + "\n")

        finally:
            await context.close()


if __name__ == "__main__":
    asyncio.run(main())

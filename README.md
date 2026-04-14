# Teamie Web Scraper (ASL)

Python web scraper for extracting assignments, homework, and course materials from American School of London's Teamie platform (https://lms.asl.org).

## Features

- **Google OAuth Authentication** with persistent sessions
- Scrapes **assignments** with deadlines and submission status
- Scrapes **homework tasks** with due dates
- Scrapes **course materials** metadata (no file downloads)
- Exports to timestamped JSON files
- Comprehensive error handling and logging
- Retry logic for transient failures

## Requirements

- Python 3.9+
- Playwright with Chromium browser
- Google account with ASL Teamie access

## Installation

### 1. Clone or Download This Repository

```bash
cd /Volumes/Shared/VSCode/Kuzey_Time_Management
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Playwright Browsers

```bash
playwright install chromium
```

### 5. Create Configuration File

```bash
cp config/.env.example .env
```

Edit the `.env` file if needed (defaults should work for most users).

## First Run - Google Authentication

**IMPORTANT**: On first run, you must log in manually via Google OAuth.

### Steps:

1. Ensure `HEADLESS=false` in your `.env` file (this is the default)

2. Run the scraper:
   ```bash
   python main.py
   ```

3. **A browser window will open** showing the Teamie login page

4. Click **"Sign in with Google"**

5. Complete the Google authentication in the browser:
   - Enter your ASL Google email
   - Enter your password
   - Complete any 2FA if required

6. Wait for redirect back to the Teamie dashboard

7. **Your session is automatically saved!**

### After First Login

Once you've logged in once, your browser session is saved in `data/browser_session/`. Future runs will automatically load this session - no login required!

## Usage

### Regular Usage (After First Authentication)

Simply run:

```bash
python main.py
```

The scraper will:
1. Load your saved session
2. Navigate to Teamie
3. Scrape all courses, assignments, homework, and materials
4. Save results to `data/output/teamie_data_YYYYMMDD_HHMMSS.json`

### Running in Headless Mode

After your first authentication, you can run the scraper without a visible browser window:

```bash
# Edit .env and set HEADLESS=true
python main.py
```

## Configuration

Edit the `.env` file to customize settings:

```env
# Teamie URL (don't change unless your school uses a different URL)
TEAMIE_URL=https://lms.asl.org/dash/#/

# Your Google email (optional, for reference only)
GOOGLE_EMAIL=your.name@asl.org

# Run without visible browser window (set to false for first run)
HEADLESS=false

# Logging verbosity (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO

# Use persistent session (recommended)
USE_PERSISTENT_SESSION=true
```

## Output Format

Scraped data is saved to `data/output/teamie_data_YYYYMMDD_HHMMSS.json`

### Example Output Structure:

```json
{
  "scrape_timestamp": "2026-03-04T14:30:00",
  "user": null,
  "courses": [
    {
      "id": "math_101",
      "name": "Mathematics 101",
      "code": "MATH101",
      "instructor": "Dr. Smith"
    }
  ],
  "assignments": [
    {
      "id": "math_101_homework_5",
      "title": "Homework 5: Calculus Problems",
      "course_name": "Mathematics 101",
      "course_id": "math_101",
      "description": "Complete problems 1-20 from Chapter 5",
      "deadline": "2026-03-15T23:59:00",
      "status": "pending",
      "total_points": 100.0,
      "submission_url": "https://lms.asl.org/...",
      "attachments": ["worksheet.pdf"],
      "created_at": "2026-03-04T14:30:00"
    }
  ],
  "homework": [...],
  "materials": [...]
}
```

## Project Structure

```
/Volumes/Shared/VSCode/Kuzey_Time_Management/
├── teamie_scraper/          # Main package
│   ├── scraper.py          # Core scraping logic
│   ├── authenticator.py    # Google OAuth handling
│   ├── parsers.py          # HTML/DOM parsing
│   ├── models.py           # Data structures
│   ├── selectors.py        # CSS selectors
│   ├── utils.py            # Utilities
│   └── exceptions.py       # Custom exceptions
├── config/
│   ├── settings.py         # Configuration management
│   └── .env.example        # Configuration template
├── data/
│   ├── output/             # Scraped JSON files
│   └── browser_session/    # Browser session data (DO NOT COMMIT)
├── logs/                   # Error logs and screenshots
├── main.py                 # Entry point
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## Troubleshooting

### Login Fails

**Problem**: Can't complete Google login or authentication fails

**Solutions**:
- Delete the session directory and try again:
  ```bash
  rm -rf data/browser_session
  python main.py
  ```
- Make sure `HEADLESS=false` in your `.env` file
- Try using a different browser profile by deleting session data

### Session Expired

**Problem**: "Session expired" error during scraping

**Solution**: Same as "Login Fails" - delete session and re-authenticate

### Timeout Errors

**Problem**: Scraper times out waiting for page elements

**Solutions**:
- Check your internet connection
- The Teamie site might be slow - this is normal, retry
- Increase timeout in settings (not recommended unless necessary)

### No Data Found / Elements Not Found

**Problem**: Scraper completes but finds no assignments/homework/materials

**Possible Causes**:
1. **First run issue**: The CSS selectors in `teamie_scraper/selectors.py` are placeholders and need to be updated based on Teamie's actual HTML structure
2. **UI changed**: Teamie's interface may have been updated

**Solution**:
- Check the screenshots in `logs/` directory
- Inspect Teamie's HTML using browser DevTools
- Update selectors in [teamie_scraper/selectors.py](teamie_scraper/selectors.py) to match actual structure

### Browser Won't Open

**Problem**: Error about Playwright browsers not installed

**Solution**:
```bash
playwright install chromium
```

### Permission Errors

**Problem**: Can't write to files or directories

**Solution**:
- Check file permissions
- Make sure `data/` and `logs/` directories exist
- The scraper should create them automatically, but you can create manually if needed:
  ```bash
  mkdir -p data/output data/browser_session logs
  ```

## Updating Selectors (For Developers)

The selectors in [teamie_scraper/selectors.py](teamie_scraper/selectors.py) are **placeholders** and likely need adjustment based on Teamie's actual HTML structure.

### To Update Selectors:

1. Run the scraper with `HEADLESS=false`
2. When the browser opens, right-click on elements and select "Inspect"
3. Note the CSS classes and IDs used by Teamie
4. Update [teamie_scraper/selectors.py](teamie_scraper/selectors.py) with actual selectors
5. Test again

### Example:

If assignments use class `.assignment-card` instead of `.assignment-item`, update:

```python
ASSIGNMENT_CARD = ".assignment-card"  # Updated from .assignment-item
```

## Security Notes

- ⚠️ **Never commit** `data/browser_session/` - it contains your authentication cookies
- ⚠️ **Never commit** `.env` file - keep it local only
- Google credentials are NEVER stored in files (only browser session cookies)
- Session data is stored locally in `data/browser_session/`
- Each user should have their own copy of this directory
- The `.gitignore` file is configured to exclude sensitive files

## Scheduling Automated Runs (Optional)

Once you've completed the first authentication, you can schedule the scraper to run automatically.

### macOS/Linux (cron):

```bash
# Edit crontab
crontab -e

# Add line to run daily at 8 AM
0 8 * * * cd /Volumes/Shared/VSCode/Kuzey_Time_Management && /Volumes/Shared/VSCode/Kuzey_Time_Management/venv/bin/python main.py
```

### Windows (Task Scheduler):

1. Open Task Scheduler
2. Create Basic Task
3. Set trigger (e.g., daily at 8 AM)
4. Action: Start a Program
5. Program: `C:\Path\To\venv\Scripts\python.exe`
6. Arguments: `main.py`
7. Start in: `C:\Path\To\Kuzey_Time_Management`

## Development

### Running Tests

(Tests not yet implemented)

```bash
pytest
```

### Code Formatting

```bash
black teamie_scraper/ config/ main.py
```

## Known Limitations

1. **Selector Discovery Required**: The initial selectors are placeholders and need to be updated based on Teamie's actual HTML structure during first test run
2. **No File Downloads**: Only metadata for course materials is collected (file names, URLs, sizes), not the actual files
3. **SPA Navigation**: Teamie uses client-side routing with hash URLs (`#/dash`), which may require special handling
4. **Session Expiry**: Browser sessions may expire after extended periods (weeks/months) requiring re-authentication

## Future Enhancements

Potential features for future versions:

- Calendar export (.ics format) for assignment deadlines
- Email/Slack notifications for new assignments
- CSV export option
- Actual file downloads for course materials
- Incremental scraping (only fetch new/updated items)
- Web dashboard for viewing collected data

## License

MIT License - See LICENSE file for details

## Support

For issues or questions:

1. Check this README
2. Review logs in `logs/` directory
3. Check screenshots saved during errors
4. Inspect Teamie HTML to verify selectors

## Disclaimer

This scraper is for personal educational use only. Please respect your institution's terms of service and data usage policies. Do not abuse or overload the Teamie platform with excessive requests.

# Daily Needs Helper

Daily Needs Helper is a FastAPI web application for local community help requests. Users can create posts, discover nearby help, and manage trust and contact access with moderation controls.

## Tech Stack

- Python
- FastAPI
- SQLite
- SQLAlchemy
- Jinja2 templates
- HTML/CSS/JavaScript

## Current Capabilities

- User signup and login with token-based authentication
- Create and browse help posts
- Filter posts by city, category, and keyword
- Post status updates (open/resolved)
- Contact privacy with request and approve/reject flow
- Rate other users' posts and compute trust score per post
- Trusted helpers leaderboard
- Post reporting and admin moderation (remove/restore)

## Local Setup

1. Create a virtual environment.

   ```bash
   python -m venv .venv
   ```

2. Activate the environment.

   Linux/macOS:

   ```bash
   source .venv/bin/activate
   ```

   Windows PowerShell:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

3. Install dependencies.

   ```bash
   pip install -r requirements.txt
   ```

4. Start the server.

   ```bash
   python -m uvicorn main:app --reload
   ```

5. Open the app.

   [http://127.0.0.1:8000](http://127.0.0.1:8000)

## Important Notes

- This project does not include seeded demo records.
- If no users/posts exist yet, the UI will show empty states until data is created.

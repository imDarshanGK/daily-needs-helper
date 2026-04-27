# Daily Needs Helper

Daily Needs Helper is a FastAPI web app for local community support. Users can post daily needs, discover nearby help posts, and interact through ratings, reports, and controlled contact sharing.

## Features

- User signup and login (token-based auth)
- Create help posts (title, description, category, city, contact)
- Filter/search posts by city, category, and keyword
- Contact privacy flow (request, approve, reject)
- Ratings for other users' posts and trusted helpers leaderboard
- Post reporting and admin moderation (remove/restore)
- Post status updates (open/resolved)

## Tech Stack

- Python
- FastAPI
- SQLAlchemy
- SQLite
- Jinja2 templates
- HTML/CSS/JavaScript

## Project Structure

```text
main.py
templates/
  index.html
static/
  style.css
  favicon.svg
requirements.txt
```

## Run Locally

1. Create a virtual environment

   ```bash
   python -m venv .venv
   ```

2. Activate it

   Linux/macOS:

   ```bash
   source .venv/bin/activate
   ```

   Windows PowerShell:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

3. Install dependencies

   ```bash
   pip install -r requirements.txt
   ```

4. Start the app

   ```bash
   python -m uvicorn main:app --reload
   ```

5. Open in browser

   http://127.0.0.1:8000

## Notes

- This project does not include seeded demo data.
- Empty states are expected until users create accounts and posts.

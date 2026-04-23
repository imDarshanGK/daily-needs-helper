# Daily Needs Helper (Community Help Hub)

A simple community platform where users can post and discover daily needs such as notes, rooms, tutors, small jobs, and emergencies.

## Tech Stack

- Python
- FastAPI
- SQLite
- HTML/CSS/JavaScript

## Features (MVP)

- User signup and login
- Create help posts
- Search/filter posts by city, category, and keyword
- Basic authorization using bearer token
- Post status management (open/resolved)
- Report post flow for moderation
- Admin moderation panel (remove/restore reported posts)
- Trusted helpers leaderboard
- Contact privacy with request/approve flow

## Run Locally

1. Create virtual environment:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

3. Start server:

   ```powershell
   uvicorn main:app --reload
   ```

4. Open app:

   [http://127.0.0.1:8000](http://127.0.0.1:8000)

## Next Upgrades

- Ratings and trust score
- Notifications
- Post moderation dashboard
- AI suggestions for related help posts

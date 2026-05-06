# Daily Needs Helper

A community-first platform for posting local needs, discovering helpers, and building trust through ratings, with privacy controls built in.

## Overview

Daily Needs Helper is a small but complete community support app built with FastAPI and a vanilla JavaScript frontend. It focuses on practical local use: post a need, find help nearby, request contact securely, and build trust through ratings and moderation.

## Highlights

- FastAPI backend with SQLite persistence
- Token-based authentication with session validation
- Search, sort, and pagination for help posts
- Contact privacy workflow with approve/reject requests
- Ratings, trusted helpers, reports, and admin moderation
- Inline editing, validation, and loading feedback in the UI

## Features

- **User Authentication** - Token-based signup/login with session validation
- **Help Posts** - Create posts with title, description, category, city, and contact info
- **Smart Search** - Filter by city, category, or keyword; find help faster
- **Privacy Control** - Request contact info; post owners approve/reject access
- **Trust System** - Rate helpers and view top trusted members by score
- **Moderation** - Users can report posts; admins review and take action
- **Status Tracking** - Mark posts as open or resolved
- **Form Validation** - Real-time client-side feedback on all fields
- **Loading States** - Visual feedback during async operations
- **Password Visibility** - Toggle to show/hide passwords while typing
- **Copy-to-Clipboard** - Quick copy contact details from post listings
- **Category Autocomplete** - Suggestions for common post categories

## Tech Stack

- **Backend**: Python, FastAPI, SQLAlchemy
- **Database**: SQLite (lightweight, no server required)
- **Frontend**: HTML5, CSS3, Vanilla JavaScript (no frameworks)
- **Templates**: Jinja2
- **Auth**: Bearer token (localStorage-based)

## Project Structure

```text
main.py                 # FastAPI app and routes
templates/
  index.html           # Single-page app markup, validation, UI logic
static/
  style.css            # Responsive design, dark/light theming
  favicon.svg          # App icon
requirements.txt       # Python dependencies
LICENSE                # MIT license text
database.db            # SQLite database (created on first run)
```

## Local Setup

### Prerequisites
- Python 3.8+
- pip
- Virtual environment (recommended)

### Installation

1. **Clone and navigate**
   ```bash
   cd daily-needs-helper
   ```

2. **Create and activate virtual environment**

   Linux/macOS:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

   Windows PowerShell:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the app**
   ```bash
   python -m uvicorn main:app --reload
   ```

5. **Open in browser**
   ```
   http://localhost:8000
   ```

## Features in Detail

### Authentication Flow
- New users sign up with username, city, password (all required)
- Token stored in localStorage, validated on app startup via `/api/me`
- Sessions auto-expire; users see clear "Session expired" message
- Logout button clears all local state

### Post Creation
- Title: 5+ characters
- Description: 10+ characters
- Category: 2+ chars (autocomplete suggestions: Room, Tutor, Notes, Job, Emergency)
- City: 2+ characters
- Contact: 3+ characters (phone/email)
- All fields show live validation errors as user types

### Contact Privacy
- Post owners see a "Private (preview)" note for their own contact
- Other logged-in users can request contact
- Owner receives requests in "Inbox" tab
- Owner can approve (share contact) or reject
- Approved users see full contact on post

### Ratings & Trust
- Only logged-in users can rate posts (can't rate own posts)
- Rating: 1-5 stars, optional comment
- Top Trusted Helpers shows top 5 by average rating score
- Ratings visible on each post (e.g., "★★★★☆ 4/5 from 3 ratings")




## Architecture

```
Request Flow:
┌─────────────────┐
│  Browser (SPA)  │
│  index.html     │
└────────┬────────┘
         │ JSON API calls (Bearer token auth)
         ▼
┌─────────────────┐
│  FastAPI App    │
│  (main.py)      │
└────────┬────────┘
         │ SQLAlchemy ORM
         ▼
┌─────────────────┐
│  SQLite DB      │
│  (database.db)  │
└─────────────────┘
```

## Security

- **Passwords**: Hashed with `passlib` (bcrypt)
- **Tokens**: Bearer tokens stored in localStorage (XSS-vulnerable; use httpOnly cookies in production)
- **Contact Privacy**: Enforced at API level; users can't see contact info without owner approval
- **Reporting**: Only post owners and admins can modify posts
- **CSRF**: Disabled for JSON API (add protection if using form submissions)

## Performance Notes

- **Database**: SQLite suitable for <1M posts. For larger scale, migrate to PostgreSQL
- **Frontend**: No external dependencies (fast load), all validation client-side
- **Responses**: Paginated posts (limit 20 per request by default)
- **Caching**: User session cached in localStorage; cleared on logout


## Contributing

- Fork the repo
- Create a feature branch: `git checkout -b feature/your-feature`
- Commit with clear messages: `git commit -m "feat: add xyz"`
- Push and create a pull request

## License

This project is licensed under the MIT License.
See [LICENSE](LICENSE) for full details.

## Live Demo

https://helpyo.onrender.com

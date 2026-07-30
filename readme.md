# Movie Tracker

A small FastAPI + SingleStore app for tracking movies/series you want to
watch, are watching, or have watched. Titles are pulled from TMDB.

## Setup

1. Create and activate a virtual environment:
   ```bash
   python3 -m venv ~/venvs/singlestore-project
   source ~/venvs/singlestore-project/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env` and fill in your SingleStore credentials
   and TMDB API key (free, from https://www.themoviedb.org/settings/api):
   ```bash
   cp .env.example .env
   ```

4. Create the database and tables:
   ```bash
   python db.py
   ```

5. Run the app:
   ```bash
   uvicorn main:app --reload
   ```

6. Open http://127.0.0.1:8000

## Project layout

- `db.py` — connection helper + schema creation
- `models.py` — Pydantic models
- `tmdb.py` — TMDB API client (search + details)
- `main.py` — FastAPI routes
- `templates/` — Jinja2 HTML templates

## Next steps / ideas to extend it

- Add real auth (currently a single hardcoded `DEFAULT_USER_ID`)
- Add pagination once your list grows
- Chart genre/rating trends with Chart.js on the dashboard
- Compare rowstore vs columnstore performance once you have more data
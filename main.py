import os
import secrets
from fastapi import FastAPI, Request, Form, status
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from itsdangerous import URLSafeSerializer
from dotenv import load_dotenv

import db_utils as db
import tmdb

import db_utils as db
import tmdb

load_dotenv()

app = FastAPI(title="Movie Tracker")
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key-change-me")
serializer = URLSafeSerializer(SECRET_KEY)

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

DEFAULT_USER_ID = int(os.getenv("DEFAULT_USER_ID", "1"))

def get_current_user(request: Request):
    """Helper to check if the user has a valid login cookie."""
    auth_cookie = request.cookies.get("session")
    if not auth_cookie:
        return None
    try:
        return serializer.loads(auth_cookie)
    except Exception:
        return None

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    expected_username = os.getenv("APP_USERNAME")
    expected_password = os.getenv("APP_PASSWORD")

    is_user_valid = secrets.compare_digest(username, expected_username)
    is_pass_valid = secrets.compare_digest(password, expected_password)

    if not (is_user_valid and is_pass_valid):
        return templates.TemplateResponse("login.html", {
            "request": request, 
            "error": "Invalid username or password"
        })

    # Login successful! Set cookie and redirect to main page
    response = RedirectResponse("/", status_code=302)
    session_token = serializer.dumps(username)
    response.set_cookie(key="session", value=session_token, httponly=True)
    return response

@app.get("/logout")
def logout():
    response = RedirectResponse(url="/login")
    response.delete_cookie("session")
    return response

# ---------- Watchlist views ----------

@app.get("/")
def home(request: Request, status: str = "want_to_watch"):
    """Show titles filtered by status. Defaults to the want-to-watch list."""
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT t.id, t.name, t.type, t.genre, t.release_year,
               t.poster_url, ws.id AS watch_id, ws.status, ws.rating
        FROM watch_status ws
        JOIN titles t ON t.id = ws.title_id
        WHERE ws.user_id = %s AND ws.status = %s
        ORDER BY ws.date_added DESC
        """,
        (DEFAULT_USER_ID, status),
    )
    columns = [c[0] for c in cur.description]
    rows = [dict(zip(columns, row)) for row in cur.fetchall()]
    cur.close()
    conn.close()
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "rows": rows, "current_status": status},
    )

@app.get("/watching")
def home(request: Request, status: str = "watching"):
    """Show titles filtered by status. Defaults to the want-to-watch list."""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT t.id, t.name, t.type, t.genre, t.release_year,
               t.poster_url, ws.id AS watch_id, ws.status, ws.rating, ws.episode_progress
        FROM watch_status ws
        JOIN titles t ON t.id = ws.title_id
        WHERE ws.user_id = %s AND ws.status = %s
        ORDER BY ws.date_added DESC
        """,
        (DEFAULT_USER_ID, status),
    )
    columns = [c[0] for c in cur.description]
    rows = [dict(zip(columns, row)) for row in cur.fetchall()]
    cur.close()
    conn.close()
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "rows": rows, "current_status": status},
    )

@app.post("/watch-status/{watch_id}/update")
def update_status(request: Request, watch_id: int, status: str = Form(...), rating: str = Form(None), episode: str = Form(None)):
    """Move a title between want_to_watch / watching / watched, set a rating, and track episode progress."""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    

    conn = db.get_connection()
    cur = conn.cursor()
    
    rating_value = int(rating) if rating else None
    episode_value = int(episode) if episode else 0
    date_watched_clause = ", date_watched = NOW()" if status == "watched" else ""
    
    cur.execute(
        f"""
        UPDATE watch_status
        SET status = %s, rating = %s, episode_progress = %s {date_watched_clause}
        WHERE id = %s AND user_id = %s
        """,
        (status, rating_value, episode_value, watch_id, DEFAULT_USER_ID),
    )
    cur.close()
    conn.close()
    return RedirectResponse("/watching", status_code=303)


@app.post("/watch-status/{watch_id}/delete")
def delete_status(request: Request, watch_id: int):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM watch_status WHERE id = %s AND user_id = %s",
        (watch_id, DEFAULT_USER_ID),
    )
    cur.close()
    conn.close()
    return RedirectResponse("/", status_code=303)


# ---------- Search / add via TMDB ----------

@app.get("/search")
def search_page(request: Request, q: str = ""):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    results = tmdb.search(q) if q else []
    return templates.TemplateResponse(
        "search.html", {"request": request, "query": q, "results": results}
    )


@app.post("/add")
def add_title(
    request: Request,
    tmdb_id: int = Form(...),
    name: str = Form(...),
    type: str = Form(...),
    genre: str = Form(None),
    release_year: str = Form(None),
    poster_url: str = Form(None),
):
    """Insert a title (if not already in our DB) and add it to the watchlist."""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    conn = db.get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM titles WHERE tmdb_id = %s", (tmdb_id,))
    existing = cur.fetchone()

    if existing:
        title_id = existing[0]
    else:
        media_type = "movie" if type == "movie" else "tv"
        details = tmdb.get_details(tmdb_id, media_type)
        cur.execute(
            """
            INSERT INTO titles (tmdb_id, name, type, genre, release_year,
                                 total_runtime_minutes, poster_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                tmdb_id, name, type, genre,
                int(release_year) if release_year else None,
                details.get("total_runtime_minutes"),
                poster_url,
            ),
        )
        cur.execute("SELECT id FROM titles WHERE tmdb_id = %s", (tmdb_id,))
        title_id = cur.fetchone()[0]

    cur.execute(
        """
        INSERT INTO watch_status (user_id, title_id, status)
        VALUES (%s, %s, 'want_to_watch')
        """,
        (DEFAULT_USER_ID, title_id),
    )
    cur.close()
    conn.close()
    return RedirectResponse("/", status_code=303)


# ---------- Dashboard ----------

@app.get("/dashboard")
def dashboard(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    conn = db.get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT t.genre, COUNT(*) AS watched_count, AVG(ws.rating) AS avg_rating
        FROM watch_status ws
        JOIN titles t ON t.id = ws.title_id
        WHERE ws.user_id = %s AND ws.status = 'watched' AND t.genre IS NOT NULL
        GROUP BY t.genre
        ORDER BY watched_count DESC
        """,
        (DEFAULT_USER_ID,),
    )
    genre_stats = cur.fetchall()

    cur.execute(
        """
        SELECT DATE_FORMAT(date_watched, '%%Y-%%m') AS month, COUNT(*) AS count
        FROM watch_status
        WHERE user_id = %s AND status = 'watched' AND date_watched IS NOT NULL
        GROUP BY month
        ORDER BY month
        """,
        (DEFAULT_USER_ID,),
    )
    monthly_stats = cur.fetchall()

    cur.close()
    conn.close()
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "genre_stats": genre_stats, "monthly_stats": monthly_stats},
    )
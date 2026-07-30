"""
Thin wrapper around the TMDB API (v3).
Docs: https://developer.themoviedb.org/reference/intro/getting-started
"""
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
BASE_URL = "https://api.themoviedb.org/3"
IMAGE_BASE = "https://image.tmdb.org/t/p/w342"

GENRE_CACHE = {}  # populated on first use, maps genre_id -> name


def _get(path: str, params: dict = None):
    params = params or {}
    params["api_key"] = TMDB_API_KEY
    resp = httpx.get(f"{BASE_URL}{path}", params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()


def _load_genres():
    """TMDB genres for movies and TV are separate lists with overlapping IDs.
    We merge them into one cache; good enough for a small hobby app."""
    if GENRE_CACHE:
        return
    for media_type in ("movie", "tv"):
        data = _get(f"/genre/{media_type}/list")
        for g in data.get("genres", []):
            GENRE_CACHE[g["id"]] = g["name"]


def search(query: str, media_type: str = "multi") -> list[dict]:
    """Search TMDB for movies/series matching a query string.
    Returns a simplified list of dicts ready to display or insert."""
    _load_genres()
    data = _get(f"/search/{media_type}", {"query": query})
    results = []
    for item in data.get("results", []):
        item_type = item.get("media_type", media_type)
        if item_type not in ("movie", "tv"):
            continue  # skip people, etc. from multi-search
        genre_ids = item.get("genre_ids", [])
        genre_names = ", ".join(GENRE_CACHE.get(g, "") for g in genre_ids if g in GENRE_CACHE)
        results.append({
            "tmdb_id": item["id"],
            "name": item.get("title") or item.get("name"),
            "type": "movie" if item_type == "movie" else "series",
            "genre": genre_names or None,
            "release_year": _extract_year(item.get("release_date") or item.get("first_air_date")),
            "poster_url": f"{IMAGE_BASE}{item['poster_path']}" if item.get("poster_path") else None,
        })
    return results


def get_details(tmdb_id: int, media_type: str) -> dict:
    """Fetch runtime (and season count, for series) info for a specific title
    (not included in search results)."""
    path = f"/movie/{tmdb_id}" if media_type == "movie" else f"/tv/{tmdb_id}"
    data = _get(path)
    if media_type == "movie":
        runtime = data.get("runtime")
        total_seasons = None
    else:
        episode_runtimes = data.get("runtime", [])
        runtime = episode_runtimes[0] if episode_runtimes else None
        total_seasons = data.get("number_of_seasons")
    return {"runtime": runtime, "total_seasons": total_seasons}


def _extract_year(date_str: str | None) -> int | None:
    if not date_str:
        return None
    try:
        return int(date_str.split("-")[0])
    except (ValueError, IndexError):
        return None
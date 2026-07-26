from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class WatchStatus(BaseModel):
    id: int
    user_id: int
    title_id: int
    status: str
    rating: Optional[int] = None
    episode_progress: Optional[int] = 0  # <--- Add this line
    date_added: Optional[datetime] = None
    date_watched: Optional[datetime] = None


class WatchStatus(BaseModel):
    id: int
    user_id: int
    title_id: int
    status: str
    rating: Optional[int] = None
    date_added: Optional[datetime] = None
    date_watched: Optional[datetime] = None
from datetime import datetime

from pydantic import BaseModel


class Clip(BaseModel):
    title: str
    thumbnail_url: str
    creator_name: str
    created_at: datetime

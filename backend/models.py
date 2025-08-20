from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class Ticket(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    description: str
    status: str = "open"       # open / closed / escalated
    priority: str = "medium"   # low / medium / high
    created_at: datetime = Field(default_factory=datetime.utcnow)
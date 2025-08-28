from uuid import UUID
from uuid import uuid4
from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class Ticket(SQLModel, table=True):
    """
    Ticket model for customer support tickets.
    """
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    ticket_number: Optional[int] = Field(default=None, index=True, unique=True, )
    customer_id: str = Field(index=True) # phone/email/uuid
    title: str
    description: str
    status: str = "open"       # open / closed / escalated
    priority: str = "medium"   # low / medium / high
    created_at: datetime = Field(default_factory=datetime.utcnow)
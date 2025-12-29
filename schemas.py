from pydantic import BaseModel
from typing import Optional

class NotionEvent(BaseModel):
	id: str
	title: str
	days_remaining: Optional[str] = "Unknown"
	due_date: Optional[str] = "No due date"
	priority: Optional[str] = "Unknown"
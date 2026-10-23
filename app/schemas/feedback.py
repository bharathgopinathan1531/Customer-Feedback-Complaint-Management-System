from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.feedback import FeedbackStatus


class FeedbackCreate(BaseModel):
    category: str = Field(min_length=2, max_length=100)
    rating: int = Field(ge=1, le=5)
    description: str = Field(min_length=5, max_length=5000)


class FeedbackUpdate(BaseModel):
    category: str | None = Field(default=None, min_length=2, max_length=100)
    rating: int | None = Field(default=None, ge=1, le=5)
    description: str | None = Field(default=None, min_length=5, max_length=5000)


class FeedbackStatusUpdate(BaseModel):
    status: FeedbackStatus


class FeedbackResponse(BaseModel):
    id: int
    customer_id: int
    category: str
    rating: int
    description: str
    status: FeedbackStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

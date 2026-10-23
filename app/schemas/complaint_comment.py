from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ComplaintCommentCreate(BaseModel):
    comment: str = Field(min_length=1, max_length=5000)

    @field_validator("comment")
    @classmethod
    def strip_comment(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Comment cannot be empty")
        return value


class ComplaintCommentResponse(BaseModel):
    id: int
    complaint_id: int
    user_id: int
    comment: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

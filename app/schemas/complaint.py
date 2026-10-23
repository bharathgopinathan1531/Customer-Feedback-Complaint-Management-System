from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.complaint import ComplaintPriority, ComplaintStatus


class ComplaintCreate(BaseModel):
    category_id: int = Field(gt=0)
    subject: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=5, max_length=5000)
    priority: ComplaintPriority = ComplaintPriority.MEDIUM
    attachment_urls: list[str] = Field(default_factory=list, max_length=10)

    @field_validator("attachment_urls")
    @classmethod
    def validate_attachment_urls(cls, values: list[str]) -> list[str]:
        cleaned = []
        for value in values:
            value = value.strip()
            if not value:
                raise ValueError("Attachment URLs cannot be empty")
            if not value.startswith(("https://", "http://")):
                raise ValueError("Attachment URLs must use HTTP or HTTPS")
            cleaned.append(value)
        return cleaned

    @field_validator("subject", "description")
    @classmethod
    def strip_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be empty")
        return value


class ComplaintUpdate(BaseModel):
    subject: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = Field(default=None, min_length=5, max_length=5000)
    priority: ComplaintPriority | None = None

    @field_validator("subject", "description")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be empty")
        return value


class ComplaintStatusUpdate(BaseModel):
    status: ComplaintStatus
    resolution_notes: str | None = Field(default=None, max_length=5000)

    @field_validator("resolution_notes")
    @classmethod
    def strip_resolution_notes(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("Resolution notes cannot be empty")
        return value


class ComplaintResponse(BaseModel):
    id: int
    reference_number: str | None = None
    customer_id: int
    category_id: int
    assigned_to_user_id: int | None = None
    subject: str
    description: str
    attachment_urls: list[str] = Field(default_factory=list)
    priority: ComplaintPriority
    status: ComplaintStatus
    created_at: datetime
    updated_at: datetime
    resolution_notes: str | None = None
    resolved_at: datetime | None = None
    closed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ComplaintAssignment(BaseModel):
    assigned_to_user_id: int = Field(gt=0)

from pathlib import Path

path = Path("app/schemas/complaint.py")
content = path.read_text(encoding="utf-8")

old = '''class ComplaintCreate(BaseModel):
    category_id: int = Field(gt=0)
    subject: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=5, max_length=5000)
    priority: ComplaintPriority = ComplaintPriority.MEDIUM'''

new = '''class ComplaintCreate(BaseModel):
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
        return cleaned'''

if old not in content:
    raise SystemExit("Could not locate ComplaintCreate schema. No changes made.")

content = content.replace(old, new, 1)

old = '''class ComplaintResponse(BaseModel):
    id: int
    customer_id: int'''

new = '''class ComplaintResponse(BaseModel):
    id: int
    reference_number: str | None = None
    customer_id: int'''

if old not in content:
    raise SystemExit("Could not locate ComplaintResponse fields. No changes made.")

content = content.replace(old, new, 1)

old = '''    description: str
    priority: ComplaintPriority
    status: ComplaintStatus'''

new = '''    description: str
    attachment_urls: list[str] = Field(default_factory=list)
    priority: ComplaintPriority
    status: ComplaintStatus'''

if old not in content:
    raise SystemExit("Could not locate response description fields. No changes made.")

content = content.replace(old, new, 1)

path.write_text(content, encoding="utf-8")
print("Complaint schemas updated.")

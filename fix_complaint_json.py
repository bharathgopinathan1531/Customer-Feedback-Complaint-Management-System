from pathlib import Path

path = Path("app/models/complaint.py")
content = path.read_text(encoding="utf-8")

if "    JSON,\n" not in content:
    content = content.replace(
        "from sqlalchemy import (\n",
        "from sqlalchemy import (\n    JSON,\n",
        1,
    )

old = '''    attachment_urls: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )'''

new = '''    attachment_urls: Mapped[list[str] | None] = mapped_column(
        JSON, nullable=True
    )'''

if old in content:
    content = content.replace(old, new, 1)
elif new not in content:
    raise SystemExit("Attachment field not found. No changes saved.")

path.write_text(content, encoding="utf-8")
print("Attachment field now uses SQLAlchemy JSON.")

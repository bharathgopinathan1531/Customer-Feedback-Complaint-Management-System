from pathlib import Path

path = Path("app/models/complaint.py")
content = path.read_text(encoding="utf-8")

old = '''    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    customer_id: Mapped[int] = mapped_column('''

new = '''    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    reference_number: Mapped[str | None] = mapped_column(
        String(30), unique=True, nullable=True, index=True
    )

    customer_id: Mapped[int] = mapped_column('''

if old not in content:
    raise SystemExit("Could not locate complaint ID fields. No changes made.")

if "reference_number:" not in content:
    content = content.replace(old, new, 1)

old = '''    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)'''

new = '''    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    attachment_urls: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )'''

if "attachment_urls:" not in content:
    if old not in content:
        raise SystemExit("Could not locate complaint subject fields. No changes made.")
    content = content.replace(old, new, 1)

path.write_text(content, encoding="utf-8")
print("Complaint model updated.")

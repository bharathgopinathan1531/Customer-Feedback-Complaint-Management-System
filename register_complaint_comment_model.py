from pathlib import Path

path = Path("app/main.py")
content = path.read_text(encoding="utf-8")

import_line = "from app.models.complaint_comment import ComplaintComment"

if import_line not in content:
    marker = "from app.models.complaint_status_history import ComplaintStatusHistory"
    if marker not in content:
        raise SystemExit("Could not find the existing complaint history import.")
    content = content.replace(marker, import_line + "\n" + marker, 1)

path.write_text(content, encoding="utf-8")
print("Complaint comment model registered.")

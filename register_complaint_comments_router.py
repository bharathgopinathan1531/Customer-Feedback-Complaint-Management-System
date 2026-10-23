from pathlib import Path

path = Path("app/main.py")
content = path.read_text(encoding="utf-8")

import_line = "from app.api.complaint_comments import router as complaint_comments_router"

if import_line not in content:
    marker = "from app.api.complaints import router as complaints_router"
    if marker not in content:
        raise SystemExit("Existing complaints router import not found.")
    content = content.replace(marker, marker + "\n" + import_line, 1)

include_line = "app.include_router(complaint_comments_router)"

if include_line not in content:
    marker = "app.include_router(complaints_router)"
    if marker not in content:
        raise SystemExit("Existing complaints router registration not found.")
    content = content.replace(marker, marker + "\n" + include_line, 1)

path.write_text(content, encoding="utf-8")
print("Complaint comments router registered.")

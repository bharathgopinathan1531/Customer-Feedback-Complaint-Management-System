from pathlib import Path

path = Path("app/main.py")
content = path.read_text(encoding="utf-8")

import_line = "from app.api.analytics import router as analytics_router"
include_line = "app.include_router(analytics_router)"

if import_line not in content:
    marker = "from app.api.notifications import router as notifications_router"
    if marker not in content:
        raise SystemExit("Could not find the notifications router import. No changes made.")
    content = content.replace(marker, marker + "\n" + import_line, 1)

if include_line not in content:
    marker = "app.include_router(notifications_router)"
    if marker not in content:
        raise SystemExit("Could not find the notifications router registration. No changes made.")
    content = content.replace(marker, marker + "\n" + include_line, 1)

path.write_text(content, encoding="utf-8")
print("Analytics router registered.")

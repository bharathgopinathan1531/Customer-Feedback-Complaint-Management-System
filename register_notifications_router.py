from pathlib import Path

path = Path("app/main.py")
content = path.read_text(encoding="utf-8")

import_line = "from app.api.notifications import router as notifications_router"
include_line = "app.include_router(notifications_router)"

if import_line not in content:
    marker = "from app.api.sla import router as sla_router"
    if marker not in content:
        raise SystemExit("Could not find the SLA router import in app/main.py.")
    content = content.replace(marker, marker + "\n" + import_line, 1)

if include_line not in content:
    marker = "app.include_router(sla_router)"
    if marker not in content:
        raise SystemExit("Could not find app.include_router(sla_router) in app/main.py.")
    content = content.replace(marker, marker + "\n" + include_line, 1)

path.write_text(content, encoding="utf-8")
print("Notifications router registered.")

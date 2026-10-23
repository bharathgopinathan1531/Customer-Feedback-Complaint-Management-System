from pathlib import Path

path = Path("app/main.py")
content = path.read_text(encoding="utf-8")

import_lines = [
    "from app.api.dashboard import dashboard_router, reports_router",
]
include_lines = [
    "app.include_router(dashboard_router)",
    "app.include_router(reports_router)",
]

for line in import_lines:
    if line not in content:
        marker = "from app.api.analytics import router as analytics_router"
        if marker not in content:
            raise SystemExit("Analytics router import not found. No changes made.")
        content = content.replace(marker, marker + "\n" + line, 1)

for line in include_lines:
    if line not in content:
        marker = "app.include_router(analytics_router)"
        if marker not in content:
            raise SystemExit("Analytics router registration not found. No changes made.")
        content = content.replace(marker, marker + "\n" + line, 1)

path.write_text(content, encoding="utf-8")
print("Dashboard and Reports routers registered.")

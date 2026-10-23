from pathlib import Path

path = Path("app/main.py")
text = path.read_text(encoding="utf-8")

import_line = "from app.api.audit_logs import router as audit_logs_router"
if import_line not in text:
    marker = "from app.api.auth import router as auth_router"
    if marker not in text:
        raise SystemExit("Could not find auth router import in app/main.py")
    text = text.replace(marker, import_line + "\n" + marker, 1)

include_line = "app.include_router(audit_logs_router)"
if include_line not in text:
    marker = "app.include_router(auth_router)"
    if marker not in text:
        raise SystemExit("Could not find auth router registration in app/main.py")
    text = text.replace(marker, include_line + "\n" + marker, 1)

path.write_text(text, encoding="utf-8")
print("Audit Logs router registered.")

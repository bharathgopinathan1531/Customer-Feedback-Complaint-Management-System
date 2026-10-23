from pathlib import Path

path = Path("app/main.py")
content = path.read_text(encoding="utf-8")

line = "from app.models.notification import Notification"

if line not in content:
    marker = "from app.models.complaint_comment import ComplaintComment"
    if marker not in content:
        raise SystemExit("Could not find the complaint comment model import.")
    content = content.replace(marker, marker + "\n" + line, 1)

path.write_text(content, encoding="utf-8")
print("Notification model registered.")

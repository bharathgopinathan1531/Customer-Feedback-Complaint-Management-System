from pathlib import Path

init_path = Path("app/models/__init__.py")
content = init_path.read_text(encoding="utf-8-sig")

if "from app.models.refresh_token import RefreshToken" not in content:
    content += "\nfrom app.models.refresh_token import RefreshToken\n"

if '"RefreshToken"' not in content:
    content = content.replace(
        '    "Category",\n',
        '    "Category",\n    "RefreshToken",\n',
    )

init_path.write_text(content, encoding="utf-8")

main_path = Path("app/main.py")
content = main_path.read_text(encoding="utf-8-sig")

old = "from app.models import User, Customer, Feedback, Category, Complaint"
new = "from app.models import User, Customer, Feedback, Category, Complaint, RefreshToken"

if old in content:
    content = content.replace(old, new, 1)
elif "RefreshToken" not in content:
    raise SystemExit(
        "Expected model import line not found in app/main.py. No main.py changes made."
    )

main_path.write_text(content, encoding="utf-8")
print("RefreshToken model created and registered.")

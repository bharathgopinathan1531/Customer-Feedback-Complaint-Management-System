from pathlib import Path

main_path = Path("app/main.py")
text = main_path.read_text(encoding="utf-8")

if "from app.models.audit_log import AuditLog" not in text:
    marker = "from app.models.complaint_status_history import ComplaintStatusHistory"
    if marker not in text:
        raise SystemExit("Could not find model import marker in app/main.py")
    text = text.replace(
        marker,
        marker + "\nfrom app.models.audit_log import AuditLog",
        1,
    )

main_path.write_text(text, encoding="utf-8")

models_path = Path("app/models/__init__.py")
models_text = models_path.read_text(encoding="utf-8")

if "from app.models.audit_log import AuditLog" not in models_text:
    models_text += "\nfrom app.models.audit_log import AuditLog\n"

if '"AuditLog"' not in models_text:
    models_text = models_text.replace(
        '    "Category",',
        '    "Category",\n    "AuditLog",',
        1,
    )

models_path.write_text(models_text, encoding="utf-8")

print("AuditLog registered.")

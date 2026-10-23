from pathlib import Path

init_path = Path("app/models/__init__.py")
content = init_path.read_text(encoding="utf-8-sig")

if "from app.models.password_reset_token import PasswordResetToken" not in content:
    content += "\nfrom app.models.password_reset_token import PasswordResetToken\n"

if '"PasswordResetToken"' not in content:
    content = content.replace(
        '    "RefreshToken",\n',
        '    "RefreshToken",\n    "PasswordResetToken",\n',
    )

init_path.write_text(content, encoding="utf-8")

main_path = Path("app/main.py")
main_content = main_path.read_text(encoding="utf-8-sig")

if "PasswordResetToken" not in main_content:
    import_line = next(
        line for line in main_content.splitlines()
        if line.startswith("from app.models import ")
    )
    updated_line = import_line.rstrip() + ", PasswordResetToken"
    main_content = main_content.replace(import_line, updated_line, 1)
    main_path.write_text(main_content, encoding="utf-8")

print("Password reset token model registered.")

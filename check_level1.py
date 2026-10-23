from app.main import app

schema = app.openapi()

print("=== AUTHENTICATION APIs ===")
for path, methods in sorted(schema["paths"].items()):
    if "/auth" in path.lower() or "/admin" in path.lower():
        for method, details in methods.items():
            print(f"{method.upper():7} {path}")

print("\n=== AUTH AND ADMIN SOURCE FILES ===")
from pathlib import Path

for filename in ["app/api/auth.py", "app/api/admin.py", "app/api/deps.py"]:
    path = Path(filename)
    print(f"\n--- {filename} ---")
    if path.exists():
        print(path.read_text(encoding="utf-8-sig"))
    else:
        print("FILE NOT FOUND")

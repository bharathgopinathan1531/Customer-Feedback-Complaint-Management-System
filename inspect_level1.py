from pathlib import Path

files = [
    "app/core/security.py",
    "app/schemas/auth.py",
    "app/models/user.py",
    "app/db/session.py",
    "tests/test_auth.py",
]

for filename in files:
    path = Path(filename)
    print(f"\n{'=' * 20} {filename} {'=' * 20}")
    if path.exists():
        print(path.read_text(encoding="utf-8-sig"))
    else:
        print("FILE NOT FOUND")

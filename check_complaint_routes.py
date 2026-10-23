import fastapi
from app.main import app
from app.api.complaints import router

print("FastAPI version:", fastapi.__version__)
print("App route types:")
for route in app.routes:
    print(type(route).__name__, getattr(route, "path", "(no path)"))

print("\nRouter route types:")
for route in router.routes:
    print(type(route).__name__, getattr(route, "path", "(no path)"))

print("\nOpenAPI complaint paths:")
schema = app.openapi()
for path in schema["paths"]:
    if "complaint" in path.lower():
        print(path)

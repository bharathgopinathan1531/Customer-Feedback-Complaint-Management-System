import json
from pathlib import Path
from app.main import app

schema = app.openapi()
items = []

for path, path_data in schema.get("paths", {}).items():
    requests = []

    for method, details in path_data.items():
        if method.lower() not in {
            "get", "post", "put", "patch", "delete", "options", "head"
        }:
            continue

        name = details.get("summary") or details.get("operationId") or f"{method.upper()} {path}"
        url_path = path
        path_variables = []

        for part in path.split("/"):
            if part.startswith("{") and part.endswith("}"):
                variable = part[1:-1]
                path_variables.append({
                    "key": variable,
                    "value": "1",
                    "description": f"Replace with actual {variable}"
                })
                url_path = url_path.replace(part, "{{" + variable + "}}")

        request = {
            "name": name,
            "request": {
                "method": method.upper(),
                "header": [],
                "url": {
                    "raw": "{{baseUrl}}" + url_path,
                    "host": ["{{baseUrl}}"],
                    "path": [p for p in url_path.strip("/").split("/") if p],
                }
            },
            "response": []
        }

        if path_variables:
            request["request"]["url"]["variable"] = path_variables

        if method.lower() not in {"get", "head", "options"}:
            request["request"]["header"].append({
                "key": "Content-Type",
                "value": "application/json"
            })
            request["request"]["body"] = {
                "mode": "raw",
                "raw": "{}",
                "options": {"raw": {"language": "json"}}
            }

        security = details.get("security", schema.get("security", []))
        if security:
            request["request"]["auth"] = {
                "type": "bearer",
                "bearer": [{"key": "token", "value": "{{token}}", "type": "string"}]
            }

        requests.append(request)

    if requests:
        items.append({
            "name": path,
            "item": requests
        })

collection = {
    "info": {
        "name": "Customer Feedback and Complaint Management System",
        "description": (
            "Generated from the FastAPI OpenAPI schema. "
            "Set baseUrl and token variables before testing. "
            "Replace placeholder request bodies with valid schema fields."
        ),
        "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
    },
    "item": items,
    "variable": [
        {"key": "baseUrl", "value": "http://127.0.0.1:8000"},
        {"key": "token", "value": ""}
    ]
}

output = Path("postman/customer-feedback-system.postman_collection.json")
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(collection, indent=2), encoding="utf-8")

# Verify that the saved file is valid JSON.
saved = json.loads(output.read_text(encoding="utf-8"))
print(f"Created: {output}")
print(f"Route groups: {len(saved['item'])}")
print(f"Requests: {sum(len(group['item']) for group in saved['item'])}")
print("JSON validation: PASS")

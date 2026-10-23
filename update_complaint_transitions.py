from pathlib import Path

path = Path("app/api/complaints.py")
content = path.read_text(encoding="utf-8")

old = '''    allowed_transitions = {
        ComplaintStatus.OPEN: {ComplaintStatus.IN_PROGRESS},
        ComplaintStatus.IN_PROGRESS: {ComplaintStatus.RESOLVED},
        ComplaintStatus.RESOLVED: {ComplaintStatus.CLOSED, ComplaintStatus.OPEN},
        ComplaintStatus.CLOSED: {ComplaintStatus.OPEN},
    }'''

new = '''    allowed_transitions = {
        ComplaintStatus.OPEN: {
            ComplaintStatus.ASSIGNED,
            ComplaintStatus.IN_PROGRESS,
        },
        ComplaintStatus.ASSIGNED: {
            ComplaintStatus.IN_PROGRESS,
            ComplaintStatus.OPEN,
        },
        ComplaintStatus.IN_PROGRESS: {
            ComplaintStatus.WAITING_FOR_CUSTOMER,
            ComplaintStatus.RESOLVED,
        },
        ComplaintStatus.WAITING_FOR_CUSTOMER: {
            ComplaintStatus.IN_PROGRESS,
            ComplaintStatus.REOPENED,
        },
        ComplaintStatus.RESOLVED: {
            ComplaintStatus.CLOSED,
            ComplaintStatus.REOPENED,
        },
        ComplaintStatus.CLOSED: {
            ComplaintStatus.REOPENED,
        },
        ComplaintStatus.REOPENED: {
            ComplaintStatus.ASSIGNED,
            ComplaintStatus.IN_PROGRESS,
        },
    }'''

if old not in content:
    raise SystemExit(
        "ERROR: The expected transition block was not found. "
        "No file changes were made."
    )

path.write_text(content.replace(old, new, 1), encoding="utf-8")
print("Complaint status transitions updated successfully.")

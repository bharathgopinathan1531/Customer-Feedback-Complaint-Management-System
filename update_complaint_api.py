from pathlib import Path

path = Path("app/api/complaints.py")
content = path.read_text(encoding="utf-8")

old_create = '''        subject=payload.subject,
        description=payload.description,
        priority=payload.priority,
    )
    db.add(complaint)
    db.commit()'''

new_create = '''        subject=payload.subject,
        description=payload.description,
        priority=payload.priority,
        attachment_urls=payload.attachment_urls,
    )
    db.add(complaint)
    db.flush()
    complaint.reference_number = f"CMP-{complaint.id:06d}"
    db.commit()'''

if old_create in content:
    content = content.replace(old_create, new_create, 1)
elif "complaint.reference_number = f\"CMP-{complaint.id:06d}\"" not in content:
    raise SystemExit("Complaint creation block not found. No changes saved.")

old_transitions = '''    allowed_transitions = {
        ComplaintStatus.OPEN: {ComplaintStatus.IN_PROGRESS},
        ComplaintStatus.IN_PROGRESS: {ComplaintStatus.RESOLVED},
        ComplaintStatus.RESOLVED: {
            ComplaintStatus.CLOSED,
            ComplaintStatus.OPEN,
        },
        ComplaintStatus.CLOSED: {ComplaintStatus.OPEN},
    }'''

new_transitions = '''    allowed_transitions = {
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
        ComplaintStatus.CLOSED: {ComplaintStatus.REOPENED},
        ComplaintStatus.REOPENED: {
            ComplaintStatus.ASSIGNED,
            ComplaintStatus.IN_PROGRESS,
        },
    }'''

if old_transitions in content:
    content = content.replace(old_transitions, new_transitions, 1)
elif "ComplaintStatus.WAITING_FOR_CUSTOMER: {" not in content:
    raise SystemExit("Status transition block not found. No changes saved.")

path.write_text(content, encoding="utf-8")
print("Complaint API updated.")

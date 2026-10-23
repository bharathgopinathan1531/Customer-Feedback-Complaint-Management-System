from pathlib import Path
import shutil

path = Path("app/api/complaints.py")
content = path.read_text(encoding="utf-8")

backup = Path("app/api/complaints.py.notifications.bak")

if "from app.models.notification import Notification" not in content:
    marker = "from app.models.customer import Customer"
    if marker not in content:
        raise SystemExit("Could not find Customer model import. No changes made.")
    content = content.replace(
        marker,
        marker + "\nfrom app.models.notification import Notification",
        1,
    )

status_marker = """    db.add(history)

    try:
        db.commit()"""

status_replacement = """    db.add(history)

    # Notify the customer in the same transaction as the status change.
    customer = (
        db.query(Customer)
        .filter(Customer.id == complaint.customer_id)
        .first()
    )
    if customer is not None:
        reference = complaint.reference_number or f"#{complaint.id}"
        db.add(
            Notification(
                user_id=customer.user_id,
                title=f"Complaint {reference} status updated",
                message=(
                    f"Your complaint status changed to "
                    f"{payload.status.value.replace('_', ' ')}."
                ),
                notification_type="complaint_status",
            )
        )

    try:
        db.commit()"""

assignment_marker = """    complaint.assigned_to_user_id = staff_member.id
    db.commit()
    db.refresh(complaint)
    return complaint"""

assignment_replacement = """    previous_assignee_id = complaint.assigned_to_user_id
    complaint.assigned_to_user_id = staff_member.id

    # Notify the newly assigned agent or manager.
    if previous_assignee_id != staff_member.id:
        reference = complaint.reference_number or f"#{complaint.id}"
        db.add(
            Notification(
                user_id=staff_member.id,
                title=f"Complaint {reference} assigned to you",
                message=f"You have been assigned complaint: {complaint.subject}",
                notification_type="complaint_assigned",
            )
        )

    try:
        db.commit()
        db.refresh(complaint)
    except Exception:
        db.rollback()
        raise

    return complaint"""

if "# Notify the customer in the same transaction as the status change." not in content:
    if status_marker not in content:
        raise SystemExit("Status update insertion point not found. No changes made.")
    content = content.replace(status_marker, status_replacement, 1)

if "# Notify the newly assigned agent or manager." not in content:
    if assignment_marker not in content:
        raise SystemExit("Assignment insertion point not found. No changes made.")
    content = content.replace(assignment_marker, assignment_replacement, 1)

if not backup.exists():
    shutil.copy2(path, backup)

path.write_text(content, encoding="utf-8")
print("Automatic complaint notifications added.")
print(f"Backup: {backup}")

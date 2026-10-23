from pathlib import Path

path = Path("app/api/complaints.py")
text = path.read_text(encoding="utf-8")

if "from app.models.audit_log import AuditLog" not in text:
    marker = "from app.models.complaint_status_history import ComplaintStatusHistory"
    if marker not in text:
        raise SystemExit("STOP: Could not find complaint history import.")
    text = text.replace(
        marker,
        marker + "\nfrom app.models.audit_log import AuditLog",
        1,
    )

replacements = [
    (
        '    complaint.reference_number = f"CMP-{complaint.id:06d}"\n    db.commit()',
        '''    complaint.reference_number = f"CMP-{complaint.id:06d}"
    db.add(
        AuditLog(
            user_id=current_user.id,
            action="COMPLAINT_CREATED",
            resource_type="complaint",
            resource_id=str(complaint.id),
            details={"reference_number": complaint.reference_number},
        )
    )
    db.commit()''',
        "complaint creation",
    ),
    (
        '''    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(complaint, field, value)

    db.commit()''',
        '''    changed_fields = payload.model_dump(exclude_unset=True)
    for field, value in changed_fields.items():
        setattr(complaint, field, value)

    db.add(
        AuditLog(
            user_id=current_user.id,
            action="COMPLAINT_UPDATED",
            resource_type="complaint",
            resource_id=str(complaint.id),
            details={"updated_fields": list(changed_fields.keys())},
        )
    )
    db.commit()''',
        "complaint update",
    ),
    (
        '''    db.add(history)

    # Notify the customer in the same transaction as the status change.''',
        '''    db.add(history)
    db.add(
        AuditLog(
            user_id=current_user.id,
            action="COMPLAINT_STATUS_CHANGED",
            resource_type="complaint",
            resource_id=str(complaint.id),
            details={
                "old_status": old_status.value,
                "new_status": payload.status.value,
            },
        )
    )

    # Notify the customer in the same transaction as the status change.''',
        "complaint status change",
    ),
    (
        '''    previous_assignee_id = complaint.assigned_to_user_id
    complaint.assigned_to_user_id = staff_member.id

    # Notify the newly assigned agent or manager.''',
        '''    previous_assignee_id = complaint.assigned_to_user_id
    complaint.assigned_to_user_id = staff_member.id

    db.add(
        AuditLog(
            user_id=current_user.id,
            action="COMPLAINT_ASSIGNED",
            resource_type="complaint",
            resource_id=str(complaint.id),
            details={
                "previous_assignee_id": previous_assignee_id,
                "assigned_to_user_id": staff_member.id,
            },
        )
    )

    # Notify the newly assigned agent or manager.''',
        "complaint assignment",
    ),
]

for old, new, label in replacements:
    if new in text:
        print(f"Already present: {label}")
        continue
    if old not in text:
        raise SystemExit(f"STOP: Could not find expected code for {label}. No further edits made.")
    text = text.replace(old, new, 1)
    print(f"Added audit logging: {label}")

path.write_text(text, encoding="utf-8")
print("Complaint audit logging updated.")

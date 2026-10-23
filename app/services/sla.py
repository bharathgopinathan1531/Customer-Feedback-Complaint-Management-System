from datetime import datetime, timedelta, timezone

from app.models.complaint import Complaint, ComplaintPriority, ComplaintStatus


SLA_HOURS = {
    ComplaintPriority.URGENT: 4,
    ComplaintPriority.HIGH: 8,
    ComplaintPriority.MEDIUM: 24,
    ComplaintPriority.LOW: 72,
}


def get_sla_deadline(complaint: Complaint) -> datetime:
    created_at = complaint.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)

    return created_at + timedelta(hours=SLA_HOURS[complaint.priority])


def get_sla_status(
    complaint: Complaint,
    now: datetime | None = None,
) -> dict:
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    deadline = get_sla_deadline(complaint)

    is_finished = complaint.status in {
        ComplaintStatus.RESOLVED,
        ComplaintStatus.CLOSED,
    }

    overdue = not is_finished and now > deadline

    return {
        "complaint_id": complaint.id,
        "reference_number": complaint.reference_number,
        "priority": complaint.priority.value,
        "status": complaint.status.value,
        "sla_deadline": deadline,
        "is_overdue": overdue,
        "hours_remaining": (
            0.0 if is_finished else round((deadline - now).total_seconds() / 3600, 2)
        ),
    }

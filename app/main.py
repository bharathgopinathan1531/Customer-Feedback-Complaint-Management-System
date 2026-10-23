from fastapi import FastAPI

from app.api.audit_logs import router as audit_logs_router
from app.api.auth import router as auth_router
from app.api.admin import router as admin_router
from app.api.customers import router as customers_router
from app.api.feedback import router as feedback_router
from app.api.categories import router as categories_router
from app.api.complaints import router as complaints_router
from app.api.complaint_comments import router as complaint_comments_router
from app.api.sla import router as sla_router
from app.api.notifications import router as notifications_router
from app.api.analytics import router as analytics_router
from app.api.dashboard import dashboard_router, reports_router
from app.core.config import settings
from app.db.session import Base, engine
from app.models import User, Customer, Feedback, Category, Complaint, RefreshToken, PasswordResetToken

from app.models.complaint_comment import ComplaintComment
from app.models.notification import Notification
from app.models.complaint_status_history import ComplaintStatusHistory
from app.models.audit_log import AuditLog

# Temporary development table creation; Alembic migrations will replace this.
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Customer feedback and complaint management API",
)

app.include_router(audit_logs_router)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(customers_router)
app.include_router(feedback_router)
app.include_router(categories_router)
app.include_router(complaints_router)
app.include_router(complaint_comments_router)
app.include_router(sla_router)
app.include_router(notifications_router)
app.include_router(analytics_router)
app.include_router(reports_router)
app.include_router(dashboard_router)


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy"}
from app.models.complaint_status_history import ComplaintStatusHistory


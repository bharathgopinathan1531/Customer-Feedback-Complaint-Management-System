from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.session import Base


class ComplaintComment(Base):
    __tablename__ = "complaint_comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    complaint_id: Mapped[int] = mapped_column(
        ForeignKey("complaints.id"), nullable=False, index=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )

    comment: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

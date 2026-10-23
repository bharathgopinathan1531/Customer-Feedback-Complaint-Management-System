from pathlib import Path

path = Path("app/api/complaints.py")
text = path.read_text(encoding="utf-8")

duplicate_start = text.find(
    '@router.get("", response_model=list[ComplaintResponse])',
    text.find('@router.get("", response_model=list[ComplaintResponse])') + 1,
)

if duplicate_start == -1:
    raise SystemExit("Duplicate list_complaints route not found; no changes made.")

duplicate_end = text.find(
    '@router.get("/{complaint_id}", response_model=ComplaintResponse)',
    duplicate_start,
)

if duplicate_end == -1:
    raise SystemExit("Complaint detail route not found; no changes made.")

text = text[:duplicate_start] + text[duplicate_end:]

my_route = '''
@router.get("/me", response_model=list[ComplaintResponse])
def get_my_complaints(
    complaint_status: ComplaintStatus | None = Query(default=None, alias="status"),
    category_id: int | None = Query(default=None, gt=0),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.CUSTOMER)),
):
    customer = (
        db.query(Customer)
        .filter(Customer.user_id == current_user.id)
        .first()
    )
    if customer is None:
        return []

    query = db.query(Complaint).filter(Complaint.customer_id == customer.id)

    if complaint_status is not None:
        query = query.filter(Complaint.status == complaint_status)

    if category_id is not None:
        query = query.filter(Complaint.category_id == category_id)

    return (
        query.order_by(Complaint.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


'''

insert_before = '@router.get("", response_model=list[ComplaintResponse])'
position = text.find(insert_before)

if position == -1:
    raise SystemExit("Staff complaint list route not found; no changes made.")

text = text[:position] + my_route + text[position:]
path.write_text(text, encoding="utf-8")
print("Restored /complaints/me and removed the duplicate list route.")

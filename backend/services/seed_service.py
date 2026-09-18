from backend.database import db
from backend.models import User

def seed_bank_user():
    """
    Ensure a default bank analyst user exists for development and demo purposes.
    Credentials:
      Email: bank@trustguard.ai
      Password: Bank@123
      Role: BANK
    """
    bank_email = "bank@trustguard.ai"
    existing = User.query.filter_by(email=bank_email).first()
    if not existing:
        bank_user = User(
            name="Bank Analyst",
            email=bank_email,
            role="BANK"
        )
        bank_user.set_password("Bank@123")
        db.session.add(bank_user)
        db.session.commit()
        print(f"[Seed] Created demo bank user: {bank_email} (Role: BANK)")
    else:
        # Ensure role is BANK
        if existing.role != "BANK":
            existing.role = "BANK"
            db.session.commit()

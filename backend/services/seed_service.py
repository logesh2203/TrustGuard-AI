from backend.database import db
from backend.models import User, CustomerTransaction
from backend.services.dataset_service import DatasetService

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

def seed_demo_customer():
    """
    Ensure a default demo customer user exists for development and demo purposes.
    Credentials:
      Email: customer@trustguard.ai
      Password: Customer@123
      Role: CUSTOMER
    """
    cust_email = "customer@trustguard.ai"
    existing = User.query.filter_by(email=cust_email).first()
    if not existing:
        cust_user = User(
            name="Demo Customer",
            email=cust_email,
            role="CUSTOMER"
        )
        cust_user.set_password("Customer@123")
        db.session.add(cust_user)
        db.session.flush()

        # Sample transactions for customer
        sample_txs = DatasetService.get_sample_transactions_for_user(normal_count=12, fraud_count=3)
        for tx in sample_txs:
            ct = CustomerTransaction(
                user_id=cust_user.id,
                dataset_row_id=tx['dataset_row_id'],
                amount=tx['amount'],
                transaction_time=tx['transaction_time'],
                class_label=tx['class_label']
            )
            db.session.add(ct)

        db.session.commit()
        print(f"[Seed] Created demo customer: {cust_email} (Role: CUSTOMER)")
    else:
        if existing.role != "CUSTOMER":
            existing.role = "CUSTOMER"
            db.session.commit()


from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from backend.database import db

def utc_now():
    return datetime.now(timezone.utc)

class User(db.Model):
    """User model for customer accounts."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default='CUSTOMER', nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)

    # Relationship to transactions
    transactions = db.relationship('CustomerTransaction', backref='user', lazy=True, cascade="all, delete-orphan")

    def set_password(self, password: str):
        """Hash and store the password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verify the password against the stored hash."""
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        """Serialize user model to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'role': self.role,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }

def compute_risk_level(class_label: int, amount: float, case_priority: str = None, case_status: str = None) -> str:
    """
    Deterministic risk badge classification based strictly on existing transaction ground truth,
    amount threshold, and investigation records (no AI risk scores).
    """
    if class_label == 1 or case_priority in ('HIGH', 'CRITICAL'):
        return 'HIGH'
    if class_label == 0 and (amount >= 500 or case_status in ('OPEN', 'UNDER_REVIEW') or case_priority == 'MEDIUM'):
        return 'MEDIUM'
    return 'LOW'


class CustomerTransaction(db.Model):
    """Customer transaction model linked to original dataset rows."""
    __tablename__ = 'customer_transactions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    dataset_row_id = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    transaction_time = db.Column(db.Float, nullable=False)
    class_label = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)

    def to_dict(self, case=None):
        """Serialize transaction model to dictionary with dynamic status and risk level."""
        status = 'Normal' if self.class_label == 0 else 'Fraud-Labeled'
        if case:
            if case.status == 'RESOLVED':
                status = 'Resolved'
            elif case.status == 'UNDER_REVIEW':
                status = 'Under Review'
            elif case.status == 'OPEN':
                status = 'Reported'

        risk = compute_risk_level(
            self.class_label,
            self.amount,
            case_priority=case.priority if case else None,
            case_status=case.status if case else None
        )

        return {
            'id': self.id,
            'user_id': self.user_id,
            'dataset_row_id': self.dataset_row_id,
            'amount': round(self.amount, 2),
            'transaction_time': self.transaction_time,
            'class_label': self.class_label,
            'status': status,
            'risk_level': risk,
            'case_id': case.id if case else None,
            'is_reported': True if (case and case.status in ('OPEN', 'UNDER_REVIEW')) else False,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }


class FraudCase(db.Model):
    """Fraud review case model for bank analysts."""
    __tablename__ = 'fraud_cases'

    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, nullable=False, index=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), default='OPEN', nullable=False)  # OPEN, UNDER_REVIEW, RESOLVED
    priority = db.Column(db.String(20), default='MEDIUM', nullable=False)  # LOW, MEDIUM, HIGH, CRITICAL
    notes = db.Column(db.Text, nullable=True)
    resolution = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Creator relationship
    creator = db.relationship('User', backref=db.backref('created_cases', lazy=True))

    def get_timeline(self):
        """Generate structured timeline milestones for the case."""
        is_cust = bool(self.creator and self.creator.role == 'CUSTOMER')
        events = [
            {
                'event_type': 'REPORTED' if is_cust else 'CREATED',
                'title': 'Suspicious Activity Reported by Customer' if is_cust else 'Fraud Review Case Opened',
                'actor': self.creator.name if self.creator else 'Bank Analyst',
                'actor_role': self.creator.role if self.creator else 'BANK',
                'timestamp': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
                'status': 'OPEN',
                'priority': self.priority,
                'description': self.notes or ('Customer flagged this transaction as suspicious.' if is_cust else 'Case initiated by analyst.')
            }
        ]

        if self.status in ('UNDER_REVIEW', 'RESOLVED'):
            events.append({
                'event_type': 'INVESTIGATION',
                'title': 'Investigation Under Review',
                'actor': 'Bank Fraud Operations',
                'actor_role': 'BANK',
                'timestamp': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'UNDER_REVIEW',
                'priority': self.priority,
                'description': 'Analyst actively inspecting transaction features, amounts, and account profile.'
            })

        if self.status == 'RESOLVED':
            events.append({
                'event_type': 'RESOLVED',
                'title': 'Case Resolved & Decision Recorded',
                'actor': 'Bank Fraud Operations',
                'actor_role': 'BANK',
                'timestamp': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None,
                'status': 'RESOLVED',
                'priority': self.priority,
                'description': self.resolution or 'Case determination finalized and closed.'
            })

        return events

    def to_dict(self):
        """Serialize fraud case to dictionary with timeline and creator metadata."""
        is_cust = bool(self.creator and self.creator.role == 'CUSTOMER')
        return {
            'id': self.id,
            'transaction_id': self.transaction_id,
            'created_by': self.created_by,
            'creator_name': self.creator.name if self.creator else 'Bank Analyst',
            'creator_role': self.creator.role if self.creator else 'BANK',
            'is_customer_reported': is_cust,
            'status': self.status,
            'priority': self.priority,
            'notes': self.notes or '',
            'resolution': self.resolution or '',
            'timeline': self.get_timeline(),
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None
        }


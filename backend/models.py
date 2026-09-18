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

    def to_dict(self):
        """Serialize transaction model to dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'dataset_row_id': self.dataset_row_id,
            'amount': round(self.amount, 2),
            'transaction_time': self.transaction_time,
            'class_label': self.class_label,
            'status': 'Normal' if self.class_label == 0 else 'Fraud',
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }


class FraudCase(db.Model):
    """Fraud review case model for bank analysts."""
    __tablename__ = 'fraud_cases'

    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, nullable=False, index=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), default='OPEN', nullable=False)  # OPEN, UNDER_REVIEW, RESOLVED
    priority = db.Column(db.String(20), default='MEDIUM', nullable=False)  # LOW, MEDIUM, HIGH
    notes = db.Column(db.Text, nullable=True)
    resolution = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Creator relationship
    creator = db.relationship('User', backref=db.backref('created_cases', lazy=True))

    def to_dict(self):
        """Serialize fraud case to dictionary."""
        return {
            'id': self.id,
            'transaction_id': self.transaction_id,
            'created_by': self.created_by,
            'creator_name': self.creator.name if self.creator else 'Bank Analyst',
            'status': self.status,
            'priority': self.priority,
            'notes': self.notes or '',
            'resolution': self.resolution or '',
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None
        }


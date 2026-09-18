import re
from functools import wraps
from flask import Blueprint, request, jsonify, session, render_template, redirect, url_for
from backend.database import db
from backend.models import User, CustomerTransaction
from backend.services.dataset_service import DatasetService

customer_bp = Blueprint('customer', __name__)

def login_required(f):
    """Decorator to require customer session authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Authentication required. Please log in.'}), 401
            return redirect(url_for('customer.login_page'))
        return f(*args, **kwargs)
    return decorated_function


# ============================================================================
# PAGE ROUTES
# ============================================================================

@customer_bp.route('/')
def index():
    """Root route redirecting to dashboard or login."""
    if 'user_id' in session:
        return redirect(url_for('customer.dashboard_page'))
    return redirect(url_for('customer.login_page'))


@customer_bp.route('/customer/register', methods=['GET'])
def register_page():
    """Render customer registration page."""
    if 'user_id' in session:
        return redirect(url_for('customer.dashboard_page'))
    return render_template('customer_register.html')


@customer_bp.route('/customer/login', methods=['GET'])
def login_page():
    """Render customer login page."""
    if 'user_id' in session:
        return redirect(url_for('customer.dashboard_page'))
    return render_template('customer_login.html')


@customer_bp.route('/customer/dashboard', methods=['GET'])
@login_required
def dashboard_page():
    """Render customer dashboard page."""
    return render_template('customer_dashboard.html', user_name=session.get('user_name', 'Customer'))


@customer_bp.route('/customer/logout', methods=['GET'])
def logout_page():
    """Handle customer logout and redirect to login."""
    session.clear()
    return redirect(url_for('customer.login_page'))


# ============================================================================
# REST API ENDPOINTS
# ============================================================================

@customer_bp.route('/api/customer/register', methods=['POST'])
def api_register():
    """Handle customer registration."""
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    confirm_password = data.get('confirm_password', '')

    # Validation
    if not name or not email or not password or not confirm_password:
        return jsonify({'error': 'All fields are required.'}), 400

    email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    if not re.match(email_regex, email):
        return jsonify({'error': 'Please provide a valid email address.'}), 400

    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters long.'}), 400

    if password != confirm_password:
        return jsonify({'error': 'Password and Confirm Password do not match.'}), 400

    # Check if email is unique
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return jsonify({'error': 'An account with this email address already exists.'}), 409

    try:
        # Create user
        user = User(name=name, email=email, role='CUSTOMER')
        user.set_password(password)
        db.session.add(user)
        db.session.flush()  # Obtain user.id

        # Assign sampled transactions from creditcard.csv to this customer
        sample_txs = DatasetService.get_sample_transactions_for_user(normal_count=12, fraud_count=3)
        for tx in sample_txs:
            ct = CustomerTransaction(
                user_id=user.id,
                dataset_row_id=tx['dataset_row_id'],
                amount=tx['amount'],
                transaction_time=tx['transaction_time'],
                class_label=tx['class_label']
            )
            db.session.add(ct)

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Registration successful! You can now log in.',
            'redirect': url_for('customer.login_page')
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Registration failed: {str(e)}'}), 500


@customer_bp.route('/api/customer/login', methods=['POST'])
def api_login():
    """Handle customer login."""
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({'error': 'Email and password are required.'}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid email or password.'}), 401

    # Store user in session
    session['user_id'] = user.id
    session['user_name'] = user.name
    session['user_email'] = user.email
    session['user_role'] = user.role

    return jsonify({
        'success': True,
        'message': 'Login successful!',
        'redirect': url_for('customer.dashboard_page'),
        'user': user.to_dict()
    }), 200


@customer_bp.route('/api/customer/logout', methods=['POST'])
def api_logout():
    """Handle customer logout via API."""
    session.clear()
    return jsonify({
        'success': True,
        'message': 'Logged out successfully.',
        'redirect': url_for('customer.login_page')
    }), 200


@customer_bp.route('/api/customer/dashboard', methods=['GET'])
@login_required
def api_dashboard():
    """Return dashboard summary metrics and recent transactions for logged-in user."""
    user_id = session['user_id']

    transactions = CustomerTransaction.query.filter_by(user_id=user_id).order_by(CustomerTransaction.id.desc()).all()

    total_count = len(transactions)
    normal_count = sum(1 for tx in transactions if tx.class_label == 0)
    fraud_count = sum(1 for tx in transactions if tx.class_label == 1)
    attention_count = fraud_count  # Class 1 transactions requiring attention

    recent_transactions = [tx.to_dict() for tx in transactions[:5]]

    return jsonify({
        'user': {
            'id': user_id,
            'name': session.get('user_name'),
            'email': session.get('user_email')
        },
        'total_transactions': total_count,
        'normal_transactions': normal_count,
        'fraud_transactions': fraud_count,
        'attention_transactions': attention_count,
        'recent_transactions': recent_transactions
    }), 200

from functools import wraps
from flask import Blueprint, request, jsonify, session, render_template, redirect, url_for
from backend.database import db
from backend.models import User, FraudCase
from backend.services.dataset_service import DatasetService

bank_bp = Blueprint('bank', __name__)

def bank_required(f):
    """Decorator to require authenticated BANK user session."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Authentication required. Please log in as bank staff.'}), 401
            return redirect(url_for('bank.login_page'))

        if session.get('user_role') != 'BANK':
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Access forbidden. Bank staff role required.'}), 403
            return render_template('base.html', error_message="Access Denied: Bank Analyst role required to access this portal."), 403

        return f(*args, **kwargs)
    return decorated_function


# ============================================================================
# BANK PAGE ROUTES
# ============================================================================

@bank_bp.route('/bank/login', methods=['GET'])
def login_page():
    """Render bank login page."""
    if 'user_id' in session and session.get('user_role') == 'BANK':
        return redirect(url_for('bank.dashboard_page'))
    return render_template('bank_login.html')


@bank_bp.route('/bank/logout', methods=['GET'])
def logout_page():
    """Handle bank logout and redirect."""
    session.clear()
    return redirect(url_for('bank.login_page'))


@bank_bp.route('/bank/dashboard', methods=['GET'])
@bank_required
def dashboard_page():
    """Render bank dashboard."""
    return render_template('bank_dashboard.html')


@bank_bp.route('/bank/transactions', methods=['GET'])
@bank_required
def transactions_page():
    """Render bank dataset transactions browser."""
    return render_template('bank_transactions.html')


@bank_bp.route('/bank/transactions/<int:row_id>', methods=['GET'])
@bank_required
def transaction_details_page(row_id):
    """Render bank transaction details page."""
    return render_template('bank_tx_details.html', row_id=row_id)


@bank_bp.route('/bank/cases', methods=['GET'])
@bank_required
def cases_page():
    """Render fraud review cases list."""
    return render_template('bank_cases.html')


@bank_bp.route('/bank/cases/<int:case_id>', methods=['GET'])
@bank_required
def case_details_page(case_id):
    """Render single case details and editor."""
    case = db.session.get(FraudCase, case_id)
    if not case:
        return render_template('bank_case_details.html', error="Review Case not found.", case_id=case_id), 404
    return render_template('bank_case_details.html', case_id=case_id)


@bank_bp.route('/bank/customers', methods=['GET'])
@bank_required
def customers_page():
    """Render bank customers list."""
    return render_template('bank_customers.html')


@bank_bp.route('/bank/analytics', methods=['GET'])
@bank_required
def analytics_page():
    """Render basic bank distribution analytics."""
    return render_template('bank_analytics.html')


# ============================================================================
# BANK REST API ENDPOINTS
# ============================================================================

@bank_bp.route('/api/bank/login', methods=['POST'])
def api_bank_login():
    """Authenticate bank analyst."""
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({'error': 'Email and password are required.'}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid email or password.'}), 401

    if user.role != 'BANK':
        return jsonify({'error': 'Access denied: User account is not assigned the BANK role.'}), 403

    # Set session
    session['user_id'] = user.id
    session['user_name'] = user.name
    session['user_email'] = user.email
    session['user_role'] = user.role

    return jsonify({
        'success': True,
        'message': 'Bank Analyst authenticated successfully.',
        'redirect': url_for('bank.dashboard_page'),
        'user': user.to_dict()
    }), 200


@bank_bp.route('/api/bank/logout', methods=['POST'])
def api_bank_logout():
    """Logout bank analyst."""
    session.clear()
    return jsonify({
        'success': True,
        'message': 'Logged out successfully.',
        'redirect': url_for('bank.login_page')
    }), 200


@bank_bp.route('/api/bank/dashboard', methods=['GET'])
@bank_required
def api_dashboard():
    """Return summary statistics and recent dataset activity for bank dashboard."""
    try:
        stats = DatasetService.get_dataset_summary_stats()
        customer_count = User.query.filter_by(role='CUSTOMER').count()
        open_cases_count = FraudCase.query.filter(FraudCase.status.in_(['OPEN', 'UNDER_REVIEW'])).count()
        recent_txs = DatasetService.get_recent_dataset_transactions(limit=5)

        return jsonify({
            'total_transactions': stats['total_transactions'],
            'normal_transactions': stats['normal_transactions'],
            'fraud_transactions': stats['fraud_transactions'],
            'customer_count': customer_count,
            'open_cases': open_cases_count,
            'recent_transactions': recent_txs
        }), 200
    except Exception as e:
        return jsonify({'error': f'Failed to load bank dashboard: {str(e)}'}), 500


@bank_bp.route('/api/bank/transactions', methods=['GET'])
@bank_required
def api_get_transactions():
    """Return paginated dataset transactions for bank staff."""
    try:
        page = max(1, int(request.args.get('page', 1)))
        per_page = min(100, max(1, int(request.args.get('limit', request.args.get('per_page', 20)))))
        status = request.args.get('status', 'all').strip().lower()
        search_q = request.args.get('q', request.args.get('search', '')).strip()

        data = DatasetService.get_paginated_dataset_transactions(
            page=page,
            per_page=per_page,
            status=status,
            search_id=search_q if search_q else None
        )
        return jsonify(data), 200
    except Exception as e:
        return jsonify({'error': f'Failed to retrieve dataset transactions: {str(e)}'}), 500


@bank_bp.route('/api/bank/transactions/<int:row_id>', methods=['GET'])
@bank_required
def api_get_transaction_details(row_id):
    """Return full transaction details and existing review case status."""
    try:
        features_data = DatasetService.get_transaction_features(row_id)
        if not features_data:
            return jsonify({'error': f'Transaction index #{row_id} not found in dataset.'}), 404

        # Check if an existing review case exists for this transaction
        existing_case = FraudCase.query.filter_by(transaction_id=row_id).first()

        features_data['existing_case'] = existing_case.to_dict() if existing_case else None
        features_data['dataset_info'] = (
            "V1-V28 are anonymized transaction features provided by the dataset. "
            "Their original real-world meanings are not available in the dataset."
        )

        return jsonify(features_data), 200
    except Exception as e:
        return jsonify({'error': f'Error loading transaction details: {str(e)}'}), 500


@bank_bp.route('/api/bank/customers', methods=['GET'])
@bank_required
def api_get_customers():
    """Return sanitized list of registered customer accounts (no passwords)."""
    try:
        customers = User.query.filter_by(role='CUSTOMER').order_by(User.id.desc()).all()
        return jsonify({
            'customers': [{
                'id': c.id,
                'name': c.name,
                'email': c.email,
                'created_at': c.created_at.strftime('%Y-%m-%d %H:%M:%S') if c.created_at else None
            } for c in customers],
            'total': len(customers)
        }), 200
    except Exception as e:
        return jsonify({'error': f'Failed to fetch customers: {str(e)}'}), 500


@bank_bp.route('/api/bank/cases', methods=['GET'])
@bank_required
def api_get_cases():
    """Return list of fraud review cases with optional status filter."""
    try:
        status_filter = request.args.get('status', 'ALL').strip().upper()
        query = FraudCase.query

        if status_filter in ('OPEN', 'UNDER_REVIEW', 'RESOLVED'):
            query = query.filter_by(status=status_filter)

        cases = query.order_by(FraudCase.id.desc()).all()
        return jsonify({
            'cases': [c.to_dict() for c in cases],
            'total': len(cases)
        }), 200
    except Exception as e:
        return jsonify({'error': f'Failed to load fraud cases: {str(e)}'}), 500


@bank_bp.route('/api/bank/cases', methods=['POST'])
@bank_required
def api_create_case():
    """Create a new fraud review case for a transaction."""
    data = request.get_json() or {}
    try:
        transaction_id = int(data.get('transaction_id'))
    except (TypeError, ValueError):
        return jsonify({'error': 'Valid transaction ID is required.'}), 400

    priority = data.get('priority', 'MEDIUM').strip().upper()
    if priority not in ('LOW', 'MEDIUM', 'HIGH'):
        priority = 'MEDIUM'

    notes = data.get('notes', '').strip()

    # Verify transaction exists in dataset
    tx_features = DatasetService.get_transaction_features(transaction_id)
    if not tx_features:
        return jsonify({'error': f'Transaction #{transaction_id} does not exist in the dataset.'}), 404

    # Check if case already exists
    existing = FraudCase.query.filter_by(transaction_id=transaction_id).first()
    if existing:
        return jsonify({
            'error': f'A review case already exists for transaction #{transaction_id}.',
            'case': existing.to_dict()
        }), 409

    try:
        new_case = FraudCase(
            transaction_id=transaction_id,
            created_by=session['user_id'],
            status='OPEN',
            priority=priority,
            notes=notes if notes else f"Case opened for transaction #{transaction_id} (Dataset Label: {tx_features['status']}).",
            resolution=''
        )
        db.session.add(new_case)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Review case created successfully.',
            'case': new_case.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to create review case: {str(e)}'}), 500


@bank_bp.route('/api/bank/cases/<int:case_id>', methods=['GET'])
@bank_required
def api_get_case_details(case_id):
    """Retrieve full details of a specific fraud case and attached transaction."""
    case = db.session.get(FraudCase, case_id)
    if not case:
        return jsonify({'error': 'Review Case not found.'}), 404

    # Attach transaction summary
    tx_features = DatasetService.get_transaction_features(case.transaction_id)
    case_dict = case.to_dict()
    case_dict['transaction'] = tx_features

    return jsonify(case_dict), 200


@bank_bp.route('/api/bank/cases/<int:case_id>', methods=['PUT'])
@bank_required
def api_update_case(case_id):
    """Update status, priority, notes, and resolution for a fraud case."""
    case = db.session.get(FraudCase, case_id)
    if not case:
        return jsonify({'error': 'Review Case not found.'}), 404

    data = request.get_json() or {}

    status = data.get('status', case.status).strip().upper()
    if status not in ('OPEN', 'UNDER_REVIEW', 'RESOLVED'):
        return jsonify({'error': 'Invalid status. Allowed values: OPEN, UNDER_REVIEW, RESOLVED.'}), 400

    priority = data.get('priority', case.priority).strip().upper()
    if priority not in ('LOW', 'MEDIUM', 'HIGH'):
        return jsonify({'error': 'Invalid priority. Allowed values: LOW, MEDIUM, HIGH.'}), 400

    notes = data.get('notes', case.notes)
    resolution = data.get('resolution', case.resolution)

    try:
        case.status = status
        case.priority = priority
        case.notes = notes
        case.resolution = resolution
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Case updated successfully.',
            'case': case.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to update case: {str(e)}'}), 500


@bank_bp.route('/api/bank/analytics', methods=['GET'])
@bank_required
def api_analytics():
    """Return dataset distribution statistics for analytics chart."""
    try:
        stats = DatasetService.get_dataset_summary_stats()
        open_cases = FraudCase.query.filter_by(status='OPEN').count()
        under_review_cases = FraudCase.query.filter_by(status='UNDER_REVIEW').count()
        resolved_cases = FraudCase.query.filter_by(status='RESOLVED').count()

        return jsonify({
            'total_transactions': stats['total_transactions'],
            'normal_transactions': stats['normal_transactions'],
            'fraud_transactions': stats['fraud_transactions'],
            'fraud_percentage': stats['fraud_percentage'],
            'case_stats': {
                'open': open_cases,
                'under_review': under_review_cases,
                'resolved': resolved_cases,
                'total_cases': open_cases + under_review_cases + resolved_cases
            }
        }), 200
    except Exception as e:
        return jsonify({'error': f'Failed to load analytics: {str(e)}'}), 500

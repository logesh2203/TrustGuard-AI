from flask import Blueprint, request, jsonify, session, render_template, abort
from backend.database import db
from backend.models import CustomerTransaction, FraudCase
from backend.routes.customer import login_required
from backend.services.dataset_service import DatasetService

transactions_bp = Blueprint('transactions', __name__)

# ============================================================================
# PAGE ROUTES
# ============================================================================

@transactions_bp.route('/customer/transactions', methods=['GET'])
@login_required
def transactions_page():
    """Render transactions list page."""
    return render_template('transactions.html')


@transactions_bp.route('/customer/transactions/<int:tx_id>', methods=['GET'])
@login_required
def transaction_details_page(tx_id):
    """Render transaction details page."""
    user_id = session['user_id']
    tx = CustomerTransaction.query.filter_by(id=tx_id, user_id=user_id).first()
    if not tx:
        return render_template('transaction_details.html', error="Transaction not found or unauthorized.", tx_id=tx_id), 404
    return render_template('transaction_details.html', tx_id=tx_id)


# ============================================================================
# REST API ENDPOINTS
# ============================================================================

@transactions_bp.route('/api/customer/transactions', methods=['GET'])
@login_required
def api_get_transactions():
    """
    Get customer transactions with advanced search, status, amount range filters,
    and dynamic risk badge classification.
    """
    user_id = session['user_id']
    query = CustomerTransaction.query.filter_by(user_id=user_id)

    # Amount range filters
    min_amount = request.args.get('min_amount')
    max_amount = request.args.get('max_amount')
    if min_amount:
        try:
            query = query.filter(CustomerTransaction.amount >= float(min_amount))
        except ValueError:
            pass
    if max_amount:
        try:
            query = query.filter(CustomerTransaction.amount <= float(max_amount))
        except ValueError:
            pass

    # Status filter
    status_filter = request.args.get('status', 'all').strip().lower()
    if status_filter in ('0', 'normal'):
        query = query.filter_by(class_label=0)
    elif status_filter in ('1', 'fraud'):
        query = query.filter_by(class_label=1)
    elif status_filter in ('reported', 'under_review', 'resolved'):
        case_status_map = {
            'reported': 'OPEN',
            'under_review': 'UNDER_REVIEW',
            'resolved': 'RESOLVED'
        }
        target_status = case_status_map[status_filter]
        matching_cases = FraudCase.query.filter_by(status=target_status).all()
        matching_row_ids = [c.transaction_id for c in matching_cases]
        query = query.filter(CustomerTransaction.dataset_row_id.in_(matching_row_ids))

    # Search filter by Transaction ID or Amount
    search_q = request.args.get('q', '').strip()
    if search_q:
        if search_q.isdigit():
            query = query.filter((CustomerTransaction.id == int(search_q)) | (CustomerTransaction.dataset_row_id == int(search_q)))
        else:
            try:
                amt_val = float(search_q)
                query = query.filter(CustomerTransaction.amount == amt_val)
            except ValueError:
                pass

    # Order by ID descending (most recent first)
    query = query.order_by(CustomerTransaction.id.desc())

    # Pagination
    try:
        page = max(1, int(request.args.get('page', 1)))
        per_page = min(50, max(1, int(request.args.get('per_page', 10))))
    except ValueError:
        page = 1
        per_page = 10

    total_count = query.count()
    total_pages = max(1, (total_count + per_page - 1) // per_page)
    offset = (page - 1) * per_page
    paginated_records = query.offset(offset).limit(per_page).all()

    # Pre-fetch attached fraud cases to prevent N+1 queries
    row_ids = [tx.dataset_row_id for tx in paginated_records]
    cases = FraudCase.query.filter(FraudCase.transaction_id.in_(row_ids)).all() if row_ids else []
    cases_by_row = {c.transaction_id: c for c in cases}

    records = [tx.to_dict(case=cases_by_row.get(tx.dataset_row_id)) for tx in paginated_records]

    return jsonify({
        'transactions': records,
        'total': total_count,
        'page': page,
        'per_page': per_page,
        'total_pages': total_pages
    }), 200


@transactions_bp.route('/api/customer/transactions/<int:tx_id>', methods=['GET'])
@login_required
def api_get_transaction_details(tx_id):
    """
    Get detailed features for a specific customer transaction, including attached case
    investigation details, risk level, and reporting status.
    """
    user_id = session['user_id']
    tx = CustomerTransaction.query.filter_by(id=tx_id, user_id=user_id).first()

    if not tx:
        return jsonify({'error': 'Transaction not found or access denied.'}), 404

    # Fetch attached review case if exists
    case = FraudCase.query.filter_by(transaction_id=tx.dataset_row_id).first()

    # Fetch original feature details from dataset
    try:
        features_data = DatasetService.get_transaction_features(tx.dataset_row_id)
        if not features_data:
            features_data = {
                'dataset_row_id': tx.dataset_row_id,
                'time': tx.transaction_time,
                'amount': tx.amount,
                'class_label': tx.class_label,
                'status': 'Normal' if tx.class_label == 0 else 'Fraud',
                'features': {}
            }
    except Exception as e:
        return jsonify({'error': f'Failed to retrieve dataset features: {str(e)}'}), 500

    response_data = tx.to_dict(case=case)
    response_data['features'] = features_data.get('features', {})
    response_data['existing_case'] = case.to_dict() if case else None
    response_data['dataset_info'] = (
        "The transaction contains anonymized features used for machine-learning research. "
        "V1-V28 are anonymized transaction features."
    )

    return jsonify(response_data), 200


@transactions_bp.route('/api/customer/transactions/<int:tx_id>/report', methods=['POST'])
@login_required
def api_report_transaction(tx_id):
    """
    Allow a customer to report an existing transaction as suspicious,
    automatically opening a review case in the Bank Case Management system.
    """
    user_id = session['user_id']
    tx = CustomerTransaction.query.filter_by(id=tx_id, user_id=user_id).first()

    if not tx:
        return jsonify({'error': 'Transaction not found or unauthorized.'}), 404

    data = request.get_json() or {}
    reason = data.get('reason', '').strip()
    if not reason:
        reason = "Customer flagged transaction as unrecognized or suspicious."

    # Check if a case already exists
    existing = FraudCase.query.filter_by(transaction_id=tx.dataset_row_id).first()
    if existing:
        if existing.status == 'RESOLVED':
            return jsonify({'error': 'This transaction has already been reviewed and resolved by bank operations.'}), 400
        return jsonify({
            'success': False,
            'error': f'This transaction is already under review in Case #{existing.id}.',
            'status': 'Reported',
            'case': existing.to_dict(),
            'transaction': tx.to_dict(case=existing)
        }), 409

    try:
        new_case = FraudCase(
            transaction_id=tx.dataset_row_id,
            created_by=user_id,
            status='OPEN',
            priority='HIGH',
            notes=f"Customer Report ({session.get('user_name', 'Customer')}): {reason}",
            resolution=''
        )
        db.session.add(new_case)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Transaction successfully reported! A review case has been opened with Bank Operations.',
            'status': 'Reported',
            'case': new_case.to_dict(),
            'transaction': tx.to_dict(case=new_case)
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to submit report: {str(e)}'}), 500

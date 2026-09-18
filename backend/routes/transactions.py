from flask import Blueprint, request, jsonify, session, render_template, abort
from backend.models import CustomerTransaction
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
    Get customer transactions with optional search, status filter, and pagination.
    """
    user_id = session['user_id']
    query = CustomerTransaction.query.filter_by(user_id=user_id)

    # Status filter: 'all', '0' (Normal), '1' (Fraud)
    status_filter = request.args.get('status', 'all').strip().lower()
    if status_filter in ('0', 'normal'):
        query = query.filter_by(class_label=0)
    elif status_filter in ('1', 'fraud'):
        query = query.filter_by(class_label=1)

    # Search filter by Transaction ID or Amount
    search_q = request.args.get('q', '').strip()
    if search_q:
        # Check if search is numeric ID
        if search_q.isdigit():
            query = query.filter((CustomerTransaction.id == int(search_q)) | (CustomerTransaction.dataset_row_id == int(search_q)))
        else:
            try:
                amt_val = float(search_q)
                query = query.filter(CustomerTransaction.amount == amt_val)
            except ValueError:
                # If not numeric, search won't match ID or amount
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

    return jsonify({
        'transactions': [tx.to_dict() for tx in paginated_records],
        'total': total_count,
        'page': page,
        'per_page': per_page,
        'total_pages': total_pages
    }), 200


@transactions_bp.route('/api/customer/transactions/<int:tx_id>', methods=['GET'])
@login_required
def api_get_transaction_details(tx_id):
    """
    Get detailed features for a specific customer transaction.
    """
    user_id = session['user_id']
    tx = CustomerTransaction.query.filter_by(id=tx_id, user_id=user_id).first()

    if not tx:
        return jsonify({'error': 'Transaction not found or access denied.'}), 404

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

    response_data = tx.to_dict()
    response_data['features'] = features_data.get('features', {})
    response_data['dataset_info'] = (
        "The transaction contains anonymized features used for machine-learning research. "
        "V1-V28 are anonymized transaction features."
    )

    return jsonify(response_data), 200

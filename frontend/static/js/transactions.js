/**
 * TrustGuard AI - Transactions JS
 * Handles All Transactions List (Search, Filter, Pagination) and Transaction Details.
 */

// Helper to format currency
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 2
    }).format(amount);
}

// Helper to render status badge
function getStatusBadge(classLabel) {
    if (classLabel === 0) {
        return `<span class="badge-status-normal"><i class="bi bi-shield-check"></i> Normal</span>`;
    } else {
        return `<span class="badge-status-fraud"><i class="bi bi-shield-exclamation"></i> Fraud</span>`;
    }
}

/**
 * Initialize Transactions List Page
 */
function initTransactionsListPage() {
    let currentPage = 1;
    let currentPerPage = 10;
    let currentStatus = 'all';
    let currentQuery = '';

    const searchInput = document.getElementById('txSearchInput');
    const searchBtn = document.getElementById('txSearchBtn');
    const statusFilter = document.getElementById('txStatusFilter');
    const perPageSelect = document.getElementById('txPerPage');
    const refreshBtn = document.getElementById('txRefreshBtn');

    async function fetchTransactions() {
        const tbody = document.getElementById('transactionsTableBody');
        const paginationInfo = document.getElementById('paginationInfo');
        const paginationControls = document.getElementById('paginationControls');

        if (!tbody) return;

        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="text-center py-5 text-muted">
                    <div class="spinner-border spinner-border-sm text-primary me-2" role="status"></div>
                    Fetching transactions...
                </td>
            </tr>
        `;

        try {
            const queryParams = new URLSearchParams({
                page: currentPage,
                per_page: currentPerPage,
                status: currentStatus,
                q: currentQuery
            });

            const response = await fetch(`/api/customer/transactions?${queryParams.toString()}`, {
                method: 'GET',
                headers: { 'Accept': 'application/json' }
            });

            if (response.status === 401) {
                window.location.href = '/customer/login';
                return;
            }

            if (!response.ok) {
                throw new Error(`Failed to load transactions (Status: ${response.status})`);
            }

            const data = await response.json();
            const txList = data.transactions || [];

            if (txList.length === 0) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="6" class="text-center py-5 text-muted">
                            <i class="bi bi-search fs-3 d-block mb-2 text-secondary"></i>
                            No transactions matched your current search or filter criteria.
                        </td>
                    </tr>
                `;
                if (paginationInfo) paginationInfo.textContent = 'Showing 0 of 0 transactions';
                if (paginationControls) paginationControls.innerHTML = '';
                return;
            }

            let rowsHtml = '';
            txList.forEach(tx => {
                rowsHtml += `
                    <tr>
                        <td class="ps-3 fw-bold font-monospace text-dark">#TX-${tx.id}</td>
                        <td class="font-monospace text-muted small">Row #${tx.dataset_row_id}</td>
                        <td class="text-muted small">${tx.transaction_time}s</td>
                        <td class="fw-bold">${formatCurrency(tx.amount)}</td>
                        <td>${getStatusBadge(tx.class_label)}</td>
                        <td class="text-end pe-3">
                            <a href="/customer/transactions/${tx.id}" class="btn btn-sm btn-outline-primary py-1 px-2">
                                <i class="bi bi-eye"></i> Details
                            </a>
                        </td>
                    </tr>
                `;
            });
            tbody.innerHTML = rowsHtml;

            // Pagination info
            const startIdx = (data.page - 1) * data.per_page + 1;
            const endIdx = Math.min(data.page * data.per_page, data.total);
            if (paginationInfo) {
                paginationInfo.textContent = `Showing ${startIdx}–${endIdx} of ${data.total} transactions`;
            }

            // Render pagination controls
            renderPagination(data.page, data.total_pages);

        } catch (error) {
            console.error('Error fetching transactions:', error);
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center py-4 text-danger">
                        <i class="bi bi-exclamation-triangle me-1"></i> Failed to load transactions: ${error.message}
                    </td>
                </tr>
            `;
        }
    }

    function renderPagination(page, totalPages) {
        const controls = document.getElementById('paginationControls');
        if (!controls) return;

        if (totalPages <= 1) {
            controls.innerHTML = '';
            return;
        }

        let html = '';

        // Previous button
        html += `
            <li class="page-item ${page === 1 ? 'disabled' : ''}">
                <a class="page-link" href="#" data-page="${page - 1}">&laquo; Prev</a>
            </li>
        `;

        // Numbered buttons
        for (let i = 1; i <= totalPages; i++) {
            if (i === 1 || i === totalPages || (i >= page - 2 && i <= page + 2)) {
                html += `
                    <li class="page-item ${i === page ? 'active' : ''}">
                        <a class="page-link" href="#" data-page="${i}">${i}</a>
                    </li>
                `;
            } else if (i === page - 3 || i === page + 3) {
                html += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
            }
        }

        // Next button
        html += `
            <li class="page-item ${page === totalPages ? 'disabled' : ''}">
                <a class="page-link" href="#" data-page="${page + 1}">Next &raquo;</a>
            </li>
        `;

        controls.innerHTML = html;

        // Bind click events
        controls.querySelectorAll('a.page-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const targetPage = parseInt(link.getAttribute('data-page'));
                if (!isNaN(targetPage) && targetPage >= 1 && targetPage <= totalPages && targetPage !== page) {
                    currentPage = targetPage;
                    fetchTransactions();
                }
            });
        });
    }

    // Search event
    if (searchBtn && searchInput) {
        searchBtn.addEventListener('click', () => {
            currentQuery = searchInput.value.trim();
            currentPage = 1;
            fetchTransactions();
        });

        searchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                currentQuery = searchInput.value.trim();
                currentPage = 1;
                fetchTransactions();
            }
        });
    }

    // Status filter event
    if (statusFilter) {
        statusFilter.addEventListener('change', () => {
            currentStatus = statusFilter.value;
            currentPage = 1;
            fetchTransactions();
        });
    }

    // Per page select event
    if (perPageSelect) {
        perPageSelect.addEventListener('change', () => {
            currentPerPage = parseInt(perPageSelect.value) || 10;
            currentPage = 1;
            fetchTransactions();
        });
    }

    // Refresh button event
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => {
            fetchTransactions();
        });
    }

    // Initial load
    fetchTransactions();
}

/**
 * Load Details for a Single Transaction
 */
async function loadTransactionDetails(txId) {
    const errorContainer = document.getElementById('txDetailsError');
    const loadingContainer = document.getElementById('txDetailsLoading');
    const contentContainer = document.getElementById('txDetailsContent');

    if (!errorContainer || !loadingContainer || !contentContainer) return;

    try {
        const response = await fetch(`/api/customer/transactions/${txId}`, {
            method: 'GET',
            headers: { 'Accept': 'application/json' }
        });

        if (response.status === 401) {
            window.location.href = '/customer/login';
            return;
        }

        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            throw new Error(errData.error || `Transaction #${txId} not found or access denied.`);
        }

        const data = await response.json();

        // Update Header & Badge
        document.getElementById('detailTxId').textContent = `#TX-${data.id}`;
        document.getElementById('detailAmount').textContent = formatCurrency(data.amount);

        const statusBadgeContainer = document.getElementById('detailStatusBadge');
        if (data.class_label === 0) {
            statusBadgeContainer.innerHTML = `
                <span class="badge-status-normal fs-6 px-3 py-2">
                    <i class="bi bi-shield-check me-1"></i> Normal Transaction
                </span>
            `;
        } else {
            statusBadgeContainer.innerHTML = `
                <span class="badge-status-fraud fs-6 px-3 py-2">
                    <i class="bi bi-shield-exclamation me-1"></i> Fraud-Labeled Transaction
                </span>
            `;
        }

        // Summary details
        document.getElementById('summaryTxId').textContent = `#TX-${data.id}`;
        document.getElementById('summaryRowIndex').textContent = `Row #${data.dataset_row_id}`;
        document.getElementById('summaryAmount').textContent = formatCurrency(data.amount);
        document.getElementById('summaryTime').textContent = `${data.transaction_time} seconds from baseline`;
        document.getElementById('summaryClassLabel').textContent = data.class_label === 0 ? '0 (Normal)' : '1 (Fraud)';
        document.getElementById('summaryCreated').textContent = data.created_at || 'N/A';

        // Dataset disclaimer
        if (data.dataset_info) {
            const disclaimerElem = document.getElementById('datasetDisclaimerText');
            if (disclaimerElem) disclaimerElem.textContent = data.dataset_info;
        }

        // Render V1 - V28 feature cards
        const featuresGrid = document.getElementById('vFeaturesGrid');
        if (featuresGrid && data.features) {
            let gridHtml = '';
            for (let i = 1; i <= 28; i++) {
                const featKey = `V${i}`;
                const featVal = data.features[featKey] !== undefined ? data.features[featKey] : 'N/A';
                gridHtml += `
                    <div class="col-6 col-sm-4 col-md-3 col-xl-2">
                        <div class="v-feature-card text-center">
                            <div class="v-feature-name">${featKey}</div>
                            <div class="v-feature-val text-truncate" title="${featVal}">${featVal}</div>
                        </div>
                    </div>
                `;
            }
            featuresGrid.innerHTML = gridHtml;
        }

        // Show content
        loadingContainer.style.display = 'none';
        contentContainer.style.display = 'block';

    } catch (error) {
        console.error('Error loading transaction details:', error);
        loadingContainer.style.display = 'none';
        errorContainer.innerHTML = `
            <div class="alert alert-danger shadow-sm border-0" role="alert">
                <h5 class="alert-heading"><i class="bi bi-exclamation-triangle-fill me-2"></i> Error Loading Transaction</h5>
                <p class="mb-0">${error.message}</p>
            </div>
        `;
    }
}

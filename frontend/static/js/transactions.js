/**
 * TrustGuard AI - Transactions JS
 * Handles Customer Transactions List (Advanced Filters, Pagination, Risk Badges)
 * and Transaction Details with Report Suspicious feature.
 */

// Helper to format currency
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 2
    }).format(amount);
}

// Helper to render deterministic Risk Badge (Low / Medium / High)
function getRiskBadge(riskLevel) {
    const r = (riskLevel || 'LOW').toUpperCase();
    if (r === 'HIGH') {
        return `<span class="badge-risk-high"><i class="bi bi-shield-slash-fill"></i> High</span>`;
    } else if (r === 'MEDIUM') {
        return `<span class="badge-risk-medium"><i class="bi bi-shield-fill"></i> Medium</span>`;
    } else {
        return `<span class="badge-risk-low"><i class="bi bi-shield-check"></i> Low</span>`;
    }
}

// Helper to render dynamic Transaction Status Badge
function getStatusBadge(status, classLabel) {
    const s = (status || '').toLowerCase();
    if (s === 'reported') {
        return `<span class="badge-status-reported"><i class="bi bi-flag-fill"></i> Reported</span>`;
    } else if (s === 'under review' || s === 'under_review') {
        return `<span class="badge-status-review"><i class="bi bi-search"></i> Under Review</span>`;
    } else if (s === 'resolved') {
        return `<span class="badge-status-resolved"><i class="bi bi-check2-all"></i> Resolved</span>`;
    } else if (s === 'fraud' || s === 'fraud-labeled' || classLabel === 1) {
        return `<span class="badge-status-fraud"><i class="bi bi-shield-exclamation"></i> Fraud-Labeled</span>`;
    } else {
        return `<span class="badge-status-normal"><i class="bi bi-shield-check"></i> Normal</span>`;
    }
}

/**
 * Initialize Transactions List Page with Advanced Filters
 */
function initTransactionsListPage() {
    let currentPage = 1;
    let currentPerPage = 10;
    let currentStatus = 'all';
    let currentQuery = '';
    let currentMinAmount = '';
    let currentMaxAmount = '';

    const searchInput = document.getElementById('txSearchInput');
    const statusFilter = document.getElementById('txStatusFilter');
    const minAmountInput = document.getElementById('txMinAmount');
    const maxAmountInput = document.getElementById('txMaxAmount');
    const applyFilterBtn = document.getElementById('txApplyFilterBtn');
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
            const params = {
                page: currentPage,
                per_page: currentPerPage,
                status: currentStatus,
                q: currentQuery
            };
            if (currentMinAmount) params.min_amount = currentMinAmount;
            if (currentMaxAmount) params.max_amount = currentMaxAmount;

            const queryParams = new URLSearchParams(params);

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
                        <td class="fw-bold">${formatCurrency(tx.amount)}</td>
                        <td>${getRiskBadge(tx.risk_level)}</td>
                        <td>${getStatusBadge(tx.status, tx.class_label)}</td>
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

    function applyFilters() {
        if (searchInput) currentQuery = searchInput.value.trim();
        if (statusFilter) currentStatus = statusFilter.value;
        if (minAmountInput) currentMinAmount = minAmountInput.value.trim();
        if (maxAmountInput) currentMaxAmount = maxAmountInput.value.trim();
        currentPage = 1;
        fetchTransactions();
    }

    // Filter events
    if (applyFilterBtn) {
        applyFilterBtn.addEventListener('click', applyFilters);
    }

    if (searchInput) {
        searchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') applyFilters();
        });
    }

    if (statusFilter) {
        statusFilter.addEventListener('change', applyFilters);
    }

    if (perPageSelect) {
        perPageSelect.addEventListener('change', () => {
            currentPerPage = parseInt(perPageSelect.value) || 10;
            currentPage = 1;
            fetchTransactions();
        });
    }

    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => {
            fetchTransactions();
        });
    }

    // Initial load
    fetchTransactions();
}

/**
 * Load Details for a Single Customer Transaction
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

        // Update Header
        document.getElementById('detailTxId').textContent = `#TX-${data.id}`;
        document.getElementById('detailAmount').textContent = formatCurrency(data.amount);

        // Risk & Status Badges
        const riskBadgeElem = document.getElementById('detailRiskBadge');
        if (riskBadgeElem) {
            riskBadgeElem.innerHTML = getRiskBadge(data.risk_level);
        }

        const statusBadgeContainer = document.getElementById('detailStatusBadge');
        if (statusBadgeContainer) {
            statusBadgeContainer.innerHTML = getStatusBadge(data.status, data.class_label);
        }

        // Report Action Button / Active Case Badge
        const reportActionContainer = document.getElementById('detailReportAction');
        if (reportActionContainer) {
            if (data.is_reported || data.status === 'Reported' || data.status === 'Under Review') {
                reportActionContainer.innerHTML = `
                    <span class="badge bg-warning-subtle text-warning-emphasis border border-warning px-3 py-2">
                        <i class="bi bi-clock-history me-1"></i> Reported (Case #${data.case_id || 'Active'})
                    </span>
                `;
            } else if (data.status === 'Resolved') {
                reportActionContainer.innerHTML = `
                    <span class="badge bg-success-subtle text-success border border-success px-3 py-2">
                        <i class="bi bi-check2-circle me-1"></i> Investigation Resolved
                    </span>
                `;
            } else {
                reportActionContainer.innerHTML = `
                    <button class="btn btn-sm btn-outline-danger d-flex align-items-center gap-1" data-bs-toggle="modal" data-bs-target="#reportSuspiciousModal">
                        <i class="bi bi-flag"></i> Report Suspicious
                    </button>
                `;
            }
        }

        // Summary details
        document.getElementById('summaryTxId').textContent = `#TX-${data.id}`;
        document.getElementById('summaryRowIndex').textContent = `Row #${data.dataset_row_id}`;
        document.getElementById('summaryAmount').textContent = formatCurrency(data.amount);
        
        const summaryRisk = document.getElementById('summaryRiskBadge');
        if (summaryRisk) summaryRisk.innerHTML = getRiskBadge(data.risk_level);

        const summaryStatus = document.getElementById('summaryStatusText');
        if (summaryStatus) summaryStatus.innerHTML = getStatusBadge(data.status, data.class_label);

        document.getElementById('summaryTime').textContent = `${data.transaction_time} seconds from baseline`;
        document.getElementById('summaryClassLabel').textContent = data.class_label === 0 ? '0 (Normal)' : '1 (Fraud-Labeled)';
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

        // Bind Report Suspicious Form
        setupReportForm(txId);

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

function setupReportForm(txId) {
    const form = document.getElementById('reportSuspiciousForm');
    const feedback = document.getElementById('reportFeedback');
    const submitBtn = document.getElementById('submitReportBtn');

    if (!form || form.getAttribute('data-bound') === 'true') return;
    form.setAttribute('data-bound', 'true');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        feedback.innerHTML = '';

        const reason = document.getElementById('reportReason').value.trim();
        const origBtnText = submitBtn.innerHTML;
        submitBtn.disabled = true;
        submitBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-1"></span> Submitting...`;

        try {
            const res = await fetch(`/api/customer/transactions/${txId}/report`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify({ reason })
            });

            const resData = await res.json();

            if (res.ok && resData.success) {
                feedback.innerHTML = `
                    <div class="alert alert-success py-2 small" role="alert">
                        <i class="bi bi-check-circle-fill me-1"></i> ${resData.message}
                    </div>
                `;
                setTimeout(() => {
                    const modalEl = document.getElementById('reportSuspiciousModal');
                    if (modalEl && typeof bootstrap !== 'undefined') {
                        const modal = bootstrap.Modal.getInstance(modalEl);
                        if (modal) modal.hide();
                    }
                    loadTransactionDetails(txId);
                }, 1200);
            } else {
                feedback.innerHTML = `
                    <div class="alert alert-danger py-2 small" role="alert">
                        <i class="bi bi-x-circle-fill me-1"></i> ${resData.error || 'Failed to submit report.'}
                    </div>
                `;
                submitBtn.disabled = false;
                submitBtn.innerHTML = origBtnText;
            }
        } catch (err) {
            feedback.innerHTML = `
                <div class="alert alert-danger py-2 small" role="alert">
                    <i class="bi bi-wifi-off me-1"></i> Error: ${err.message}
                </div>
            `;
            submitBtn.disabled = false;
            submitBtn.innerHTML = origBtnText;
        }
    });
}

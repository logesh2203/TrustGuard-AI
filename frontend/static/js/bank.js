/**
 * TrustGuard AI - Bank Portal JS (Module 2)
 * Handles Bank Auth, Operations Dashboard, Dataset Browser, Case Management, Customers, and Analytics.
 */

// Helper to format currency
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 2
    }).format(amount);
}

// Helper to format numbers with commas
function formatNumber(num) {
    return new Intl.NumberFormat('en-US').format(num);
}

// Helper for status badge
function getBankStatusBadge(classLabel) {
    if (classLabel === 0) {
        return `<span class="badge-status-normal"><i class="bi bi-shield-check"></i> Normal</span>`;
    } else {
        return `<span class="badge-status-fraud"><i class="bi bi-shield-exclamation"></i> Fraud-Labeled</span>`;
    }
}

// Helper for case status badge
function getCaseStatusBadge(status) {
    switch (status) {
        case 'OPEN':
            return `<span class="badge-case-open"><i class="bi bi-clock"></i> Open</span>`;
        case 'UNDER_REVIEW':
            return `<span class="badge-case-review"><i class="bi bi-search"></i> Under Review</span>`;
        case 'RESOLVED':
            return `<span class="badge-case-resolved"><i class="bi bi-check-circle"></i> Resolved</span>`;
        default:
            return `<span class="badge bg-secondary">${status}</span>`;
    }
}

// Helper for priority badge
function getPriorityBadge(priority) {
    switch (priority) {
        case 'HIGH':
            return `<span class="badge-priority-high">HIGH</span>`;
        case 'MEDIUM':
            return `<span class="badge-priority-medium">MEDIUM</span>`;
        case 'LOW':
            return `<span class="badge-priority-low">LOW</span>`;
        default:
            return `<span class="badge bg-light text-dark border">${priority}</span>`;
    }
}

/**
 * 1. Bank Login Handler
 */
function initBankLogin() {
    const form = document.getElementById('bankLoginForm');
    const feedback = document.getElementById('bankLoginFeedback');
    const submitBtn = document.getElementById('bankLoginSubmitBtn');

    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        feedback.innerHTML = '';

        const email = document.getElementById('bankEmail').value.trim();
        const password = document.getElementById('bankPassword').value;

        if (!email || !password) {
            feedback.innerHTML = `
                <div class="alert alert-warning py-2 small" role="alert">
                    <i class="bi bi-exclamation-circle me-1"></i> Please enter both bank email and password.
                </div>
            `;
            return;
        }

        const originalText = submitBtn.innerHTML;
        submitBtn.disabled = true;
        submitBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-2" role="status"></span> Authenticating...`;

        try {
            const response = await fetch('/api/bank/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify({ email, password })
            });

            const data = await response.json();

            if (response.ok && data.success) {
                feedback.innerHTML = `
                    <div class="alert alert-success py-2 small" role="alert">
                        <i class="bi bi-check-circle-fill me-1"></i> ${data.message} Redirecting to Bank Dashboard...
                    </div>
                `;
                setTimeout(() => {
                    window.location.href = data.redirect || '/bank/dashboard';
                }, 600);
            } else {
                feedback.innerHTML = `
                    <div class="alert alert-danger py-2 small" role="alert">
                        <i class="bi bi-x-circle-fill me-1"></i> ${data.error || 'Authentication failed.'}
                    </div>
                `;
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalText;
            }
        } catch (error) {
            console.error('Bank login error:', error);
            feedback.innerHTML = `
                <div class="alert alert-danger py-2 small" role="alert">
                    <i class="bi bi-wifi-off me-1"></i> Server connection failed.
                </div>
            `;
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalText;
        }
    });
}

/**
 * 2. Bank Dashboard Handler
 */
async function loadBankDashboard() {
    try {
        const response = await fetch('/api/bank/dashboard', {
            method: 'GET',
            headers: { 'Accept': 'application/json' }
        });

        if (response.status === 401 || response.status === 403) {
            window.location.href = '/bank/login';
            return;
        }

        if (!response.ok) {
            throw new Error(`Failed to load bank dashboard (Status: ${response.status})`);
        }

        const data = await response.json();

        // Update Stat Cards
        document.getElementById('bankStatTotal').textContent = formatNumber(data.total_transactions);
        document.getElementById('bankStatNormal').textContent = formatNumber(data.normal_transactions);
        document.getElementById('bankStatFraud').textContent = formatNumber(data.fraud_transactions);
        document.getElementById('bankStatCases').textContent = formatNumber(data.open_cases);
        document.getElementById('bankStatCustomers').textContent = `${formatNumber(data.customer_count)} Accounts`;

        // Update Recent Transactions Table
        const tbody = document.getElementById('bankRecentTxBody');
        if (tbody) {
            if (!data.recent_transactions || data.recent_transactions.length === 0) {
                tbody.innerHTML = `<tr><td colspan="5" class="text-center py-4 text-muted">No recent transactions.</td></tr>`;
                return;
            }

            let rows = '';
            data.recent_transactions.forEach(tx => {
                rows += `
                    <tr>
                        <td class="ps-3 fw-bold font-monospace text-dark">Row #${tx.id}</td>
                        <td class="text-muted small">${tx.transaction_time}s</td>
                        <td class="fw-bold">${formatCurrency(tx.amount)}</td>
                        <td>${getBankStatusBadge(tx.class_label)}</td>
                        <td class="text-end pe-3">
                            <a href="/bank/transactions/${tx.id}" class="btn btn-sm btn-outline-primary py-1 px-2">
                                <i class="bi bi-eye"></i> View
                            </a>
                        </td>
                    </tr>
                `;
            });
            tbody.innerHTML = rows;
        }
    } catch (error) {
        console.error('Bank dashboard error:', error);
        showAlert(`Failed to load bank dashboard: ${error.message}`, 'danger');
    }
}

/**
 * 3. Bank Transactions Dataset Browser (20 per page)
 */
function initBankTransactionsList() {
    let currentPage = 1;
    let currentPerPage = 20;
    let currentStatus = 'all';
    let currentQuery = '';

    const searchInput = document.getElementById('bankTxSearchInput');
    const searchBtn = document.getElementById('bankTxSearchBtn');
    const statusFilter = document.getElementById('bankTxStatusFilter');
    const perPageSelect = document.getElementById('bankTxPerPage');
    const refreshBtn = document.getElementById('bankTxRefreshBtn');

    async function fetchDatasetTransactions() {
        const tbody = document.getElementById('bankTxTableBody');
        const paginationInfo = document.getElementById('bankPaginationInfo');
        const paginationControls = document.getElementById('bankPaginationControls');

        if (!tbody) return;

        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="text-center py-5 text-muted">
                    <div class="spinner-border spinner-border-sm text-primary me-2" role="status"></div>
                    Querying dataset (${currentStatus === 'all' ? '284,807 rows' : currentStatus})...
                </td>
            </tr>
        `;

        try {
            const queryParams = new URLSearchParams({
                page: currentPage,
                limit: currentPerPage,
                status: currentStatus,
                q: currentQuery
            });

            const response = await fetch(`/api/bank/transactions?${queryParams.toString()}`, {
                method: 'GET',
                headers: { 'Accept': 'application/json' }
            });

            if (response.status === 401 || response.status === 403) {
                window.location.href = '/bank/login';
                return;
            }

            if (!response.ok) {
                throw new Error(`Failed to fetch transactions (Status: ${response.status})`);
            }

            const data = await response.json();
            const list = data.transactions || [];

            if (list.length === 0) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="6" class="text-center py-5 text-muted">
                            <i class="bi bi-search fs-3 d-block mb-2 text-secondary"></i>
                            No dataset transactions matched your criteria.
                        </td>
                    </tr>
                `;
                if (paginationInfo) paginationInfo.textContent = 'Showing 0 of 0 transactions';
                if (paginationControls) paginationControls.innerHTML = '';
                return;
            }

            let rows = '';
            list.forEach(tx => {
                rows += `
                    <tr>
                        <td class="ps-3 fw-bold font-monospace text-dark">Row #${tx.id}</td>
                        <td class="text-muted small">${tx.transaction_time}s</td>
                        <td class="fw-bold">${formatCurrency(tx.amount)}</td>
                        <td class="font-monospace">${tx.class_label === 1 ? '<span class="text-danger fw-bold">1</span>' : '<span class="text-secondary">0</span>'}</td>
                        <td>${getBankStatusBadge(tx.class_label)}</td>
                        <td class="text-end pe-3">
                            <a href="/bank/transactions/${tx.id}" class="btn btn-sm btn-outline-primary py-1 px-2">
                                <i class="bi bi-eye"></i> Inspect
                            </a>
                        </td>
                    </tr>
                `;
            });
            tbody.innerHTML = rows;

            // Pagination info
            const startIdx = (data.page - 1) * data.per_page + 1;
            const endIdx = Math.min(data.page * data.per_page, data.total);
            if (paginationInfo) {
                paginationInfo.textContent = `Showing ${formatNumber(startIdx)}–${formatNumber(endIdx)} of ${formatNumber(data.total)} transactions`;
            }

            // Render Pagination Buttons
            renderBankPagination(data.page, data.total_pages);

        } catch (error) {
            console.error('Error loading dataset transactions:', error);
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center py-4 text-danger">
                        <i class="bi bi-exclamation-triangle me-1"></i> ${error.message}
                    </td>
                </tr>
            `;
        }
    }

    function renderBankPagination(page, totalPages) {
        const controls = document.getElementById('bankPaginationControls');
        if (!controls) return;

        if (totalPages <= 1) {
            controls.innerHTML = '';
            return;
        }

        let html = '';

        // Previous
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

        // Next
        html += `
            <li class="page-item ${page === totalPages ? 'disabled' : ''}">
                <a class="page-link" href="#" data-page="${page + 1}">Next &raquo;</a>
            </li>
        `;

        controls.innerHTML = html;

        controls.querySelectorAll('a.page-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const targetPage = parseInt(link.getAttribute('data-page'));
                if (!isNaN(targetPage) && targetPage >= 1 && targetPage <= totalPages && targetPage !== page) {
                    currentPage = targetPage;
                    fetchDatasetTransactions();
                }
            });
        });
    }

    if (searchBtn && searchInput) {
        searchBtn.addEventListener('click', () => {
            currentQuery = searchInput.value.trim();
            currentPage = 1;
            fetchDatasetTransactions();
        });

        searchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                currentQuery = searchInput.value.trim();
                currentPage = 1;
                fetchDatasetTransactions();
            }
        });
    }

    if (statusFilter) {
        statusFilter.addEventListener('change', () => {
            currentStatus = statusFilter.value;
            currentPage = 1;
            fetchDatasetTransactions();
        });
    }

    if (perPageSelect) {
        perPageSelect.addEventListener('change', () => {
            currentPerPage = parseInt(perPageSelect.value) || 20;
            currentPage = 1;
            fetchDatasetTransactions();
        });
    }

    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => {
            fetchDatasetTransactions();
        });
    }

    fetchDatasetTransactions();
}

/**
 * 4. Bank Transaction Details & Case Creation
 */
async function loadBankTransactionDetails(rowId) {
    const errorContainer = document.getElementById('bankTxError');
    const loadingContainer = document.getElementById('bankTxLoading');
    const contentContainer = document.getElementById('bankTxContent');
    const caseActionBody = document.getElementById('caseActionCardBody');
    const caseActionTop = document.getElementById('caseActionTop');

    if (!errorContainer || !loadingContainer || !contentContainer) return;

    try {
        const response = await fetch(`/api/bank/transactions/${rowId}`, {
            method: 'GET',
            headers: { 'Accept': 'application/json' }
        });

        if (response.status === 401 || response.status === 403) {
            window.location.href = '/bank/login';
            return;
        }

        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            throw new Error(errData.error || `Transaction #${rowId} not found.`);
        }

        const data = await response.json();

        // Header & Metadata
        document.getElementById('btxRowId').textContent = `Row #${data.dataset_row_id}`;
        document.getElementById('btxAmount').textContent = formatCurrency(data.amount);
        
        const statusBadgeContainer = document.getElementById('btxStatusBadge');
        if (data.class_label === 0) {
            statusBadgeContainer.innerHTML = `
                <span class="badge-status-normal fs-6 px-3 py-2">
                    <i class="bi bi-shield-check me-1"></i> Normal Transaction (Class 0)
                </span>
            `;
        } else {
            statusBadgeContainer.innerHTML = `
                <span class="badge-status-fraud fs-6 px-3 py-2">
                    <i class="bi bi-shield-exclamation me-1"></i> Fraud-Labeled (Class 1)
                </span>
            `;
        }

        document.getElementById('metaRowId').textContent = `#${data.dataset_row_id}`;
        document.getElementById('metaAmount').textContent = formatCurrency(data.amount);
        document.getElementById('metaTime').textContent = `${data.time} seconds`;
        document.getElementById('metaClass').textContent = data.class_label === 0 ? '0 (Normal)' : '1 (Fraud-Labeled)';

        // Case status & Case creation card
        const metaCaseStatus = document.getElementById('metaCaseStatus');
        if (data.existing_case) {
            const c = data.existing_case;
            metaCaseStatus.innerHTML = `${getCaseStatusBadge(c.status)} <span class="ms-1">${getPriorityBadge(c.priority)}</span>`;
            
            caseActionTop.innerHTML = `
                <a href="/bank/cases/${c.id}" class="btn btn-warning btn-sm d-flex align-items-center gap-1 text-dark">
                    <i class="bi bi-folder2-open"></i> View Case #${c.id}
                </a>
            `;

            caseActionBody.innerHTML = `
                <div class="alert alert-warning py-3 px-3 border-0 bg-warning-subtle text-warning-emphasis mb-3">
                    <div class="d-flex justify-content-between align-items-center mb-1">
                        <strong class="fs-6"><i class="bi bi-folder-check me-1"></i> Case #${c.id} Already Active</strong>
                        ${getCaseStatusBadge(c.status)}
                    </div>
                    <p class="small mb-2 text-dark">Created on ${c.created_at} by ${c.creator_name}.</p>
                    <div class="p-2 bg-white rounded border small text-secondary mb-3">
                        <strong>Notes:</strong> ${c.notes || 'No investigation notes.'}
                    </div>
                    <a href="/bank/cases/${c.id}" class="btn btn-warning btn-sm text-dark fw-semibold">
                        <i class="bi bi-pencil-square me-1"></i> Open &amp; Edit Case #${c.id}
                    </a>
                </div>
            `;
        } else {
            metaCaseStatus.innerHTML = `<span class="badge bg-light text-muted border">No Active Case</span>`;

            caseActionTop.innerHTML = `
                <button class="btn btn-warning btn-sm d-flex align-items-center gap-1 text-dark" id="topCreateCaseBtn">
                    <i class="bi bi-plus-circle"></i> Create Review Case
                </button>
            `;

            caseActionBody.innerHTML = `
                <p class="text-secondary small mb-3">
                    Bank analysts can initiate a formal fraud review case for this transaction in the SQLite review database.
                </p>
                <form id="createCaseForm">
                    <div class="mb-3">
                        <label class="form-label fw-semibold text-secondary small">Case Priority</label>
                        <select class="form-select form-select-sm" id="casePrioritySelect">
                            <option value="LOW">Low Priority</option>
                            <option value="MEDIUM" ${data.class_label === 1 ? 'selected' : ''}>Medium Priority</option>
                            <option value="HIGH" ${data.class_label === 1 ? 'selected' : ''}>High Priority</option>
                        </select>
                    </div>
                    <div class="mb-3">
                        <label class="form-label fw-semibold text-secondary small">Initial Notes</label>
                        <textarea class="form-control form-control-sm" id="caseNotesInput" rows="2" placeholder="Describe reason for review or anomaly...">${data.class_label === 1 ? 'Ground truth dataset label is Fraud (Class 1). Initiating analyst review.' : 'Routine analyst transaction inspection.'}</textarea>
                    </div>
                    <button type="submit" class="btn btn-warning btn-sm text-dark fw-semibold d-flex align-items-center gap-1" id="submitCreateCaseBtn">
                        <i class="bi bi-folder-plus"></i> Create Review Case
                    </button>
                </form>
            `;

            // Bind create case submit
            const form = document.getElementById('createCaseForm');
            if (form) {
                form.addEventListener('submit', (e) => {
                    e.preventDefault();
                    handleCreateCase(data.dataset_row_id);
                });
            }

            const topBtn = document.getElementById('topCreateCaseBtn');
            if (topBtn) {
                topBtn.addEventListener('click', () => {
                    handleCreateCase(data.dataset_row_id);
                });
            }
        }

        // Render V1 - V28 feature cards
        const featuresGrid = document.getElementById('bankVFeaturesGrid');
        if (featuresGrid && data.features) {
            let gridHtml = '';
            for (let i = 1; i <= 28; i++) {
                const key = `V${i}`;
                const val = data.features[key] !== undefined ? data.features[key] : 'N/A';
                gridHtml += `
                    <div class="col-6 col-sm-4 col-md-3 col-xl-2">
                        <div class="v-feature-card text-center">
                            <div class="v-feature-name">${key}</div>
                            <div class="v-feature-val text-truncate" title="${val}">${val}</div>
                        </div>
                    </div>
                `;
            }
            featuresGrid.innerHTML = gridHtml;
        }

        loadingContainer.style.display = 'none';
        contentContainer.style.display = 'block';

    } catch (error) {
        console.error('Error loading bank transaction details:', error);
        loadingContainer.style.display = 'none';
        errorContainer.innerHTML = `
            <div class="alert alert-danger shadow-sm border-0" role="alert">
                <h5><i class="bi bi-exclamation-triangle-fill me-2"></i> Error</h5>
                <p class="mb-0">${error.message}</p>
            </div>
        `;
    }
}

async function handleCreateCase(rowId) {
    const prioritySelect = document.getElementById('casePrioritySelect');
    const notesInput = document.getElementById('caseNotesInput');
    const priority = prioritySelect ? prioritySelect.value : 'MEDIUM';
    const notes = notesInput ? notesInput.value.trim() : '';

    try {
        const response = await fetch('/api/bank/cases', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify({
                transaction_id: rowId,
                priority: priority,
                notes: notes
            })
        });

        const resData = await response.json();

        if (response.ok && resData.success) {
            showAlert(`Fraud review case #${resData.case.id} created! Redirecting to case...`, 'success');
            setTimeout(() => {
                window.location.href = `/bank/cases/${resData.case.id}`;
            }, 800);
        } else {
            showAlert(resData.error || 'Failed to create review case.', 'danger');
        }
    } catch (error) {
        console.error('Case creation failed:', error);
        showAlert(`Error creating case: ${error.message}`, 'danger');
    }
}

/**
 * 5. Bank Fraud Cases List
 */
function initBankCasesList() {
    let currentStatus = 'ALL';

    const filterGroup = document.getElementById('caseStatusFilterGroup');
    const refreshBtn = document.getElementById('refreshCasesBtn');

    async function fetchCases() {
        const tbody = document.getElementById('casesTableBody');
        const countElem = document.getElementById('totalCasesCount');

        if (!tbody) return;

        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="text-center py-5 text-muted">
                    <div class="spinner-border spinner-border-sm text-primary me-2" role="status"></div>
                    Loading review cases...
                </td>
            </tr>
        `;

        try {
            const queryParams = new URLSearchParams({ status: currentStatus });
            const response = await fetch(`/api/bank/cases?${queryParams.toString()}`, {
                method: 'GET',
                headers: { 'Accept': 'application/json' }
            });

            if (response.status === 401 || response.status === 403) {
                window.location.href = '/bank/login';
                return;
            }

            if (!response.ok) {
                throw new Error(`Failed to load cases (Status: ${response.status})`);
            }

            const data = await response.json();
            const list = data.cases || [];

            if (countElem) countElem.textContent = `${list.length} cases`;

            if (list.length === 0) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="6" class="text-center py-5 text-muted">
                            <i class="bi bi-folder2 fs-3 d-block mb-2 text-secondary"></i>
                            No fraud review cases found matching status: <strong>${currentStatus}</strong>.
                        </td>
                    </tr>
                `;
                return;
            }

            let rows = '';
            list.forEach(c => {
                rows += `
                    <tr>
                        <td class="ps-3 fw-bold text-dark font-monospace">#CASE-${c.id}</td>
                        <td class="font-monospace">
                            <a href="/bank/transactions/${c.transaction_id}" class="text-decoration-none">
                                Row #${c.transaction_id} <i class="bi bi-box-arrow-up-right small"></i>
                            </a>
                        </td>
                        <td>${getPriorityBadge(c.priority)}</td>
                        <td>${getCaseStatusBadge(c.status)}</td>
                        <td class="text-muted small">${c.created_at}</td>
                        <td class="text-end pe-3">
                            <a href="/bank/cases/${c.id}" class="btn btn-sm btn-outline-primary py-1 px-2">
                                <i class="bi bi-pencil-square"></i> View Case
                            </a>
                        </td>
                    </tr>
                `;
            });
            tbody.innerHTML = rows;

        } catch (error) {
            console.error('Error loading fraud cases:', error);
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center py-4 text-danger">
                        <i class="bi bi-exclamation-triangle me-1"></i> ${error.message}
                    </td>
                </tr>
            `;
        }
    }

    if (filterGroup) {
        filterGroup.querySelectorAll('button').forEach(btn => {
            btn.addEventListener('click', () => {
                filterGroup.querySelectorAll('button').forEach(b => {
                    b.classList.remove('btn-primary', 'active');
                    b.classList.add('btn-outline-secondary');
                });
                btn.classList.remove('btn-outline-secondary');
                btn.classList.add('btn-primary', 'active');

                currentStatus = btn.getAttribute('data-status') || 'ALL';
                fetchCases();
            });
        });
    }

    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => fetchCases());
    }

    fetchCases();
}

/**
 * 6. Bank Case Details & Live Editor
 */
async function loadBankCaseDetails(caseId) {
    const feedback = document.getElementById('caseFeedback');
    const loading = document.getElementById('caseLoading');
    const content = document.getElementById('caseContent');
    const form = document.getElementById('caseEditForm');
    const saveBtn = document.getElementById('saveCaseBtn');

    if (!loading || !content) return;

    try {
        const response = await fetch(`/api/bank/cases/${caseId}`, {
            method: 'GET',
            headers: { 'Accept': 'application/json' }
        });

        if (response.status === 401 || response.status === 403) {
            window.location.href = '/bank/login';
            return;
        }

        if (!response.ok) {
            throw new Error(`Review case #${caseId} not found.`);
        }

        const data = await response.json();

        // Update Overview
        document.getElementById('headerCaseBadge').textContent = `Case #${data.id}`;
        document.getElementById('dispCaseId').textContent = `#CASE-${data.id}`;
        document.getElementById('dispCaseStatus').innerHTML = getCaseStatusBadge(data.status);
        document.getElementById('dispCasePriority').innerHTML = getPriorityBadge(data.priority);
        document.getElementById('dispCreatedBy').textContent = data.creator_name || 'Bank Analyst';
        document.getElementById('dispCreatedAt').textContent = data.created_at || 'N/A';
        document.getElementById('dispUpdatedAt').textContent = data.updated_at || 'N/A';

        // Update Attached Transaction Summary
        if (data.transaction) {
            document.getElementById('txSummaryRowId').textContent = `Row #${data.transaction_id}`;
            document.getElementById('txSummaryAmount').textContent = formatCurrency(data.transaction.amount);
            document.getElementById('txSummaryTime').textContent = `${data.transaction.time}s`;
            document.getElementById('txSummaryBadge').innerHTML = getBankStatusBadge(data.transaction.class_label);
            document.getElementById('viewTxDetailsLink').href = `/bank/transactions/${data.transaction_id}`;
        }

        // Form Inputs
        document.getElementById('editCaseStatus').value = data.status;
        document.getElementById('editCasePriority').value = data.priority;
        document.getElementById('editCaseNotes').value = data.notes || '';
        document.getElementById('editCaseResolution').value = data.resolution || '';

        loading.style.display = 'none';
        content.style.display = 'block';

        // Bind form submit
        if (form) {
            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                feedback.innerHTML = '';

                const status = document.getElementById('editCaseStatus').value;
                const priority = document.getElementById('editCasePriority').value;
                const notes = document.getElementById('editCaseNotes').value;
                const resolution = document.getElementById('editCaseResolution').value;

                const origBtn = saveBtn.innerHTML;
                saveBtn.disabled = true;
                saveBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-2" role="status"></span> Saving...`;

                try {
                    const putRes = await fetch(`/api/bank/cases/${caseId}`, {
                        method: 'PUT',
                        headers: {
                            'Content-Type': 'application/json',
                            'Accept': 'application/json'
                        },
                        body: JSON.stringify({ status, priority, notes, resolution })
                    });

                    const putData = await putRes.json();

                    if (putRes.ok && putData.success) {
                        feedback.innerHTML = `
                            <div class="alert alert-success alert-dismissible fade show shadow-sm" role="alert">
                                <i class="bi bi-check-circle-fill me-2"></i> Case updated successfully!
                                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                            </div>
                        `;
                        // Update badges in UI
                        document.getElementById('dispCaseStatus').innerHTML = getCaseStatusBadge(status);
                        document.getElementById('dispCasePriority').innerHTML = getPriorityBadge(priority);
                        if (putData.case && putData.case.updated_at) {
                            document.getElementById('dispUpdatedAt').textContent = putData.case.updated_at;
                        }
                    } else {
                        feedback.innerHTML = `
                            <div class="alert alert-danger alert-dismissible fade show shadow-sm" role="alert">
                                <i class="bi bi-x-circle-fill me-2"></i> ${putData.error || 'Failed to update case.'}
                                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                            </div>
                        `;
                    }
                } catch (err) {
                    feedback.innerHTML = `
                        <div class="alert alert-danger alert-dismissible fade show shadow-sm" role="alert">
                            <i class="bi bi-wifi-off me-2"></i> Error saving case: ${err.message}
                            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                        </div>
                    `;
                } finally {
                    saveBtn.disabled = false;
                    saveBtn.innerHTML = origBtn;
                }
            });
        }

    } catch (error) {
        console.error('Error loading case details:', error);
        loading.style.display = 'none';
        if (feedback) {
            feedback.innerHTML = `
                <div class="alert alert-danger shadow-sm border-0" role="alert">
                    <h5><i class="bi bi-exclamation-triangle-fill me-2"></i> Error Loading Case</h5>
                    <p class="mb-0">${error.message}</p>
                </div>
            `;
        }
    }
}

/**
 * 7. Bank Customers Directory Loader
 */
async function loadBankCustomers() {
    const tbody = document.getElementById('customersTableBody');
    const countBadge = document.getElementById('totalCustomersBadge');

    if (!tbody) return;

    try {
        const response = await fetch('/api/bank/customers', {
            method: 'GET',
            headers: { 'Accept': 'application/json' }
        });

        if (response.status === 401 || response.status === 403) {
            window.location.href = '/bank/login';
            return;
        }

        if (!response.ok) {
            throw new Error(`Failed to load customers (Status: ${response.status})`);
        }

        const data = await response.json();
        const list = data.customers || [];

        if (countBadge) countBadge.textContent = `${list.length} Registered`;

        if (list.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="5" class="text-center py-5 text-muted">
                        <i class="bi bi-person-x fs-3 d-block mb-2 text-secondary"></i>
                        No customer accounts registered yet.
                    </td>
                </tr>
            `;
            return;
        }

        let rows = '';
        list.forEach(c => {
            rows += `
                <tr>
                    <td class="ps-3 fw-bold font-monospace text-dark">#CUST-${c.id}</td>
                    <td class="fw-semibold text-navy">${c.name}</td>
                    <td class="text-secondary">${c.email}</td>
                    <td><span class="badge bg-secondary-subtle text-secondary border">CUSTOMER</span></td>
                    <td class="text-end pe-3 text-muted small">${c.created_at || 'N/A'}</td>
                </tr>
            `;
        });
        tbody.innerHTML = rows;

    } catch (error) {
        console.error('Error loading customers:', error);
        tbody.innerHTML = `
            <tr>
                <td colspan="5" class="text-center py-4 text-danger">
                    <i class="bi bi-exclamation-triangle me-1"></i> ${error.message}
                </td>
            </tr>
        `;
    }
}

/**
 * 8. Bank Analytics Loader & Charts (Chart.js)
 */
let classChartInstance = null;
let caseChartInstance = null;

async function loadBankAnalytics() {
    try {
        const response = await fetch('/api/bank/analytics', {
            method: 'GET',
            headers: { 'Accept': 'application/json' }
        });

        if (response.status === 401 || response.status === 403) {
            window.location.href = '/bank/login';
            return;
        }

        if (!response.ok) {
            throw new Error(`Failed to load analytics (Status: ${response.status})`);
        }

        const data = await response.json();

        // Update Stat Cards
        document.getElementById('anaTotal').textContent = formatNumber(data.total_transactions);
        document.getElementById('anaNormalPct').textContent = `${(100 - data.fraud_percentage).toFixed(2)}%`;
        document.getElementById('anaNormalCount').textContent = `${formatNumber(data.normal_transactions)} normal txs`;
        document.getElementById('anaFraudPct').textContent = `${data.fraud_percentage.toFixed(3)}%`;
        document.getElementById('anaFraudCount').textContent = `${formatNumber(data.fraud_transactions)} fraud txs`;

        const cases = data.case_stats || { open: 0, under_review: 0, resolved: 0, total_cases: 0 };
        document.getElementById('anaTotalCases').textContent = cases.total_cases;
        document.getElementById('anaResolvedCases').textContent = `${cases.resolved} resolved`;

        // 1. Render Class Distribution Doughnut Chart
        const classCanvas = document.getElementById('classDistChart');
        if (classCanvas && typeof Chart !== 'undefined') {
            if (classChartInstance) classChartInstance.destroy();
            classChartInstance = new Chart(classCanvas, {
                type: 'doughnut',
                data: {
                    labels: ['Normal (Class 0)', 'Fraud-Labeled (Class 1)'],
                    datasets: [{
                        data: [data.normal_transactions, data.fraud_transactions],
                        backgroundColor: ['#059669', '#dc2626'],
                        borderWidth: 2,
                        borderColor: '#ffffff'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { position: 'bottom' }
                    }
                }
            });
        }

        // 2. Render Case Status Bar Chart
        const caseCanvas = document.getElementById('caseStatusChart');
        if (caseCanvas && typeof Chart !== 'undefined') {
            if (caseChartInstance) caseChartInstance.destroy();
            caseChartInstance = new Chart(caseCanvas, {
                type: 'bar',
                data: {
                    labels: ['Open', 'Under Review', 'Resolved'],
                    datasets: [{
                        label: 'Cases',
                        data: [cases.open, cases.under_review, cases.resolved],
                        backgroundColor: ['#f59e0b', '#2563eb', '#059669'],
                        borderRadius: 6
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: { stepSize: 1 }
                        }
                    },
                    plugins: {
                        legend: { display: false }
                    }
                }
            });
        }

    } catch (error) {
        console.error('Error loading analytics:', error);
        showAlert(`Failed to load analytics: ${error.message}`, 'danger');
    }
}

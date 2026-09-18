/**
 * TrustGuard AI - Customer JS
 * Handles Customer Auth (Login, Register) and Dashboard Data Fetching.
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
 * Initialize Customer Login Form
 */
function initCustomerLogin() {
    const form = document.getElementById('loginForm');
    const feedback = document.getElementById('loginFeedback');
    const submitBtn = document.getElementById('loginSubmitBtn');

    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        feedback.innerHTML = '';

        const email = document.getElementById('email').value.trim();
        const password = document.getElementById('password').value;

        if (!email || !password) {
            feedback.innerHTML = `
                <div class="alert alert-warning py-2 small" role="alert">
                    <i class="bi bi-exclamation-circle me-1"></i> Please enter both email and password.
                </div>
            `;
            return;
        }

        // Disable button while processing
        const originalBtnText = submitBtn.innerHTML;
        submitBtn.disabled = true;
        submitBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-2" role="status"></span> Signing in...`;

        try {
            const response = await fetch('/api/customer/login', {
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
                        <i class="bi bi-check-circle-fill me-1"></i> ${data.message} Redirecting...
                    </div>
                `;
                setTimeout(() => {
                    window.location.href = data.redirect || '/customer/dashboard';
                }, 600);
            } else {
                feedback.innerHTML = `
                    <div class="alert alert-danger py-2 small" role="alert">
                        <i class="bi bi-x-circle-fill me-1"></i> ${data.error || 'Login failed. Please check credentials.'}
                    </div>
                `;
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalBtnText;
            }
        } catch (error) {
            console.error('Login error:', error);
            feedback.innerHTML = `
                <div class="alert alert-danger py-2 small" role="alert">
                    <i class="bi bi-wifi-off me-1"></i> Connection error. Unable to reach server.
                </div>
            `;
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalBtnText;
        }
    });
}

/**
 * Initialize Customer Registration Form
 */
function initCustomerRegister() {
    const form = document.getElementById('registerForm');
    const feedback = document.getElementById('registerFeedback');
    const submitBtn = document.getElementById('registerSubmitBtn');

    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        feedback.innerHTML = '';

        const name = document.getElementById('regName').value.trim();
        const email = document.getElementById('regEmail').value.trim();
        const password = document.getElementById('regPassword').value;
        const confirmPassword = document.getElementById('regConfirmPassword').value;

        // Client-side validations
        if (!name || !email || !password || !confirmPassword) {
            feedback.innerHTML = `
                <div class="alert alert-warning py-2 small" role="alert">
                    <i class="bi bi-exclamation-circle me-1"></i> All fields are required.
                </div>
            `;
            return;
        }

        if (password.length < 6) {
            feedback.innerHTML = `
                <div class="alert alert-warning py-2 small" role="alert">
                    <i class="bi bi-exclamation-circle me-1"></i> Password must be at least 6 characters long.
                </div>
            `;
            return;
        }

        if (password !== confirmPassword) {
            feedback.innerHTML = `
                <div class="alert alert-warning py-2 small" role="alert">
                    <i class="bi bi-exclamation-circle me-1"></i> Passwords do not match.
                </div>
            `;
            return;
        }

        // Disable button while processing
        const originalBtnText = submitBtn.innerHTML;
        submitBtn.disabled = true;
        submitBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-2" role="status"></span> Creating account...`;

        try {
            const response = await fetch('/api/customer/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify({
                    name,
                    email,
                    password,
                    confirm_password: confirmPassword
                })
            });

            const data = await response.json();

            if (response.ok && data.success) {
                feedback.innerHTML = `
                    <div class="alert alert-success py-2 small" role="alert">
                        <i class="bi bi-check-circle-fill me-1"></i> ${data.message} Redirecting to login...
                    </div>
                `;
                setTimeout(() => {
                    window.location.href = data.redirect || '/customer/login';
                }, 1000);
            } else {
                feedback.innerHTML = `
                    <div class="alert alert-danger py-2 small" role="alert">
                        <i class="bi bi-x-circle-fill me-1"></i> ${data.error || 'Registration failed.'}
                    </div>
                `;
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalBtnText;
            }
        } catch (error) {
            console.error('Registration error:', error);
            feedback.innerHTML = `
                <div class="alert alert-danger py-2 small" role="alert">
                    <i class="bi bi-wifi-off me-1"></i> Connection error. Unable to reach server.
                </div>
            `;
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalBtnText;
        }
    });
}

/**
 * Load Customer Dashboard Data from API
 */
async function loadDashboardData() {
    try {
        const response = await fetch('/api/customer/dashboard', {
            method: 'GET',
            headers: {
                'Accept': 'application/json'
            }
        });

        if (response.status === 401) {
            window.location.href = '/customer/login';
            return;
        }

        if (!response.ok) {
            throw new Error(`Server returned error status: ${response.status}`);
        }

        const data = await response.json();

        // Update Welcome Message
        const welcomeElem = document.getElementById('dashboardWelcome');
        if (welcomeElem && data.user && data.user.name) {
            welcomeElem.textContent = `Welcome to TrustGuard AI, ${data.user.name}`;
        }

        // Update Stat Cards
        const totalElem = document.getElementById('statTotal');
        const normalElem = document.getElementById('statNormal');
        const fraudElem = document.getElementById('statFraud');
        const attentionElem = document.getElementById('statAttention');

        if (totalElem) totalElem.textContent = data.total_transactions;
        if (normalElem) normalElem.textContent = data.normal_transactions;
        if (fraudElem) fraudElem.textContent = data.fraud_transactions;
        if (attentionElem) attentionElem.textContent = data.attention_transactions;

        // Populate Recent Transactions Table
        const tbody = document.getElementById('recentTransactionsBody');
        if (tbody) {
            if (!data.recent_transactions || data.recent_transactions.length === 0) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="5" class="text-center py-4 text-muted">
                            <i class="bi bi-inbox fs-4 d-block mb-1"></i>
                            No transaction records found for this account.
                        </td>
                    </tr>
                `;
                return;
            }

            let rowsHtml = '';
            data.recent_transactions.forEach(tx => {
                rowsHtml += `
                    <tr>
                        <td class="ps-3 fw-semibold font-monospace text-dark">#TX-${tx.id}</td>
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
        }
    } catch (error) {
        console.error('Failed to load dashboard data:', error);
        showAlert(`Failed to load dashboard data: ${error.message}`, 'danger');
    }
}

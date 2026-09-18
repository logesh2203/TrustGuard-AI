# TrustGuard AI

TrustGuard AI is an AI-powered financial security platform. The repository currently contains **MODULE 1 (Basic Customer Portal)** and **MODULE 2 (Basic Bank Portal)**.

---

## 1. System Overview & Modules

```
                                  +-----------------------------+
                                  |     data/creditcard.csv     |
                                  |  (Dataset Benchmark Source) |
                                  +--------------+--------------+
                                                 | (On-demand lookup & sampling)
                                                 v
+------------------------+        +-----------------------------+        +------------------------+
|    Customer Portal     | <----> |     Flask Backend API       | <----> |      Bank Portal       |
|  - Register / Login    | (Fetch)|  (Auth, Services, Routes)   | (Fetch)|  - Operations Dash     |
|  - Account Dashboard   |        +--------------+--------------+        |  - Dataset Browser     |
|  - Assigned Tx History |                       | (ORM Queries)         |  - Fraud Cases (CRUD)  |
|  - Feature Inspection  |                       v                       |  - Customer Directory  |
+------------------------+        +-----------------------------+        |  - Class Analytics     |
                                  |    database/trustguard.db   |        +------------------------+
                                  |      (SQLite Database)      |
                                  +-----------------------------+
```

### Module 1 &mdash; Basic Customer Portal
- User registration & session-based authentication.
- Automatically seeds a realistic sample of transactions from `creditcard.csv` to new customer accounts.
- Customer dashboard with 4 metric summary cards and recent transactions.
- Transactions list with search, status filtering, and pagination.
- Transaction feature inspection view with anonymized features $V_1..V_{28}$ and research disclaimer.

### Module 2 &mdash; Basic Bank Portal
- Role-based access control protecting bank routes and APIs (`role='BANK'`).
- Auto-seeded demo bank analyst account (`bank@trustguard.ai` / `Bank@123`).
- Bank Operations Dashboard with system-wide volume, ground truth dataset counts, customer count, and open cases.
- Dataset Transactions Browser supporting backend pagination across all 284,807 transactions with row search and class filters.
- Direct review case initiation from any dataset transaction.
- Fraud Review Case management (listing, filtering by status, viewing details, updating priority, status, investigation notes, and resolution).
- Sanitized Customer Directory (strictly no passwords or credentials exposed).
- Descriptive dataset analytics & visual charts (Chart.js) for class breakdown and case distribution.

---

## 2. Technology Stack

- **Backend**:
  - Python 3.10+
  - Flask (Modular application with Blueprints)
  - Flask-SQLAlchemy (ORM)
  - SQLite (Local database)
  - Pandas (High-performance CSV slicing & queries)
  - Werkzeug (Password hashing)
- **Frontend**:
  - HTML5 & CSS3 (Custom Fintech Theme)
  - Bootstrap 5 (Responsive Grid & Components)
  - Bootstrap Icons
  - Google Fonts (Inter)
  - Chart.js (Descriptive distribution visualization)
  - Vanilla JavaScript (`fetch()` API for all dynamic interactions)
- **Dataset**:
  - `data/creditcard.csv` (284,807 transactions with anonymized PCA features $V_1..V_{28}$, `Time`, `Amount`, `Class`).

---

## 3. Project Structure

```
trustguard-ai/
│
├── backend/
│   ├── __init__.py
│   ├── app.py                      # Flask application factory & startup hooks
│   ├── config.py                   # App configuration & paths
│   ├── database.py                 # SQLAlchemy db instance
│   ├── models.py                   # User, CustomerTransaction, FraudCase models
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── dataset_service.py      # creditcard.csv loader, pagination & features
│   │   └── seed_service.py         # Demo bank user seeding helper
│   │
│   └── routes/
│       ├── __init__.py
│       ├── customer.py             # Customer auth & dashboard routes
│       ├── transactions.py         # Customer transactions routes
│       └── bank.py                 # Bank portal pages & REST APIs
│
├── data/
│   └── creditcard.csv              # Original dataset (retained untouched)
│
├── database/
│   └── trustguard.db               # SQLite database (auto-created at runtime)
│
├── frontend/
│   ├── templates/
│   │   ├── base.html               # Shared role-aware layout & navbar
│   │   │
│   │   ├── customer_login.html     # Customer login page
│   │   ├── customer_register.html  # Customer registration page
│   │   ├── customer_dashboard.html # Customer dashboard
│   │   ├── transactions.html       # Customer transactions list
│   │   ├── transaction_details.html# Customer transaction details
│   │   │
│   │   ├── bank_login.html         # Bank login page
│   │   ├── bank_dashboard.html     # Bank operations dashboard
│   │   ├── bank_transactions.html  # Dataset browser (20/page)
│   │   ├── bank_tx_details.html    # Bank transaction inspection & case creation
│   │   ├── bank_cases.html         # Fraud review cases list
│   │   ├── bank_case_details.html  # Case editor (status, priority, notes)
│   │   ├── bank_customers.html     # Sanitized customer accounts directory
│   │   └── bank_analytics.html     # Dataset distribution chart (Chart.js)
│   │
│   └── static/
│       ├── css/
│       │   └── style.css           # Custom styling & status badges
│       └── js/
│           ├── customer.js         # Customer auth & dashboard async client
│           ├── transactions.js     # Customer transactions async client
│           └── bank.js             # Bank operations async client
│
├── tests/
│   ├── test_module1.py             # Module 1 unit & integration tests
│   └── test_module2.py             # Module 2 bank portal & RBAC tests
│
├── requirements.txt
├── README.md
└── .gitignore
```

---

## 4. Database Structure & Relationship to Dataset

### SQLite Database (`database/trustguard.db`)
SQLite holds application-generated records and state:

1. **`users` Table**:
   - `id` (INTEGER, Primary Key)
   - `name` (VARCHAR(120))
   - `email` (VARCHAR(120), Unique)
   - `password_hash` (VARCHAR(255))
   - `role` (VARCHAR(50), `'CUSTOMER'` or `'BANK'`)
   - `created_at` (DATETIME)
2. **`customer_transactions` Table**:
   - `id` (INTEGER, Primary Key)
   - `user_id` (INTEGER, Foreign Key $\rightarrow$ `users.id`)
   - `dataset_row_id` (INTEGER, index into `creditcard.csv`)
   - `amount` (FLOAT)
   - `transaction_time` (FLOAT)
   - `class_label` (INTEGER, 0 or 1)
   - `created_at` (DATETIME)
3. **`fraud_cases` Table**:
   - `id` (INTEGER, Primary Key)
   - `transaction_id` (INTEGER, index into `creditcard.csv`)
   - `created_by` (INTEGER, Foreign Key $\rightarrow$ `users.id`)
   - `status` (VARCHAR(20), `'OPEN'`, `'UNDER_REVIEW'`, `'RESOLVED'`)
   - `priority` (VARCHAR(20), `'LOW'`, `'MEDIUM'`, `'HIGH'`)
   - `notes` (TEXT)
   - `resolution` (TEXT)
   - `created_at` (DATETIME)
   - `updated_at` (DATETIME)

### Dataset Relationship
- The original 284,807 rows are **not duplicated** into SQLite.
- `creditcard.csv` serves as the benchmark dataset source.
- Applications reference transactions by their zero-indexed `dataset_row_id`. Full $V_1..V_{28}$ features are retrieved on demand in constant time via `DatasetService`.

---

## 5. Demo Credentials

| Role | Email | Password | Access Portal |
|---|---|---|---|
| **Bank Analyst (Demo)** | `bank@trustguard.ai` | `Bank@123` | `/bank/login` |
| **Customer** | *(Self-register or use registered account)* | *(Your password)* | `/customer/login` |

---

## 6. Installation & How to Run

### Windows (PowerShell / CMD)

```powershell
# 1. Activate virtual environment (optional)
python -m venv venv
venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run all automated unit and integration tests
python -m unittest discover tests

# 4. Start the application
python backend/app.py
```

The server runs at: **`http://127.0.0.1:5000`**

---

## 7. Available Pages (UI Routes)

### Customer Portal Routes
- `/customer/register` &mdash; Customer registration.
- `/customer/login` &mdash; Customer sign in.
- `/customer/dashboard` &mdash; Customer account overview.
- `/customer/transactions` &mdash; Customer transactions history.
- `/customer/transactions/<id>` &mdash; Customer transaction details.
- `/customer/logout` &mdash; Customer sign out.

### Bank Portal Routes
- `/bank/login` &mdash; Bank analyst sign in.
- `/bank/dashboard` &mdash; Bank operations dashboard.
- `/bank/transactions` &mdash; Dataset transactions browser (20 per page).
- `/bank/transactions/<row_id>` &mdash; Bank transaction inspection & case creation.
- `/bank/cases` &mdash; Fraud review cases queue.
- `/bank/cases/<case_id>` &mdash; Case investigation & resolution editor.
- `/bank/customers` &mdash; Customer directory.
- `/bank/analytics` &mdash; Dataset distribution analytics.
- `/bank/logout` &mdash; Bank analyst sign out.

---

## 8. Backend REST API Endpoints

### Customer APIs (`role='CUSTOMER'` required)
- `POST /api/customer/register`
- `POST /api/customer/login`
- `POST /api/customer/logout`
- `GET /api/customer/dashboard`
- `GET /api/customer/transactions`
- `GET /api/customer/transactions/<id>`

### Bank APIs (`role='BANK'` required)
- `POST /api/bank/login`
- `POST /api/bank/logout`
- `GET /api/bank/dashboard` &mdash; Returns aggregate dataset stats, customer count, and open cases.
- `GET /api/bank/transactions` &mdash; Paginated dataset query (`page`, `limit`, `status`, `q`).
- `GET /api/bank/transactions/<row_id>` &mdash; Full transaction features and attached review case status.
- `GET /api/bank/customers` &mdash; Sanitized customer list.
- `GET /api/bank/cases` &mdash; List of fraud review cases (`status=ALL|OPEN|UNDER_REVIEW|RESOLVED`).
- `POST /api/bank/cases` &mdash; Create a new case (`transaction_id`, `priority`, `notes`).
- `GET /api/bank/cases/<case_id>` &mdash; Fetch single case and attached transaction summary.
- `PUT /api/bank/cases/<case_id>` &mdash; Update case (`status`, `priority`, `notes`, `resolution`).
- `GET /api/bank/analytics` &mdash; Descriptive statistics for Chart.js.

---

## 9. Current Limitations & Roadmap

- **Descriptive Labels Only**: Transaction statuses reflect historical dataset ground truth labels (`0 = Normal`, `1 = Fraud`).
- **Future ML Modules**: Supervised classification models (Random Forest, XGBoost), explainable AI (SHAP), dynamic risk scoring, risk threshold simulators, and the Trust Loop customer feedback workflow will be added in subsequent modules.

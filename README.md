# TrustGuard AI

**AI-Powered Financial Security & Fraud Review Platform**

TrustGuard AI is a financial security platform designed to provide separate **Customer** and **Bank Analyst** portals for transaction monitoring, fraud review, customer management, and dataset-based analysis.

> **Current Submission:** Customer Portal + Bank Analyst Portal

---

## 🚀 Key Features

### 👤 Customer Portal

* Customer registration and secure login
* Personal account dashboard
* Transaction history with search and filtering
* Transaction details and feature inspection
* Session-based authentication

### 🏦 Bank Analyst Portal

* Role-based bank authentication
* Operations dashboard with transaction and case statistics
* Large-scale transaction dataset browser
* Transaction search, filtering, and pagination
* Fraud review case creation and management
* Case priority, status, investigation notes, and resolution
* Sanitized customer directory
* Dataset analytics and visual charts

### 🔐 Security

* Password hashing
* Session-based authentication
* Role-based access control
* Protected bank APIs and routes
* Customer credentials are not exposed through the bank portal

---

## 🏗️ System Architecture

```text
                    ┌─────────────────────────┐
                    │   Credit Card Dataset   │
                    │    284,807 Records      │
                    └────────────┬────────────┘
                                 │
                                 ▼
┌──────────────────┐     ┌─────────────────────┐     ┌──────────────────┐
│ Customer Portal  │◄───►│   Flask Backend     │◄───►│  Bank Portal     │
│                  │     │                     │     │                  │
│ • Login/Register │     │ • Authentication    │     │ • Dashboard      │
│ • Dashboard      │     │ • REST APIs         │     │ • Transactions   │
│ • Transactions   │     │ • Business Logic    │     │ • Fraud Cases    │
│ • Details        │     │ • Database Access   │     │ • Analytics      │
└──────────────────┘     └──────────┬──────────┘     └──────────────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │   SQLite Database   │
                         │ Users / Cases /     │
                         │ Application State   │
                         └─────────────────────┘
```

---

## 🛠️ Technology Stack

| Layer           | Technologies                                      |
| --------------- | ------------------------------------------------- |
| Backend         | Python, Flask, Flask-SQLAlchemy                   |
| Frontend        | HTML5, CSS3, Bootstrap 5, JavaScript              |
| Database        | SQLite                                            |
| Data Processing | Pandas                                            |
| Visualization   | Chart.js                                          |
| Security        | Werkzeug Password Hashing, Session Authentication |
| Dataset         | Credit Card Fraud Detection Dataset               |

---

## 📊 Dataset

The project uses a credit-card transaction dataset containing **284,807 transactions**.

The dataset includes:

* `Time`
* `Amount`
* `V1`–`V28` anonymized features
* `Class` — historical transaction label

The original dataset is retained separately and accessed when required rather than duplicating all records into the application database.

---

## 📁 Project Structure

```text
trustguard-ai/
│
├── backend/
│   ├── app.py
│   ├── config.py
│   ├── database.py
│   ├── models.py
│   ├── services/
│   └── routes/
│
├── frontend/
│   ├── templates/
│   └── static/
│
├── data/
│   └── creditcard.csv
│
├── database/
│   └── trustguard.db
│
├── tests/
│   ├── test_module1.py
│   └── test_module2.py
│
├── requirements.txt
├── README.md
└── .gitignore
```

---

## ⚙️ Installation & Setup

### 1. Clone the repository

```bash
git clone <YOUR-GITHUB-REPOSITORY-URL>
cd trustguard-ai
```

### 2. Create a virtual environment

**Windows:**

```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run tests

```bash
python -m unittest discover tests
```

### 5. Start the application

```bash
python backend/app.py
```

Open:

```text
http://127.0.0.1:5000
```

---

## 🔑 Demo Access

### Bank Analyst

```text
Email:    bank@trustguard.ai
Password: Bank@123
```

### Customer

Create an account using the **Customer Registration** page.

> **Note:** Demo credentials are intended for local/project demonstration only. Change or remove default credentials before production deployment.

---

## 🔄 Application Workflow

```text
Customer
   │
   ├── Register / Login
   │
   ├── View Dashboard
   │
   └── View Transactions
          │
          ▼
      Transaction Details


Bank Analyst
   │
   ├── Login
   │
   ├── View Operations Dashboard
   │
   ├── Search Transactions
   │
   ├── Inspect Transaction
   │
   ├── Create Fraud Review Case
   │
   └── Investigate → Update → Resolve Case
```

---

## 🧪 Testing

Automated unit and integration tests are included for:

* Customer authentication and portal functionality
* Transaction operations
* Bank portal functionality
* Role-based access control
* Fraud review case workflows

Run all tests with:

```bash
python -m unittest discover tests
```

---

## ⚠️ Current Scope

The current submission focuses on the **customer and bank operational workflow** using historical transaction labels from the dataset.

The current system does **not** yet provide live transaction fraud prediction or a trained machine-learning risk score.

### Planned Enhancements

* Machine-learning fraud classification
* Dynamic transaction risk scoring
* Explainable AI using SHAP
* Risk threshold simulation
* Customer feedback / Trust Loop
* Real-time transaction monitoring

---

## 🎯 Project Objective

TrustGuard AI aims to provide a structured financial-security workflow where customers can view their transaction activity while bank analysts can inspect transactions, manage fraud-review cases, and analyze historical transaction data through a unified platform.

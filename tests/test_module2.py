import unittest
import json
from backend.app import create_app
from backend.database import db
from backend.models import User, FraudCase
from backend.services.seed_service import seed_bank_user

class TestModule2(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()

        with self.app.app_context():
            seed_bank_user()

    def test_01_bank_seed_and_auth(self):
        """Test demo bank user seeding and authentication."""
        # 1. Login with demo credentials
        res = self.client.post('/api/bank/login', json={
            'email': 'bank@trustguard.ai',
            'password': 'Bank@123'
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['user']['role'], 'BANK')

        # 2. Invalid password
        res = self.client.post('/api/bank/login', json={
            'email': 'bank@trustguard.ai',
            'password': 'WrongPassword!'
        })
        self.assertEqual(res.status_code, 401)

    def test_02_role_based_access_control(self):
        """Verify customers cannot access bank APIs and unauthenticated requests are blocked."""
        # 1. Unauthenticated request to bank API
        res = self.client.get('/api/bank/dashboard')
        self.assertEqual(res.status_code, 401)

        # 2. Register and login as customer
        cust_email = "victim@trustguard.ai"
        self.client.post('/api/customer/register', json={
            'name': 'Customer User',
            'email': cust_email,
            'password': 'Password123!',
            'confirm_password': 'Password123!'
        })
        self.client.post('/api/customer/login', json={
            'email': cust_email,
            'password': 'Password123!'
        })

        # 3. Customer tries to access bank dashboard API -> must be 403 Forbidden
        res = self.client.get('/api/bank/dashboard')
        self.assertEqual(res.status_code, 403)

        # 4. Customer tries to create a fraud case -> 403 Forbidden
        res = self.client.post('/api/bank/cases', json={'transaction_id': 541})
        self.assertEqual(res.status_code, 403)

    def test_03_bank_dashboard_and_dataset_browser(self):
        """Test bank dashboard stats, dataset browser with pagination, search, and filters."""
        # Login as bank analyst
        self.client.post('/api/bank/login', json={
            'email': 'bank@trustguard.ai',
            'password': 'Bank@123'
        })

        # Dashboard
        res = self.client.get('/api/bank/dashboard')
        self.assertEqual(res.status_code, 200)
        dash = res.get_json()
        self.assertEqual(dash['total_transactions'], 284807)
        self.assertEqual(dash['fraud_transactions'], 492)
        self.assertEqual(dash['normal_transactions'], 284315)
        self.assertGreaterEqual(dash['customer_count'], 0)

        # Transactions browser - Page 1
        res = self.client.get('/api/bank/transactions?page=1&limit=20&status=all')
        self.assertEqual(res.status_code, 200)
        tx_data = res.get_json()
        self.assertEqual(len(tx_data['transactions']), 20)
        self.assertEqual(tx_data['total'], 284807)

        # Transactions browser - Filter by Fraud (Class 1)
        res = self.client.get('/api/bank/transactions?page=1&limit=20&status=1')
        self.assertEqual(res.status_code, 200)
        fraud_data = res.get_json()
        self.assertEqual(fraud_data['total'], 492)
        for tx in fraud_data['transactions']:
            self.assertEqual(tx['class_label'], 1)

        # Transactions browser - Search by Row ID 541 (known fraud transaction in dataset)
        res = self.client.get('/api/bank/transactions?q=541')
        self.assertEqual(res.status_code, 200)
        search_data = res.get_json()
        self.assertEqual(len(search_data['transactions']), 1)
        self.assertEqual(search_data['transactions'][0]['id'], 541)

        # Transaction details
        res = self.client.get('/api/bank/transactions/541')
        self.assertEqual(res.status_code, 200)
        detail = res.get_json()
        self.assertEqual(detail['dataset_row_id'], 541)
        self.assertEqual(detail['class_label'], 1)
        self.assertIn('V1', detail['features'])
        self.assertIn('V28', detail['features'])

    def test_04_fraud_case_lifecycle(self):
        """Test creating, listing, viewing, and updating a fraud review case."""
        # Login as bank analyst
        self.client.post('/api/bank/login', json={
            'email': 'bank@trustguard.ai',
            'password': 'Bank@123'
        })

        test_row_id = 541

        # 1. Clean up existing case for row 541 if any
        with self.app.app_context():
            FraudCase.query.filter_by(transaction_id=test_row_id).delete()
            db.session.commit()

        # 2. Create review case
        create_res = self.client.post('/api/bank/cases', json={
            'transaction_id': test_row_id,
            'priority': 'HIGH',
            'notes': 'High-risk anomaly observed on benchmark dataset.'
        })
        self.assertEqual(create_res.status_code, 201)
        case_data = create_res.get_json()['case']
        case_id = case_data['id']
        self.assertEqual(case_data['status'], 'OPEN')
        self.assertEqual(case_data['priority'], 'HIGH')

        # 3. Duplicate creation should fail (409 Conflict)
        dup_res = self.client.post('/api/bank/cases', json={
            'transaction_id': test_row_id,
            'priority': 'MEDIUM'
        })
        self.assertEqual(dup_res.status_code, 409)

        # 4. Fetch cases list
        list_res = self.client.get('/api/bank/cases?status=ALL')
        self.assertEqual(list_res.status_code, 200)
        cases_list = list_res.get_json()['cases']
        self.assertTrue(any(c['id'] == case_id for c in cases_list))

        # 5. Fetch single case details
        get_res = self.client.get(f'/api/bank/cases/{case_id}')
        self.assertEqual(get_res.status_code, 200)
        single_case = get_res.get_json()
        self.assertEqual(single_case['id'], case_id)
        self.assertIn('transaction', single_case)
        self.assertEqual(single_case['transaction']['dataset_row_id'], test_row_id)

        # 6. Update case to UNDER_REVIEW
        put_res = self.client.put(f'/api/bank/cases/{case_id}', json={
            'status': 'UNDER_REVIEW',
            'priority': 'HIGH',
            'notes': 'Contacted customer, waiting for confirmation.',
            'resolution': ''
        })
        self.assertEqual(put_res.status_code, 200)
        self.assertEqual(put_res.get_json()['case']['status'], 'UNDER_REVIEW')

        # 7. Update case to RESOLVED
        put_res2 = self.client.put(f'/api/bank/cases/{case_id}', json={
            'status': 'RESOLVED',
            'priority': 'HIGH',
            'notes': 'Customer confirmed unauthorized transaction. Card blocked.',
            'resolution': 'Confirmed Fraud & Chargeback Initiated'
        })
        self.assertEqual(put_res2.status_code, 200)
        self.assertEqual(put_res2.get_json()['case']['status'], 'RESOLVED')

    def test_05_customers_and_analytics_apis(self):
        """Test sanitized customer listing and analytics API endpoints."""
        # Login as bank analyst
        self.client.post('/api/bank/login', json={
            'email': 'bank@trustguard.ai',
            'password': 'Bank@123'
        })

        # Customers API
        cust_res = self.client.get('/api/bank/customers')
        self.assertEqual(cust_res.status_code, 200)
        cust_data = cust_res.get_json()
        self.assertIn('customers', cust_data)
        for c in cust_data['customers']:
            self.assertNotIn('password', c)
            self.assertNotIn('password_hash', c)

        # Analytics API
        ana_res = self.client.get('/api/bank/analytics')
        self.assertEqual(ana_res.status_code, 200)
        ana_data = ana_res.get_json()
        self.assertEqual(ana_data['total_transactions'], 284807)
        self.assertAlmostEqual(ana_data['fraud_percentage'], 0.173, places=2)
        self.assertIn('case_stats', ana_data)


if __name__ == '__main__':
    unittest.main()

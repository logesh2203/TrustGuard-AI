import unittest
import os
import json
import csv
import io
from backend.app import create_app
from backend.database import db
from backend.models import User, CustomerTransaction, FraudCase, compute_risk_level
from backend.config import TestConfig

class TestLevel2Features(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        test_db = os.path.join(TestConfig.DATABASE_DIR, 'test_trustguard.db')
        if os.path.exists(test_db):
            try:
                os.remove(test_db)
            except OSError:
                pass

    @classmethod
    def tearDownClass(cls):
        test_db = os.path.join(TestConfig.DATABASE_DIR, 'test_trustguard.db')
        if os.path.exists(test_db):
            try:
                os.remove(test_db)
            except OSError:
                pass

    def setUp(self):
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()

    def test_01_deterministic_risk_level_computation(self):
        """Test compute_risk_level helper function with various transaction states."""
        # Class 1 ground truth fraud -> always HIGH
        self.assertEqual(compute_risk_level(class_label=1, amount=5.00), 'HIGH')
        
        # Case priority CRITICAL or HIGH -> always HIGH
        self.assertEqual(compute_risk_level(class_label=0, amount=20.00, case_priority='CRITICAL'), 'HIGH')
        self.assertEqual(compute_risk_level(class_label=0, amount=20.00, case_priority='HIGH'), 'HIGH')

        # Large amount (>= 500) -> MEDIUM
        self.assertEqual(compute_risk_level(class_label=0, amount=500.00), 'MEDIUM')
        self.assertEqual(compute_risk_level(class_label=0, amount=1200.00), 'MEDIUM')

        # Open or Under Review case on normal transaction -> MEDIUM
        self.assertEqual(compute_risk_level(class_label=0, amount=50.00, case_status='OPEN'), 'MEDIUM')
        self.assertEqual(compute_risk_level(class_label=0, amount=50.00, case_status='UNDER_REVIEW'), 'MEDIUM')

        # Normal small transaction with no active investigation -> LOW
        self.assertEqual(compute_risk_level(class_label=0, amount=49.99), 'LOW')
        self.assertEqual(compute_risk_level(class_label=0, amount=10.00, case_status='RESOLVED'), 'LOW')

    def test_02_customer_report_suspicious_flow(self):
        """Test customer reporting a suspicious transaction and creating an automated bank case."""
        cust_email = "reporter@trustguard.ai"
        
        # 1. Register & Login customer
        self.client.post('/api/customer/register', json={
            'name': 'Reporter User',
            'email': cust_email,
            'password': 'SecurePassword123!',
            'confirm_password': 'SecurePassword123!'
        })
        login_res = self.client.post('/api/customer/login', json={
            'email': cust_email,
            'password': 'SecurePassword123!'
        })
        self.assertEqual(login_res.status_code, 200)

        # 2. Get a customer transaction
        txs_res = self.client.get('/api/customer/transactions?page=1&per_page=5')
        self.assertEqual(txs_res.status_code, 200)
        tx_list = txs_res.get_json()['transactions']
        self.assertGreater(len(tx_list), 0)
        target_tx = tx_list[0]
        tx_id = target_tx['id']

        # 3. Report the transaction
        report_res = self.client.post(f'/api/customer/transactions/{tx_id}/report', json={
            'reason': 'Unrecognized transaction at midnight from foreign merchant.'
        })
        self.assertEqual(report_res.status_code, 201)
        rep_data = report_res.get_json()
        self.assertTrue(rep_data['success'])
        self.assertEqual(rep_data['status'], 'Reported')
        case_id = rep_data['case']['id']

        # 4. Duplicate report should return 409 Conflict
        dup_res = self.client.post(f'/api/customer/transactions/{tx_id}/report', json={
            'reason': 'Second attempt'
        })
        self.assertEqual(dup_res.status_code, 409)

        # 5. Customer transaction detail now reflects 'Reported' and links to case
        detail_res = self.client.get(f'/api/customer/transactions/{tx_id}')
        self.assertEqual(detail_res.status_code, 200)
        detail_data = detail_res.get_json()
        self.assertEqual(detail_data['status'], 'Reported')
        self.assertTrue(detail_data['is_reported'])
        self.assertEqual(detail_data['case_id'], case_id)

    def test_03_advanced_filters_and_pagination(self):
        """Test min/max amount and risk filters for customer and bank endpoints."""
        # 1. Bank Login
        self.client.post('/api/bank/login', json={
            'email': 'bank@trustguard.ai',
            'password': 'Bank@123'
        })

        # Test Bank transactions amount range filter
        res = self.client.get('/api/bank/transactions?min_amount=100&max_amount=200&limit=10')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        for tx in data['transactions']:
            self.assertGreaterEqual(tx['amount'], 100.0)
            self.assertLessEqual(tx['amount'], 200.0)

        # Test Bank transactions risk filter (HIGH)
        res_high = self.client.get('/api/bank/transactions?risk=HIGH&limit=10')
        self.assertEqual(res_high.status_code, 200)
        data_high = res_high.get_json()
        for tx in data_high['transactions']:
            self.assertEqual(tx['risk_level'], 'HIGH')

    def test_04_fraud_alert_center_api(self):
        """Test /api/bank/alerts returns aggregated high-risk alerts and customer reports."""
        self.client.post('/api/bank/login', json={
            'email': 'bank@trustguard.ai',
            'password': 'Bank@123'
        })

        res = self.client.get('/api/bank/alerts')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('alerts', data)
        self.assertIn('total_alerts', data)
        self.assertIn('high_risk_count', data)
        self.assertIn('customer_reported_count', data)
        self.assertGreater(data['total_alerts'], 0)

        # Alerts should have risk badges and status
        first_alert = data['alerts'][0]
        self.assertIn('risk_level', first_alert)
        self.assertIn('priority', first_alert)
        self.assertIn('status', first_alert)

    def test_05_critical_priority_and_timeline(self):
        """Test creating/updating a case with CRITICAL priority and inspect timeline events."""
        self.client.post('/api/bank/login', json={
            'email': 'bank@trustguard.ai',
            'password': 'Bank@123'
        })

        # Create case with CRITICAL priority
        create_res = self.client.post('/api/bank/cases', json={
            'transaction_id': 9999,
            'priority': 'CRITICAL',
            'notes': 'High volume transaction with anomalous pattern.'
        })
        self.assertEqual(create_res.status_code, 201)
        case_id = create_res.get_json()['case']['id']

        # Get case details and verify timeline
        get_res = self.client.get(f'/api/bank/cases/{case_id}')
        self.assertEqual(get_res.status_code, 200)
        case_data = get_res.get_json()
        self.assertEqual(case_data['priority'], 'CRITICAL')
        self.assertIn('timeline', case_data)
        self.assertGreater(len(case_data['timeline']), 0)
        first_event = case_data['timeline'][0]
        self.assertIn('title', first_event)
        self.assertIn('timestamp', first_event)

        # Update case to RESOLVED
        update_res = self.client.put(f'/api/bank/cases/{case_id}', json={
            'status': 'RESOLVED',
            'priority': 'CRITICAL',
            'notes': 'Verified with client and account secured.',
            'resolution': 'Confirmed security hold applied.'
        })
        self.assertEqual(update_res.status_code, 200)
        updated_data = update_res.get_json()['case']
        self.assertEqual(updated_data['status'], 'RESOLVED')
        self.assertEqual(len(updated_data['timeline']), 3)

    def test_06_csv_export_endpoints(self):
        """Test streaming CSV export for transactions and cases."""
        self.client.post('/api/bank/login', json={
            'email': 'bank@trustguard.ai',
            'password': 'Bank@123'
        })

        # 1. Export Transactions CSV
        tx_export_res = self.client.get('/api/bank/transactions/export?status=1&limit=25')
        self.assertEqual(tx_export_res.status_code, 200)
        self.assertIn('text/csv', tx_export_res.content_type)
        self.assertIn('attachment; filename=trustguard_transactions_export.csv', tx_export_res.headers.get('Content-Disposition', ''))
        
        csv_text = tx_export_res.data.decode('utf-8')
        reader = list(csv.reader(io.StringIO(csv_text)))
        self.assertGreater(len(reader), 1)
        headers = reader[0]
        self.assertIn('Row_ID', headers)
        self.assertIn('Amount_USD', headers)
        self.assertIn('Risk_Level', headers)

        # 2. Export Cases CSV
        case_export_res = self.client.get('/api/bank/cases/export')
        self.assertEqual(case_export_res.status_code, 200)
        self.assertIn('text/csv', case_export_res.content_type)
        self.assertIn('attachment; filename=trustguard_fraud_cases_export.csv', case_export_res.headers.get('Content-Disposition', ''))
        case_csv_text = case_export_res.data.decode('utf-8')
        case_reader = list(csv.reader(io.StringIO(case_csv_text)))
        self.assertGreater(len(case_reader), 1)
        case_headers = case_reader[0]
        self.assertIn('Case_ID', case_headers)
        self.assertIn('Status', case_headers)
        self.assertIn('Priority', case_headers)

import unittest
import os
import json
from backend.app import create_app
from backend.database import db
from backend.models import User, CustomerTransaction
from backend.services.dataset_service import DatasetService
from backend.config import Config

class TestModule1(unittest.TestCase):
    def setUp(self):
        # Configure app for testing
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()

    def test_01_dataset_service(self):
        """Test dataset loading and column validation."""
        self.assertTrue(DatasetService.is_dataset_available(), "creditcard.csv should exist")
        df = DatasetService.load_dataset()
        self.assertIn('Time', df.columns)
        self.assertIn('Amount', df.columns)
        self.assertIn('Class', df.columns)
        self.assertIn('V1', df.columns)
        self.assertIn('V28', df.columns)
        
        # Test sample generation
        samples = DatasetService.get_sample_transactions_for_user(normal_count=5, fraud_count=2)
        self.assertEqual(len(samples), 7)
        normal_samples = [s for s in samples if s['class_label'] == 0]
        fraud_samples = [s for s in samples if s['class_label'] == 1]
        self.assertEqual(len(normal_samples), 5)
        self.assertEqual(len(fraud_samples), 2)

        # Test feature retrieval
        feat = DatasetService.get_transaction_features(samples[0]['dataset_row_id'])
        self.assertIsNotNone(feat)
        self.assertIn('V1', feat['features'])
        self.assertIn('V28', feat['features'])

    def test_02_customer_registration_and_login_flow(self):
        """Test registration, auto-seeding of transactions, and login."""
        test_email = "testuser@trustguard.ai"
        
        # 1. Register
        reg_payload = {
            "name": "Jane Test",
            "email": test_email,
            "password": "SecurePassword123!",
            "confirm_password": "SecurePassword123!"
        }
        res = self.client.post('/api/customer/register', json=reg_payload)
        self.assertIn(res.status_code, [201, 409]) # 201 if new, 409 if already registered

        # 2. Login
        login_payload = {
            "email": test_email,
            "password": "SecurePassword123!"
        }
        res = self.client.post('/api/customer/login', json=login_payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['user']['email'], test_email)

        # 3. Dashboard API
        res = self.client.get('/api/customer/dashboard')
        self.assertEqual(res.status_code, 200)
        dash_data = res.get_json()
        self.assertGreater(dash_data['total_transactions'], 0)
        self.assertGreater(dash_data['normal_transactions'], 0)
        self.assertGreater(dash_data['fraud_transactions'], 0)
        self.assertEqual(len(dash_data['recent_transactions']), min(5, dash_data['total_transactions']))

        # 4. Transactions List API
        res = self.client.get('/api/customer/transactions?page=1&per_page=10&status=all')
        self.assertEqual(res.status_code, 200)
        tx_data = res.get_json()
        self.assertGreater(len(tx_data['transactions']), 0)
        tx_id = tx_data['transactions'][0]['id']

        # 5. Transaction Details API
        res = self.client.get(f'/api/customer/transactions/{tx_id}')
        self.assertEqual(res.status_code, 200)
        detail_data = res.get_json()
        self.assertEqual(detail_data['id'], tx_id)
        self.assertIn('features', detail_data)
        self.assertIn('V1', detail_data['features'])
        self.assertIn('V28', detail_data['features'])
        self.assertIn('dataset_info', detail_data)

        # 6. Logout API
        res = self.client.post('/api/customer/logout')
        self.assertEqual(res.status_code, 200)

        # 7. Verify protected route is unauthorized after logout
        res = self.client.get('/api/customer/dashboard')
        self.assertEqual(res.status_code, 401)


if __name__ == '__main__':
    unittest.main()

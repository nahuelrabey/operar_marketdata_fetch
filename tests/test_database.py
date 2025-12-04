import unittest
import os
import sqlite3
from src import database

class TestDatabase(unittest.TestCase):
    def setUp(self):
        # Use a temporary database for testing
        self.test_db = "test_market_data.db"
        database.DB_PATH = self.test_db
        database.initialize_db()

    def tearDown(self):
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    def test_create_position(self):
        pos_id = database.create_position("Test Strat", "Description")
        self.assertGreater(pos_id, 0)
        
        positions = database.get_positions()
        self.assertEqual(len(positions), 1)
        self.assertEqual(positions[0]['name'], "Test Strat")

    def test_add_operation(self):
        pos_id = database.create_position("Test Strat", "")
        
        # Create contract first (FK constraint)
        contract = {
            'symbol': 'GGALC2600',
            'underlying_symbol': 'GGAL',
            'type': 'Call',
            'expiration_date': '2025-12-19',
            'strike': 2600.0,
            'description': 'Call GGAL 2600'
        }
        database.upsert_contract(contract)
        
        op_data = {
            'contract_symbol': 'GGALC2600',
            'operation_type': 'BUY',
            'quantity': 10,
            'price': 100.0,
            'operation_date': '2025-12-04'
        }
        
        op_id = database.add_operation(pos_id, op_data)
        self.assertGreater(op_id, 0)
        
        details = database.get_position_details(pos_id)
        self.assertEqual(len(details['operations']), 1)
        self.assertEqual(details['composition'][0]['net_quantity'], 10)

if __name__ == '__main__':
    unittest.main()

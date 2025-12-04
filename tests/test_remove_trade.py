import unittest
import os
import sys

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import database

class TestRemoveTrade(unittest.TestCase):
    def setUp(self):
        self.db_path = 'test_remove_trade.db'
        database.DB_PATH = self.db_path
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        database.initialize_db()

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_remove_operation_from_position(self):
        # 1. Create Position
        pos_id = database.create_position("Test Strat", "Desc")
        
        # 2. Add Operation
        op_data = {
            'contract_symbol': 'GGALC2600',
            'operation_type': 'BUY',
            'quantity': 10,
            'price': 5.0,
            'operation_date': '2025-12-04'
        }
        op_id = database.add_operation(pos_id, op_data)
        
        # Verify added
        details = database.get_position_details(pos_id)
        self.assertEqual(len(details['operations']), 1)
        
        # 3. Remove Operation
        result = database.remove_operation_from_position(pos_id, op_id)
        self.assertTrue(result)
        
        # Verify removed
        details_after = database.get_position_details(pos_id)
        self.assertEqual(len(details_after['operations']), 0)

if __name__ == '__main__':
    unittest.main()

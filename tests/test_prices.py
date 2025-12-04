import unittest
import os
import sys
from datetime import datetime

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import database

class TestPrices(unittest.TestCase):
    def setUp(self):
        # Use a temporary database
        self.db_path = 'test_market_data.db'
        database.DB_PATH = self.db_path
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        database.initialize_db()

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_get_latest_prices_by_underlying(self):
        # Setup data
        symbol = "GGAL"
        contract_c = {
            "symbol": "GGALC2600",
            "underlying_symbol": symbol,
            "type": "Call",
            "expiration_date": "2025-12-19",
            "strike": 2600.0,
            "description": "Call GGAL 2600"
        }
        contract_p = {
            "symbol": "GGALV2600",
            "underlying_symbol": symbol,
            "type": "Put",
            "expiration_date": "2025-12-19",
            "strike": 2600.0,
            "description": "Put GGAL 2600"
        }
        
        database.upsert_contract(contract_c)
        database.upsert_contract(contract_p)
        
        # Insert prices (old and new)
        price_old = {
            "contract_symbol": "GGALC2600",
            "price": 10.0,
            "broker_timestamp": "2025-12-04 10:00:00",
            "system_timestamp": "2025-12-04 10:00:00",
            "volume": 100
        }
        price_new = {
            "contract_symbol": "GGALC2600",
            "price": 12.0,
            "broker_timestamp": "2025-12-04 11:00:00",
            "system_timestamp": "2025-12-04 11:00:00",
            "volume": 150
        }
        price_put = {
            "contract_symbol": "GGALV2600",
            "price": 5.0,
            "broker_timestamp": None,
            "system_timestamp": "2025-12-04 11:00:00",
            "volume": 50
        }
        
        database.insert_market_price(price_old)
        database.insert_market_price(price_new)
        database.insert_market_price(price_put)
        
        # Test
        results = database.get_latest_prices_by_underlying(symbol)
        
        self.assertEqual(len(results), 2)
        
        # Check Call (should be latest price)
        call_res = next(r for r in results if r['symbol'] == "GGALC2600")
        self.assertEqual(call_res['price'], 12.0)
        self.assertEqual(call_res['timestamp'], "2025-12-04 11:00:00")
        
        # Check Put
        put_res = next(r for r in results if r['symbol'] == "GGALV2600")
        self.assertEqual(put_res['price'], 5.0)

if __name__ == '__main__':
    unittest.main()

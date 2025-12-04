import unittest
import numpy as np
from src import pnl

class TestPnL(unittest.TestCase):
    def test_calculate_pnl(self):
        ops = [
            {'contract_symbol': 'A', 'operation_type': 'BUY', 'quantity': 10, 'price': 100},
            {'contract_symbol': 'B', 'operation_type': 'SELL', 'quantity': 5, 'price': 50}
        ]
        prices = {'A': 110, 'B': 40} # A: +100, B: +50 (Short 50->40 is gain)
        
        total, vec = pnl.calculate_pnl(ops, prices)
        self.assertEqual(total, 150.0)
        np.testing.assert_array_equal(vec, np.array([100.0, 50.0]))

    def test_calculate_pnl_curve(self):
        ops = [
            {'strike': 100, 'contract_type': 'Call', 'operation_type': 'BUY', 'quantity': 1, 'price': 5}
        ]
        # At expiration:
        # If price = 110, Payoff = 10, P&L = 10 - 5 = 5
        # If price = 100, Payoff = 0, P&L = -5
        
        S_T, curve = pnl.calculate_pnl_curve_at_finish(ops, 100, range_pct=0.1, steps=3)
        # S_T will be [90, 100, 110]
        
        expected_curve = np.array([-5.0, -5.0, 5.0])
        np.testing.assert_allclose(curve, expected_curve, atol=0.1)

if __name__ == '__main__':
    unittest.main()

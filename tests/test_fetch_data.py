import unittest
from unittest.mock import patch, MagicMock
from src import fetch_data

class TestFetchData(unittest.TestCase):
    @patch('src.fetch_data.requests.get')
    @patch('src.fetch_data._save_raw_data')
    def test_fetch_option_chain(self, mock_save, mock_get):
        # Mock API response
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                "simbolo": "GGALC2600",
                "simboloSubyacente": "GGAL",
                "tipoOpcion": "Call",
                "fechaVencimiento": "2025-12-19T00:00:00",
                "descripcion": "Call GGAL 2,600.00 Vencimiento",
                "cotizacion": {
                    "ultimoPrecio": 100.0,
                    "fechaHora": "2025-12-04T10:00:00",
                    "volumenNominal": 500
                }
            }
        ]
        mock_get.return_value = mock_response
        
        contracts, prices = fetch_data.fetch_option_chain("GGAL", "fake_token")
        
        self.assertEqual(len(contracts), 1)
        self.assertEqual(contracts[0]['symbol'], "GGALC2600")
        self.assertEqual(contracts[0]['strike'], 2600.0)
        
        self.assertEqual(len(prices), 1)
        self.assertEqual(prices[0]['price'], 100.0)
        self.assertEqual(prices[0]['broker_timestamp'], "2025-12-04T10:00:00")

    def test_extract_strike(self):
        desc = "Call GGAL 2,654.90 Vencimiento"
        strike = fetch_data._extract_strike_from_description(desc)
        self.assertEqual(strike, 2654.90)
        
        desc2 = "Put GGAL 3000 Vencimiento"
        strike2 = fetch_data._extract_strike_from_description(desc2)
        self.assertEqual(strike2, 3000.0)

if __name__ == '__main__':
    unittest.main()

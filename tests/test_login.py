import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from login import authenticate

class TestLogin(unittest.TestCase):

    @patch('login.requests.post')
    @patch('login.open') # Mock file opening
    def test_authenticate_success(self, mock_open, mock_post):
        # Mock successful API response
        mock_response = MagicMock()
        mock_response.json.return_value = {'access_token': 'fake_token_123'}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        # Mock file writing
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        token = authenticate('user', 'pass')
        self.assertEqual(token, 'fake_token_123')
        
        # Verify correct API call
        mock_post.assert_called_with(
            "https://api.invertironline.com/token",
            data={'username': 'user', 'password': 'pass', 'grant_type': 'password'}
        )
        
        # Verify token saved
        mock_file.write.assert_called_with('fake_token_123')

    @patch('login.requests.post')
    def test_authenticate_failure(self, mock_post):
        # Mock failed API response
        import requests
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("HTTP Error")
        mock_post.return_value = mock_response

        with self.assertRaises(Exception) as cm:
            authenticate('user', 'pass')
        
        self.assertIn("Authentication failed", str(cm.exception))

if __name__ == '__main__':
    unittest.main()

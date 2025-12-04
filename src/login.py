import requests
import os
import json

API_URL = "https://api.invertironline.com/token"

def authenticate(username: str, password: str) -> str:
    """
    Authenticates against the Invertir Online API.
    Stores the token in 'token.txt' in the root directory.
    Returns the access token.
    """
    payload = {
        'username': username,
        'password': password,
        'grant_type': 'password'
    }
    
    try:
        response = requests.post(API_URL, data=payload)
        response.raise_for_status()
        
        data = response.json()
        access_token = data.get('access_token')
        
        if not access_token:
            raise Exception("Token not found in response")
            
        # Save token to file
        root_dir = os.path.dirname(os.path.dirname(__file__))
        token_path = os.path.join(root_dir, 'token.txt')
        
        with open(token_path, 'w') as f:
            f.write(access_token)
            
        return access_token
        
    except requests.exceptions.RequestException as e:
        raise Exception(f"Authentication failed: {str(e)}")
    except Exception as e:
        raise Exception(f"An error occurred during login: {str(e)}")

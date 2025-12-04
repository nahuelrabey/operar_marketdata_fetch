import requests
import pandas as pd
import datetime
import os
import tkinter as tk
from tkinter import messagebox
from tkinter import messagebox
from login import get_user_credentials

from tkinter import simpledialog

def get_stock_symbol_ui():
    """
    Opens a dialog to get the stock symbol from the user.
    Uses simpledialog to avoid creating a second root window.
    """
    # If a root window already exists (which it does in interface.py), 
    # simpledialog will use it. If not, we might need a temporary one, 
    # but for now we assume this is called from interface.py
    
    symbol = simpledialog.askstring("Fetch Option Chain", "Stock Symbol (e.g. GGAL):")
    return symbol

def fetch_option_chain(token, symbol):
    """
    Fetches the option chain for a given stock symbol from Invertir Online API.
    """
    # Note: This endpoint is based on the assumption in the plan. 
    # It might need adjustment based on actual API behavior.
    url = f"https://api.invertironline.com/api/v2/bCBA/Titulos/{symbol}/Opciones"
    headers = {'Authorization': f'Bearer {token}'}
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error fetching options: {e}")
        if response.content:
            print(f"Response content: {response.content.decode()}")
        return None
    except Exception as e:
        print(f"Error fetching options: {e}")
        return None

def get_token_from_file():
    """
    Reads the authentication token from token.txt.
    """
    try:
        if os.path.exists('token.txt'):
            with open('token.txt', 'r') as f:
                return f.read().strip()
    except Exception as e:
        print(f"Error reading token file: {e}")
    return None

def save_to_csv(data, symbol):
    """
    Saves the option chain data to a CSV file using pandas.
    Extracts symbol, last_price, and date.
    """
    if not data:
        print("No data to save.")
        return

    # Create data directory if it doesn't exist
    if not os.path.exists('data'):
        os.makedirs('data')

    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    filename = f"data/{symbol}_option_chain_{date_str}.csv"

    parsed_data = []
    for item in data:
        try:
            option_symbol = item.get('simbolo')
            cotizacion = item.get('cotizacion', {})
            last_price = cotizacion.get('ultimoPrecio')
            date_time = cotizacion.get('fechaHora')
            
            parsed_data.append({
                'symbol': option_symbol,
                'last_price': last_price,
                'date': date_time
            })
        except Exception as e:
            print(f"Error parsing item: {e}")

    try:
        df = pd.DataFrame(parsed_data)
        # Ensure columns are in the correct order
        df = df[['symbol', 'last_price', 'date']]
        df.to_csv(filename, index=False)
        print(f"Data saved to {filename}")
    except Exception as e:
        print(f"Error saving to CSV: {e}")

if __name__ == "__main__":
    # For testing purposes only
    print("Starting FetchData module (Test Mode)...")
    
    token = get_token_from_file()
    if not token:
        print("Token not found.")
        exit()
        
    symbol = get_stock_symbol_ui()
    if symbol:
        data = fetch_option_chain(token, symbol)
        if data:
            save_to_csv(data, symbol)

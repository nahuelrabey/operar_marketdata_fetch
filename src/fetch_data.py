import requests
import json
import csv
import os
import re
from datetime import datetime
from typing import List, Dict, Any, Tuple
from .database import ContractData, PriceData

# API Configuration
BASE_URL = "https://api.invertironline.com/api/v2"

def fetch_option_chain(symbol: str, token: str) -> Tuple[List[ContractData], List[PriceData]]:
    """
    Fetches the option chain for a given underlying symbol.
    Saves raw data to 'data/' folder.
    Returns parsed ContractData and PriceData lists.
    """
    url = f"{BASE_URL}/bCBA/Titulos/{symbol}/Opciones"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        # Save raw data
        _save_raw_data(symbol, data)
        
        # Parse data
        contracts = []
        prices = []
        system_timestamp = datetime.now().isoformat()
        
        for item in data:
            # Parse Contract
            contract = _parse_contract(item)
            contracts.append(contract)
            
            # Parse Price
            price = _parse_price(item, system_timestamp)
            prices.append(price)
            
        return contracts, prices
        
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to fetch data: {str(e)}")
    except Exception as e:
        raise Exception(f"Error processing data: {str(e)}")

def _save_raw_data(symbol: str, data: List[Dict[str, Any]]) -> None:
    """Saves the raw JSON response to a file."""
    root_dir = os.path.dirname(os.path.dirname(__file__))
    data_dir = os.path.join(root_dir, 'data')
    os.makedirs(data_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{symbol}_option_chain_{timestamp}.json"
    filepath = os.path.join(data_dir, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

def _parse_contract(item: Dict[str, Any]) -> ContractData:
    """Maps API item to ContractData."""
    description = item.get('descripcion', '')
    strike = _extract_strike_from_description(description)
    
    return {
        'symbol': item.get('simbolo'),
        'underlying_symbol': item.get('simboloSubyacente'),
        'type': item.get('tipoOpcion'), # "Call" or "Put"
        'expiration_date': item.get('fechaVencimiento'),
        'strike': strike,
        'description': description
    }

def _parse_price(item: Dict[str, Any], system_timestamp: str) -> PriceData:
    """Maps API item to PriceData."""
    cotizacion = item.get('cotizacion', {})
    broker_timestamp = cotizacion.get('fechaHora')
    
    # Handle invalid timestamp
    if broker_timestamp and broker_timestamp.startswith("0001-01-01"):
        broker_timestamp = None
        
    return {
        'contract_symbol': item.get('simbolo'),
        'price': cotizacion.get('ultimoPrecio', 0.0),
        'broker_timestamp': broker_timestamp,
        'system_timestamp': system_timestamp,
        'volume': cotizacion.get('volumenNominal', 0)
    }

def _extract_strike_from_description(description: str) -> float:
    """
    Extracts strike price from description.
    Example: "Call GGAL 2,654.90 Vencimiento..." -> 2654.90
    """
    try:
        # Regex to find the number after the symbol (assuming format "Type Symbol Strike ...")
        # This is a heuristic. A more robust way might be needed if descriptions vary wildly.
        # Looking for a number with optional commas and decimals
        
        # Split by spaces
        parts = description.split()
        
        # Usually the strike is the 3rd element: "Call", "GGAL", "2,654.90"
        if len(contracts := [p for p in parts if re.match(r'^(\d{1,3}(,\d{3})*|\d+)(\.\d+)?$', p)]) > 0:
             # Take the first number found that looks like a strike (not a date)
             # But wait, dates are usually dd/mm/yyyy.
             
             # Let's try to find the specific pattern
             for part in parts:
                 # Remove commas to check if it's a number
                 clean_part = part.replace(',', '')
                 if clean_part.replace('.', '', 1).isdigit():
                     return float(clean_part)
                     
        return 0.0
    except:
        return 0.0

import requests
import json
import csv
import os
import re
from datetime import datetime
from typing import List, Dict, Any, Tuple
from src.type_definitions import ContractData, PriceData

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
    description = item.get('descripcionTitulo') or item.get('descripcion', '')
    
    # Try to extract fields from description if not present in item (common for single title fetch)
    parsed = _parse_description(description)
    
    return {
        'symbol': item.get('simbolo'),
        'underlying_symbol': item.get('simboloSubyacente') or parsed['underlying'],
        'type': item.get('tipoOpcion') or parsed['type'], 
        'expiration_date': item.get('fechaVencimiento') or parsed['expiration'],
        'strike': parsed['strike'],
        'description': description
    }

def _parse_description(description: str) -> Dict[str, Any]:
    """
    Parses 'Call GGAL 10,177.00 Vencimiento: 19/12/2025'
    """
    if not description:
        return {'type': None, 'underlying': None, 'strike': 0.0, 'expiration': None}
        
    parts = description.split()
    # Expecting: Type Underlying Strike ... Vencimiento: Date
    
    op_type = parts[0] if len(parts) > 0 else None
    underlying = parts[1] if len(parts) > 1 else None
    
    # Strike extraction (improved)
    strike = 0.0
    if len(parts) > 2:
        try:
             # Handle 10,177.00 -> 10177.00
             # Handle 10.177,00 (if locale differs, but API usually sends english/dot decimal or specific fmt)
             # Based on previous JSON, it was "10,177.00" (comma thousands, dot decimal)
             strike_str = parts[2].replace(',', '') 
             strike = float(strike_str)
        except:
             # Fallback to regex search if strict position fails
             strike = _extract_strike_from_description(description)

    # Expiration Date
    expiration = None
    if "Vencimiento:" in parts:
        try:
            date_idx = parts.index("Vencimiento:") + 1
            if date_idx < len(parts):
                date_str = parts[date_idx]
                # Parse dd/mm/yyyy
                dt = datetime.strptime(date_str, "%d/%m/%Y")
                expiration = dt.isoformat()
        except:
            pass
            
    return {
        'type': op_type,
        'underlying': underlying,
        'strike': strike,
        'expiration': expiration
    }

def _parse_price(item: Dict[str, Any], system_timestamp: str) -> PriceData:
    """Maps API item to PriceData."""
    # Handle both structures: nested 'cotizacion' or top-level fields
    cotizacion = item.get('cotizacion', item) 
    
    # For single title, price fields are top level in 'item' (except fechaHora might be top level too)
    # But wait, looking at user JSON example:
    # "cotizacion": { ... } is NOT in the new JSON?
    # Actually the user JSON shows keys like "ultimoPrecio", "fechaHora" at ROOT level.
    # So we need to handle that.
    
    price = cotizacion.get('ultimoPrecio', 0.0)
    broker_timestamp = cotizacion.get('fechaHora')
    volume = int(cotizacion.get('volumenNominal', 0))
    
    # Check if we should look at root if not found in cotizacion
    if 'ultimoPrecio' in item and price == 0.0:
         price = item.get('ultimoPrecio', 0.0)
    if 'fechaHora' in item and not broker_timestamp:
         broker_timestamp = item.get('fechaHora')
    if 'volumenNominal' in item and volume == 0:
         volume = int(item.get('volumenNominal', 0))

    
    # Handle invalid timestamp
    if broker_timestamp and broker_timestamp.startswith("0001-01-01"):
        broker_timestamp = None
        
    return {
        'contract_symbol': item.get('simbolo'),
        'price': price,
        'broker_timestamp': broker_timestamp,
        'system_timestamp': system_timestamp,
        'volume': volume
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

def fetch_contract_data(symbol: str, token: str) -> Tuple[ContractData, PriceData]:
    """
    Fetches detailed information for a specific contract symbol.
    Returns both contract details and current market price data.
    """
    url = f"{BASE_URL}/bCBA/Titulos/{symbol}"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        # Parse Contract
        contract = _parse_contract(data)
        
        # Parse Price
        system_timestamp = datetime.now().isoformat()
        price = _parse_price(data, system_timestamp)
        
        return contract, price
        
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to fetch data for {symbol}: {str(e)}")
    except Exception as e:
        raise Exception(f"Error processing data for {symbol}: {str(e)}")

def process_symbols_list(file_path: str, token: str) -> None:
    """
    Reads symbols from a JSON file and updates the database with their details.
    """
    from src.database import upsert_contract, insert_market_price
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            symbols = json.load(f)
            
        print(f"Found {len(symbols)} symbols to process.")
        
        for symbol in symbols:
            try:
                print(f"Fetching data for {symbol}...")
                contract_data, price_data = fetch_contract_data(symbol, token)
                
                # Update Contract
                upsert_contract(contract_data)
                
                # Insert Price
                insert_market_price(price_data)
                
                print(f"Successfully updated {symbol}.")
            except Exception as e:
                print(f"Error processing {symbol}: {e}")
                
    except Exception as e:
        raise Exception(f"Failed to process symbols list: {e}")


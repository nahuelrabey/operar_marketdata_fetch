import requests
import json
import csv
import os
import re
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.type_definitions import ContractData, PriceData, LatestPriceData
from src.database import (
    upsert_contract, 
    insert_market_price, 
    get_all_contract_symbols, 
    insert_market_prices_batch, 
    upsert_latest_prices_batch
)

# API Configuration
BASE_URL = "https://api.invertironline.com/api/v2"

def fetch_option_chain(symbol: str, token: str) -> Tuple[List[ContractData], List[PriceData]]:
    """
    Fetches the full option chain for a given underlying symbol.

    This function makes a single API call to 'Opciones', saves the raw JSON response 
    to the 'data/' folder, and parses the response into contracts and prices.

    Args:
        symbol: The underlying symbol (e.g. 'GGAL').
        token: Valid IOL Access Token.

    Returns:
        A tuple containing a list of ContractData and a list of PriceData.

    Raises:
        Exception: If the API request fails or parsing errors occur.
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
    Parses a description string to extract metadata.
    
    Example: 'Call GGAL 10,177.00 Vencimiento: 19/12/2025'

    Args:
        description: The raw description string.

    Returns:
        Dict with keys: type, underlying, strike, expiration.
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
    Extracts strike price from description using heuristics.
    
    Example: "Call GGAL 2,654.90 Vencimiento..." -> 2654.90

    Args:
        description: The description string.

    Returns:
        The extracted strike price or 0.0 if not found.
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

    Args:
        symbol: The contract symbol (e.g. 'GGALC4600O').
        token: Access Token.

    Returns:
        Tuple of (ContractData, PriceData).

    Raises:
        Exception: If fetch fails.
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

    Args:
        file_path: Path to the JSON file containing a list of strings.
        token: Access Token.
    """
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


def fetch_historical_prices(symbol: str, date_from: datetime, date_to: datetime, token: str) -> List[PriceData]:
    """
    Fetches historical price series for a symbol.
    
    Endpoint: `/api/v2/bCBA/Titulos/{symbol}/Cotizacion/seriehistorica/{date_from}/{date_to}/sinAjustar`

    Args:
        symbol: Contract symbol.
        date_from: Start date object.
        date_to: End date object.
        token: Access Token.

    Returns:
        List of PriceData objects representing the history.
    """
    fmt = "%Y-%m-%d"
    
    str_from = date_from.strftime(fmt)
    str_to = date_to.strftime(fmt)
    
    url = f"{BASE_URL}/bCBA/Titulos/{symbol}/Cotizacion/seriehistorica/{str_from}/{str_to}/sinAjustar"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        prices = []
        system_timestamp = datetime.now().isoformat()
        
        for item in data:
            if 'ultimoPrecio' in item and 'fechaHora' in item:
                prices.append({
                    'contract_symbol': symbol,
                    'price': item.get('ultimoPrecio', 0.0),
                    'broker_timestamp': item.get('fechaHora'),
                    'system_timestamp': system_timestamp,
                    'volume': int(item.get('volumenNominal', 0))
                })
        return prices
        
    except requests.exceptions.RequestException as e:
        print(f"Warning: Failed to fetch history for {symbol}: {e}")
        return []
    except Exception as e:
        print(f"Error parsing history for {symbol}: {e}")
        return []

def process_historical_data(date_from_str: str, token: str) -> None:
    """
    Orchestrates collecting historical data for all symbols.
    
    1. Fetches all known symbols from DB.
    2. Iterates and calls `fetch_historical_prices` for each.
    3. Batch inserts results to DB.

    Args:
        date_from_str: Start date in "YYYY-MM-DD" format.
        token: Access Token.
    """
    try:
        # Parse Dates
        date_from = datetime.strptime(date_from_str, "%Y-%m-%d")
        date_to = datetime.now()
        
        # 1. Get Symbols
        symbols = get_all_contract_symbols()
        print(f"Found {len(symbols)} symbols to backfill.")
        
        # 2. Iterate
        total_records = 0
        for symbol in symbols:
            print(f"Fetching history for {symbol}...")
            prices = fetch_historical_prices(symbol, date_from, date_to, token)
            
            if prices:
                # 3. Batch Insert
                insert_market_prices_batch(prices)
                count = len(prices)
                total_records += count
                print(f"  > Inserted {count} records.")
            else:
                print(f"  > No data.")
                
        print(f"Done. Total historical records inserted: {total_records}")
        
    except ValueError:
        print("Error: Invalid date format. Please use YYYY-MM-DD.")
    except Exception as e:
        print(f"Critical Error in process_historical_data: {e}")


def _parse_latest_price(item: Dict[str, Any]) -> LatestPriceData:
    """Parses IOL API response for latest price fields."""
    cotizacion = item.get('cotizacion', item)
    
    # Extract timestamp
    timestamp = cotizacion.get('fechaHora')
    if timestamp and timestamp.startswith("0001-01-01"):
        timestamp = None
        
    return {
        'symbol': item.get('simbolo'),
        'market_id': item.get('mercado'),
        'last_price': cotizacion.get('ultimoPrecio'),
        'bid_price': cotizacion.get('precioCompra'),
        'offer_price': cotizacion.get('precioVenta'),
        'timestamp': timestamp
    }

def _fetch_latest_data_safe(symbol: str, token: str) -> Optional[LatestPriceData]:
    """Fetches latest data for a symbol, safely handling errors."""
    try:
        url = f"{BASE_URL}/bCBA/Titulos/{symbol}"
        headers = {"Authorization": f"Bearer {token}"}
        res = requests.get(url, headers=headers)
        res.raise_for_status()
        data = res.json()
        return _parse_latest_price(data)
    except Exception as e:
        print(f"Failed to fetch {symbol}: {e}")
        return None

def batch_fetch_latest_prices(symbols: List[str], token: str, max_workers: int = 10) -> None:
    """
    Fetches latest prices (Last, Bid, Offer) for a list of symbols concurrently and writes to the database in batches.

    ## Architecture & Implementation Details

    This function utilizes a **concurrent execution model** to overcome network latency inherent in sequential API requests.

    ### Concurrency
    It uses `concurrent.futures.ThreadPoolExecutor` to spawn multiple worker threads (default: 10).
    Each thread performs a blocking I/O call to the IOL API via `_fetch_latest_data_safe`.
    
    *   **Pros**: Drastically reduces total execution time for large lists of symbols.
    *   **Cons**: Higher CPU/Memory overhead compared to sequential, though negligible for I/O bound tasks.

    ### Batch Processing
    To optimize database interactions, results are not written one-by-one. Instead:
    1.  Results are accumulated in a local list `prices_accumulator`.
    2.  When the accumulator reaches a threshold (e.g., 20 items), a **batch upsert** is triggered via `upsert_latest_prices_batch`.
    3.  The accumulator is cleared, and the process continues.
    4.  A final flush handles any remaining items after the loop.

    ### Error Handling
    Individual symbol fetch failures are caught within `_fetch_latest_data_safe` and return `None`.
    These `None` results are filtered out, ensuring that one bad request does not crash the entire batch process.

    Args:
        symbols: List of contract symbols to fetch.
        token: Valid IOL Access Token.
        max_workers: Number of concurrent threads to use. Defaults to 10.
    """
    import random
    
    prices_accumulator: List[LatestPriceData] = []
    
    print(f"Starting batch fetch for {len(symbols)} symbols with {max_workers} workers...")
    
    # Debug sampling
    debug_samples = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_symbol = {executor.submit(_fetch_latest_data_safe, sym, token): sym for sym in symbols}
        
        for future in as_completed(future_to_symbol):
            data = future.result()
            
            if not data:
                print("DEBUG: future.result() is None")
                continue
                
            if not data.get('timestamp'):
                print(f"DEBUG: Skipping {data.get('symbol')} - Missing timestamp. Raw: {data}")
            
            if data and data.get('timestamp'): 
                # Ensure we respect DB constraints (non-null timestamp usually required or useful)
                prices_accumulator.append(data)
                
                # Collect sample
                if len(debug_samples) < 5:
                    debug_samples.append((data['symbol'], data['timestamp']))
                elif random.random() < 0.1: # Reservoir sampling-ish replacment for variety
                    idx = random.randint(0, 4)
                    debug_samples[idx] = (data['symbol'], data['timestamp'])
            
            # Intermediate batch save
            if len(prices_accumulator) >= 20:
                upsert_latest_prices_batch(prices_accumulator)
                prices_accumulator = []

    # Final save
    if prices_accumulator:
        upsert_latest_prices_batch(prices_accumulator)
        
    print("Batch fetch completed.")
    
    print("\n--- DEBUG: Random Sample of Fetched Data ---")
    for s, t in debug_samples:
        print(f"Symbol: {s}, Timestamp: {t}")
    print("--------------------------------------------\n")

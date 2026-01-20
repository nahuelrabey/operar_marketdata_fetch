import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from supabase import create_client, Client
from dotenv import load_dotenv
from src.type_definitions import *

load_dotenv()

# --- Database Connection ---

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

_client: Optional[Client] = None

def get_client() -> Client:
    """
    Retrieves or initializes the Supabase client.

    Returns:
        The authenticated Supabase client instance.

    Raises:
        EnvironmentError: If SUPABASE_URL or SUPABASE_KEY are missing.
    """
    global _client
    if _client is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise EnvironmentError("SUPABASE_URL and SUPABASE_KEY environment variables are required.")
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client

# --- Initialization ---

def initialize_db() -> None:
    """
    Checks connection to Supabase and verifies core tables exist.

    This function performs a simple query to ensure connectivity. 
    Table creation is handled via external SQL scripts.
    """
    try:
        client = get_client()
        # Simple ping to verify connection/tables
        client.table("positions").select("count", count="exact").limit(0).execute()
        # print("Connected to Supabase successfully.")
    except Exception as e:
        print(f"Warning: Could not connect to Supabase: {e}")
        print("Ensure SUPABASE_URL and SUPABASE_KEY are set.")

# --- CRUD Functions ---

def upsert_contract(contract_data: ContractData) -> None:
    """
    Inserts or updates contract details in the 'options_contracts' table.

    Args:
        contract_data: Key-value pairs matching the table schema.
    """
    client = get_client()
    # Supabase upsert requires dict keys to match column names
    client.table("options_contracts").upsert(contract_data).execute()

def insert_market_price(price_data: PriceData) -> int:
    """
    Logs new price data for a contract.

    Args:
        price_data: The market price information to insert.

    Returns:
        The ID of the inserted record, or -1 if failed.
    """
    client = get_client()
    response = client.table("market_prices").insert(price_data).execute()
    if response.data and len(response.data) > 0:
        return response.data[0]['id']
    return -1

def create_position(name: str, description: str) -> int:
    """
    Creates a new strategy position with status 'OPEN'.

    Args:
        name: Name of the strategy.
        description: Brief description of the strategy.

    Returns:
        The ID of the newly created position.
    """
    client = get_client()
    data = {"name": name, "description": description, "status": "OPEN"}
    response = client.table("positions").insert(data).execute()
    if response.data and len(response.data) > 0:
        return response.data[0]['id']
    return -1

def add_operation(position_id: int, operation_data: OperationData) -> int:
    """
    Adds a trade (operation) to a position.

    Performs a two-step process:
    1. Inserts the operation into the `operations` table.
    2. Links it to the position in the `position_contains_operations` table.

    Args:
        position_id: The ID of the strategy/position.
        operation_data: The details of the trade.

    Returns:
        The ID of the created operation.

    Raises:
        Exception: If the operation insert fails.
    """
    client = get_client()
    
    # 1. Insert Operation
    op_resp = client.table("operations").insert(operation_data).execute()
    if not op_resp.data:
        raise Exception("Failed to insert operation")
        
    operation_id = op_resp.data[0]['id']

    # 2. Link to Position
    link_data = {"position_id": position_id, "operation_id": operation_id}
    client.table("position_contains_operations").insert(link_data).execute()
    
    return operation_id

def remove_operation_from_position(position_id: int, operation_id: int) -> bool:
    """
    Removes the link between a position and an operation.

    Args:
        position_id: The strategy ID.
        operation_id: The operation ID to remove.

    Returns:
        True if the deletion was successful, False otherwise.
    """
    client = get_client()
    response = client.table("position_contains_operations")\
        .delete()\
        .eq("position_id", position_id)\
        .eq("operation_id", operation_id)\
        .execute()
    
    return len(response.data) > 0

def close_position(position_id: int) -> bool:
    """
    Updates a position's status to 'CLOSED'.

    Args:
        position_id: The ID of the position to close.

    Returns:
        True if the update was successful.
    """
    client = get_client()
    response = client.table("positions").update({"status": "CLOSED"}).eq("id", position_id).execute()
    return len(response.data) > 0

def get_positions() -> List[PositionData]:
    """
    Retrieves a list of all positions.

    Returns:
        List of position metadata (id, name, status, etc.).
    """
    client = get_client()
    response = client.table("positions").select("*").order("created_at", desc=True).execute()
    return response.data

def get_position_details(position_id: int) -> PositionDetails:
    """
    Retrieves detailed information for a specific position.

    This includes all individual operations and the calculated net composition 
    (aggregated quantity per symbol).

    Args:
        position_id: The ID of the position.

    Returns:
        Object containing raw operations and the net portfolio composition.
    """
    client = get_client()
    
    # Query operations via the link table
    response = client.table("position_contains_operations")\
        .select("operation:operations(*, contract:options_contracts(strike, type))")\
        .eq("position_id", position_id)\
        .execute()
        
    # Flatten/Normalize
    operations = []
    for item in response.data:
        op = item['operation']
        contract = op.get('contract')
        if contract:
            op['strike'] = contract.get('strike')
            op['contract_type'] = contract.get('type')
        operations.append(op)
    
    # Calculate Composition (Net Quantity)
    portfolio: Dict[str, int] = {}
    
    for op in operations:
        symbol = op.get('contract_symbol')
        qty = op.get('quantity', 0)
        if op.get('operation_type') == 'BUY':
            portfolio[symbol] = portfolio.get(symbol, 0) + qty
        else:
            portfolio[symbol] = portfolio.get(symbol, 0) - qty
            
    composition = [{'symbol': k, 'net_quantity': v} for k, v in portfolio.items() if v != 0]
    
    return {
        'operations': operations,
        'composition': composition
    }

def get_latest_prices(symbols: List[str]) -> Dict[str, float]:
    """
    Batch query to get existing latest prices for a list of symbols from the DB.

    Optimized to use resource embedding to fetch the latest market_price for each symbol.

    Args:
        symbols: List of contract symbols.

    Returns:
        A dictionary mapping symbol -> latest price.
    """
    if not symbols:
        return {}
        
    client = get_client()
    
    # We query contracts and embed the latest market price
    # limit(1) on foreign table works in Supabase
    response = client.table("options_contracts")\
        .select("symbol, market_prices(price, system_timestamp)")\
        .in_("symbol", symbols)\
        .order("system_timestamp", desc=True, foreign_table="market_prices")\
        .limit(1, foreign_table="market_prices")\
        .execute()

    prices_map = {}
    for item in response.data:
        symbol = item['symbol']
        mps = item.get('market_prices')
        if mps and len(mps) > 0:
            prices_map[symbol] = float(mps[0]['price'])
            
    return prices_map

def get_latest_prices_by_underlying(underlying_symbol: str) -> List[Dict[str, Any]]:
    """
    Retrieves the latest market price for all contracts of a given underlying.

    Args:
        underlying_symbol: The ticker of the underlying asset (e.g., 'GGAL').

    Returns:
        List of dicts with keys: symbol, type, strike, price, timestamp.
    """
    client = get_client()
    
    response = client.table("options_contracts")\
        .select("symbol, type, strike, market_prices(price, system_timestamp, broker_timestamp)")\
        .eq("underlying_symbol", underlying_symbol)\
        .order("strike", desc=False)\
        .order("system_timestamp", desc=True, foreign_table="market_prices")\
        .limit(1, foreign_table="market_prices")\
        .execute()
        
    results = []
    for item in response.data:
        mps = item.get('market_prices')
        price = 0.0
        timestamp = None
        
        if mps and len(mps) > 0:
            latest = mps[0]
            price = float(latest.get('price', 0))
            timestamp = latest.get('broker_timestamp') or latest.get('system_timestamp')
            
        results.append({
            'symbol': item['symbol'],
            'type': item['type'],
            'strike': float(item['strike']) if item['strike'] else 0.0,
            'price': price,
            'timestamp': timestamp
        })
        
    return results

def get_all_contract_symbols() -> List[str]:
    """
    Retrieves all contract symbols currently stored in the database.

    Returns:
        List of symbol strings.
    """
    client = get_client()
    response = client.table("options_contracts").select("symbol").execute()
    
    return [item['symbol'] for item in response.data]

def insert_market_prices_batch(prices: List[PriceData]) -> None:
    """
    Batch inserts multiple market price records.

    Uses Supabase upsert with ignore_duplicates=True to handle potential conflicts.

    Args:
        prices: List of PriceData objects.
    """
    client = get_client()
    if not prices:
        return
        
    try:
        response = client.table("market_prices").upsert(prices, ignore_duplicates=True).execute()
    except Exception as e:
        print(f"Error executing batch insert: {e}")


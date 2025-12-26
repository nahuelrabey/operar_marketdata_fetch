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
    global _client
    if _client is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise EnvironmentError("SUPABASE_URL and SUPABASE_KEY environment variables are required.")
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client

# --- Initialization ---

def initialize_db() -> None:
    """
    Checks connection to Supabase.
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
    """Inserts or updates contract details."""
    client = get_client()
    # Supabase upsert requires dict keys to match column names
    client.table("options_contracts").upsert(contract_data).execute()

def insert_market_price(price_data: PriceData) -> int:
    """Logs new price data. Returns the new row ID if available."""
    client = get_client()
    response = client.table("market_prices").insert(price_data).execute()
    if response.data and len(response.data) > 0:
        return response.data[0]['id']
    return -1

def create_position(name: str, description: str) -> int:
    """Inserts new strategy with status 'OPEN'. Returns the new position_id."""
    client = get_client()
    data = {"name": name, "description": description, "status": "OPEN"}
    response = client.table("positions").insert(data).execute()
    if response.data and len(response.data) > 0:
        return response.data[0]['id']
    return -1

def add_operation(position_id: int, operation_data: OperationData) -> int:
    """Transactional insert into operations and linking in position_contains_operations."""
    client = get_client()
    
    # Supabase doesn't support complex multi-table transactions via client directly 
    # in the same way SQL does (begin/commit), but we can do sequential inserts.
    # If a failure occurs, we might have orphaned records. 
    # RPC is recommended for true transactions, but we'll stick to sequential calls for logic CLI.
    
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
    """
    client = get_client()
    response = client.table("position_contains_operations")\
        .delete()\
        .eq("position_id", position_id)\
        .eq("operation_id", operation_id)\
        .execute()
    
    # Optionally remove the operation itself if orphaned? 
    # Design says "Optionally deletes the record". We'll skip that for safety/simplicity.
    
    return len(response.data) > 0

def close_position(position_id: int) -> bool:
    """Updates status to 'CLOSED'."""
    client = get_client()
    response = client.table("positions").update({"status": "CLOSED"}).eq("id", position_id).execute()
    return len(response.data) > 0

def get_positions() -> List[PositionData]:
    """Returns a list of all positions with their basic metadata."""
    client = get_client()
    response = client.table("positions").select("*").order("created_at", desc=True).execute()
    return response.data

def get_position_details(position_id: int) -> PositionDetails:
    """
    Aggregates operations to calculate Net Quantity per contract.
    """
    client = get_client()
    
    # Query operations via the link table
    # We want: Operation details + Contract details
    # Path: position_contains_operations -> operations -> options_contracts
    
    # Select from link table, joining operations and their nested contracts
    response = client.table("position_contains_operations")\
        .select("operation:operations(*, contract:options_contracts(strike, type))")\
        .eq("position_id", position_id)\
        .execute()
        
    # Response data structure will be list of { operation: { ..., contract: { ... } } }
    
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
    Batch query to get latest prices for a list of symbols.
    Optimized to use resource embedding to fetch the latest price for each symbol.
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
    Returns a list of dicts with keys: symbol, type, strike, price, timestamp.
    """
    client = get_client()
    
    # Similar strategy to get_latest_prices, but filtered by underlying
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

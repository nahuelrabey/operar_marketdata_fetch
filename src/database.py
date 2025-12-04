import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Any, Optional, TypedDict, Union

# --- Data Structures (from modules_design.md) ---

class ContractData(TypedDict):
    symbol: str
    underlying_symbol: str
    type: str
    expiration_date: str
    strike: float
    description: str

class PriceData(TypedDict):
    contract_symbol: str
    price: float
    broker_timestamp: Optional[str]
    system_timestamp: str
    volume: int

class OperationData(TypedDict):
    contract_symbol: str
    operation_type: str
    quantity: int
    price: float
    operation_date: str

# --- Database Connection ---

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'market_data.db')

def get_connection():
    return sqlite3.connect(DB_PATH)

# --- Initialization ---

def initialize_db() -> None:
    """Creates tables if they don't exist."""
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Options Contracts
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS options_contracts (
        symbol VARCHAR(50) PRIMARY KEY,
        underlying_symbol VARCHAR(20),
        type VARCHAR(10),
        expiration_date TEXT,
        strike DECIMAL(12, 3),
        description TEXT
    );
    ''')

    # 2. Market Prices
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS market_prices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        contract_symbol VARCHAR(50) REFERENCES options_contracts(symbol),
        price DECIMAL(12, 3),
        broker_timestamp TEXT,
        system_timestamp TEXT,
        volume INTEGER
    );
    ''')

    # 3. Positions (Strategy Container)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS positions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(100),
        description TEXT,
        status VARCHAR(20) DEFAULT 'OPEN',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    ''')

    # 4. Operations (Trades)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS operations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        contract_symbol VARCHAR(50) REFERENCES options_contracts(symbol),
        operation_type VARCHAR(4) CHECK (operation_type IN ('BUY', 'SELL')),
        quantity INTEGER NOT NULL,
        price DECIMAL(12, 3) NOT NULL,
        operation_date TEXT DEFAULT CURRENT_TIMESTAMP
    );
    ''')

    # 5. Position-Operations Link
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS position_contains_operations (
        position_id INTEGER REFERENCES positions(id),
        operation_id INTEGER REFERENCES operations(id),
        PRIMARY KEY (position_id, operation_id)
    );
    ''')

    conn.commit()
    conn.close()

# --- CRUD Functions ---

def upsert_contract(contract_data: ContractData) -> None:
    """Inserts or updates contract details."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    INSERT INTO options_contracts (symbol, underlying_symbol, type, expiration_date, strike, description)
    VALUES (?, ?, ?, ?, ?, ?)
    ON CONFLICT(symbol) DO UPDATE SET
        underlying_symbol=excluded.underlying_symbol,
        type=excluded.type,
        expiration_date=excluded.expiration_date,
        strike=excluded.strike,
        description=excluded.description;
    ''', (
        contract_data['symbol'],
        contract_data['underlying_symbol'],
        contract_data['type'],
        contract_data['expiration_date'],
        contract_data['strike'],
        contract_data['description']
    ))
    
    conn.commit()
    conn.close()

def insert_market_price(price_data: PriceData) -> int:
    """Logs new price data. Returns the new row ID."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    INSERT INTO market_prices (contract_symbol, price, broker_timestamp, system_timestamp, volume)
    VALUES (?, ?, ?, ?, ?)
    ''', (
        price_data['contract_symbol'],
        price_data['price'],
        price_data['broker_timestamp'],
        price_data['system_timestamp'],
        price_data['volume']
    ))
    
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id if new_id else -1

def create_position(name: str, description: str) -> int:
    """Inserts new strategy with status 'OPEN'. Returns the new position_id."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    INSERT INTO positions (name, description, status) VALUES (?, ?, 'OPEN')
    ''', (name, description))
    
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id if new_id else -1

def add_operation(position_id: int, operation_data: OperationData) -> int:
    """Transactional insert into operations and linking in position_contains_operations."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # 1. Insert Operation
        cursor.execute('''
        INSERT INTO operations (contract_symbol, operation_type, quantity, price, operation_date)
        VALUES (?, ?, ?, ?, ?)
        ''', (
            operation_data['contract_symbol'],
            operation_data['operation_type'],
            operation_data['quantity'],
            operation_data['price'],
            operation_data['operation_date']
        ))
        operation_id = cursor.lastrowid
        
        if not operation_id:
            raise Exception("Failed to insert operation")

        # 2. Link to Position
        cursor.execute('''
        INSERT INTO position_contains_operations (position_id, operation_id)
        VALUES (?, ?)
        ''', (position_id, operation_id))
        
        conn.commit()
        return operation_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def remove_operation_from_position(position_id: int, operation_id: int) -> bool:
    """
    Removes the link between a position and an operation.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "DELETE FROM position_contains_operations WHERE position_id = ? AND operation_id = ?",
            (position_id, operation_id)
        )
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def close_position(position_id: int) -> bool:
    """Updates status to 'CLOSED'."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    UPDATE positions SET status = 'CLOSED' WHERE id = ?
    ''', (position_id,))
    
    conn.commit()
    rows_affected = cursor.rowcount
    conn.close()
    return rows_affected > 0

def get_positions() -> List[Dict[str, Any]]:
    """Returns a list of all positions with their basic metadata."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM positions ORDER BY created_at DESC')
    rows = cursor.fetchall()
    
    positions = [dict(row) for row in rows]
    conn.close()
    return positions

def get_position_details(position_id: int) -> Dict[str, Any]:
    """
    Aggregates operations to calculate Net Quantity per contract.
    Note: P&L calculation is delegated to pnl.py, this function prepares the data.
    """
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Fetch operations
    cursor.execute('''
    SELECT o.id, o.contract_symbol, o.operation_type, o.quantity, o.price, o.operation_date, c.strike, c.type as contract_type
    FROM operations o
    JOIN position_contains_operations link ON o.id = link.operation_id
    LEFT JOIN options_contracts c ON o.contract_symbol = c.symbol
    WHERE link.position_id = ?
    ''', (position_id,))
    
    rows = cursor.fetchall()
    operations = [dict(row) for row in rows]
    
    conn.close()
    
    # Calculate Composition (Net Quantity)
    portfolio: Dict[str, int] = {}
    
    for op in operations:
        symbol = op['contract_symbol']
        qty = op['quantity']
        if op['operation_type'] == 'BUY':
            portfolio[symbol] = portfolio.get(symbol, 0) + qty
        else:
            portfolio[symbol] = portfolio.get(symbol, 0) - qty
            
    composition = [{'symbol': k, 'net_quantity': v} for k, v in portfolio.items() if v != 0]
    
    return {
        'operations': operations,
        'composition': composition
    }

def get_latest_prices(symbols: List[str]) -> Dict[str, float]:
    """Batch query to get latest prices for a list of symbols."""
    if not symbols:
        return {}
        
    conn = get_connection()
    cursor = conn.cursor()
    
    placeholders = ','.join(['?'] * len(symbols))
    query = f'''
    SELECT contract_symbol, price 
    FROM market_prices 
    WHERE contract_symbol IN ({placeholders})
    AND (contract_symbol, system_timestamp) IN (
        SELECT contract_symbol, MAX(system_timestamp)
        FROM market_prices
        WHERE contract_symbol IN ({placeholders})
        GROUP BY contract_symbol
    );
    '''
    
    # We need to pass the symbols list twice because of the subquery
    cursor.execute(query, symbols + symbols)
    rows = cursor.fetchall()
    conn.close()
    
    return {row[0]: row[1] for row in rows}

def get_latest_prices_by_underlying(underlying_symbol: str) -> List[Dict[str, Any]]:
    """
    Retrieves the latest market price for all contracts of a given underlying.
    Returns a list of dicts with keys: symbol, type, strike, price, timestamp.
    """
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    query = '''
    SELECT 
        c.symbol, 
        c.type, 
        c.strike, 
        mp.price, 
        COALESCE(mp.broker_timestamp, mp.system_timestamp) as timestamp
    FROM options_contracts c
    JOIN market_prices mp ON c.symbol = mp.contract_symbol
    WHERE c.underlying_symbol = ?
    AND mp.system_timestamp = (
        SELECT MAX(system_timestamp) 
        FROM market_prices 
        WHERE contract_symbol = c.symbol
    )
    ORDER BY c.strike ASC;
    '''
    
    cursor.execute(query, (underlying_symbol,))
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

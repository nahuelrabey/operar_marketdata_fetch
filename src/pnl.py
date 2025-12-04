import numpy as np
from typing import List, Dict, Tuple, Any

def calculate_pnl(operations: List[Dict[str, Any]], current_prices_map: Dict[str, float]) -> Tuple[float, np.ndarray]:
    """
    Calculates the Current P&L for a set of operations.
    
    Args:
        operations: List of dicts with keys ['contract_symbol', 'operation_type', 'quantity', 'price']
        current_prices_map: Dict { 'symbol': current_price_float }
        
    Returns:
        total_pnl: float
        pnl_vec: np.ndarray (P&L per leg)
    """
    if not operations:
        return 0.0, np.array([])

    # 1. Prepare Lists
    quantities = []
    entry_prices = []
    current_prices = []
    
    for op in operations:
        symbol = op['contract_symbol']
        # Determine Signed Quantity
        q = op['quantity'] if op['operation_type'] == 'BUY' else -op['quantity']
        
        # Get Prices
        p_entry = float(op['price'])
        # Fallback to entry price if no current price (P&L = 0 for that leg)
        p_curr = current_prices_map.get(symbol, p_entry) 
        
        quantities.append(q)
        entry_prices.append(p_entry)
        current_prices.append(p_curr)
        
    # 2. Convert to Numpy Arrays
    q_vec = np.array(quantities)
    p_entry_vec = np.array(entry_prices)
    p_current_vec = np.array(current_prices)
    
    # 3. Vector Calculation
    # P&L = q * (p_current - p_entry)
    pnl_vec = q_vec * (p_current_vec - p_entry_vec)
    
    # 4. Total P&L
    total_pnl = float(np.sum(pnl_vec))
    
    return total_pnl, pnl_vec

def calculate_pnl_curve_at_finish(operations: List[Dict[str, Any]], current_underlying_price: float, range_pct: float = 0.2, steps: int = 100) -> Tuple[np.ndarray, np.ndarray]:
    """
    Generates the P&L curve at expiration.
    
    Args:
        operations: List of dicts (must include 'strike', 'contract_type'/'type', 'operation_type', 'quantity', 'price')
        current_underlying_price: Float, center of the simulation range.
        range_pct: Float, percentage range to simulate (e.g., 0.2 for +/- 20%).
        steps: Int, number of price points.
        
    Returns:
        S_T: np.ndarray (The price vector)
        total_pnl_curve: np.ndarray (The returns vector)
    """
    if not operations:
        return np.array([]), np.array([])
        
    # 1. Generate Underlying Price Vector (S_T)
    min_price = current_underlying_price * (1 - range_pct)
    max_price = current_underlying_price * (1 + range_pct)
    S_T = np.linspace(min_price, max_price, steps)
    
    # Initialize Total P&L vector with zeros
    total_pnl_curve = np.zeros_like(S_T)
    
    for op in operations:
        # Handle key variations if necessary, assuming standard keys from database.py
        K = float(op.get('strike', 0))
        contract_type = op.get('contract_type') or op.get('type') # 'Call' or 'Put'
        
        q = op['quantity'] if op['operation_type'] == 'BUY' else -op['quantity']
        p_entry = float(op['price'])
        
        # 2. Vectorized Payoff Calculation
        if contract_type == 'Call':
            # Payoff = max(S_T - K, 0)
            payoff = np.maximum(S_T - K, 0)
        elif contract_type == 'Put':
            # Payoff = max(K - S_T, 0)
            payoff = np.maximum(K - S_T, 0)
        else:
            continue # Skip if unknown type
            
        # 3. P&L for this leg
        # P&L = Quantity * (Final_Value - Initial_Cost)
        leg_pnl = q * (payoff - p_entry)
        
        # Add to total
        total_pnl_curve += leg_pnl
        
    return S_T, total_pnl_curve

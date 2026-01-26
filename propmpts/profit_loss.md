# P&L Calculation Strategy

This document explains how to calculate the **Current Profit & Loss (P&L)** for a Strategy (Position) using the tables defined in `DatabaseDesign.md` and Python's `numpy` library for efficient vector operations.

## 1. Data Retrieval

To calculate P&L, we need two sets of data:
1.  **Operations**: The trades executed (Entry Price, Quantity, Type).
2.  **Market Prices**: The current market price for the contracts involved.

### SQL Query: Fetch Operations
Get all operations linked to the target `position_id`.

```sql
SELECT 
    o.contract_symbol, 
    o.operation_type, 
    o.quantity, 
    o.price as entry_price
FROM operations o
JOIN position_contains_operations link ON o.id = link.operation_id
WHERE link.position_id = ?;
```

### SQL Query: Fetch Latest Market Prices
For each distinct `contract_symbol` found in the operations, fetch the most recent price.

### SQL Query: Fetch Latest Market Prices (Batch)
Instead of running one query per symbol (which is slow), we fetch all needed prices in one go.

```sql
SELECT contract_symbol, price 
FROM market_prices 
WHERE contract_symbol IN ('GGAL_CALL', 'GGAL_PUT', ...) -- List of symbols from operations
AND (contract_symbol, system_timestamp) IN (
    SELECT contract_symbol, MAX(system_timestamp)
    FROM market_prices
    GROUP BY contract_symbol
);
```
**Why?** Running a separate query for each contract (e.g., 50 times for a 50-leg strategy) introduces significant network latency ("N+1 problem"). A single batch query is much faster.

## 2. Vector Construction

We will convert the SQL results into `numpy` arrays.

Let $N$ be the number of operations.

- **`q` (Signed Quantity)**: Vector of size $N$.
    - If `operation_type` == 'BUY', value is `+quantity`.
    - If `operation_type` == 'SELL', value is `-quantity`.
- **`p_entry` (Entry Price)**: Vector of size $N$.
    - Contains the `price` from the `operations` table.
- **`p_current` (Current Price)**: Vector of size $N$.
    - Contains the latest market price corresponding to the `contract_symbol` of that operation.

## 3. Calculation Logic

The P&L for a single trade is:
$$ P\&L_{trade} = Quantity_{signed} \times (Price_{current} - Price_{entry}) $$

- **Long Position (Buy)**:
    - You bought at 100, current is 110. $1 \times (110 - 100) = +10$ (Profit).
    - You bought at 100, current is 90. $1 \times (90 - 100) = -10$ (Loss).
- **Short Position (Sell)**:
    - You sold at 100, current is 90. $-1 \times (90 - 100) = -1 \times -10 = +10$ (Profit).
    - You sold at 100, current is 110. $-1 \times (110 - 100) = -1 \times 10 = -10$ (Loss).

## 4. Python Implementation with Numpy

```python
import numpy as np
import pandas as pd
from typing import List, Dict, TypedDict

# In the actual implementation, this class is imported from src.database
from src.database import OperationData

# For this logical definition, we assume OperationData has:
# keys: 'contract_symbol', 'operation_type', 'quantity', 'price'

def calculate_pnl(operations: List[OperationData], current_prices_map: Dict[str, float]):
    """
    Calculates P&L using vectorized operations.
    """
    
    # 1. Prepare Lists
    quantities = []
    entry_prices = []
    current_prices = []
    
    for op in operations:
        # Determine Signed Quantity
        q = op['quantity'] if op['operation_type'] == 'BUY' else -op['quantity']
        
        # Get Prices
        p_entry = op['price']
        # Fallback to entry if no current price
        p_curr = current_prices_map.get(op['contract_symbol'], p_entry) 
        
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
    total_pnl = np.sum(pnl_vec)
    
    return total_pnl, pnl_vec

# Example Usage
ops: List['OperationData'] = [
    {'contract_symbol': 'GGAL_CALL', 'operation_type': 'BUY', 'quantity': 10, 'price': 100},
    {'contract_symbol': 'GGAL_PUT', 'operation_type': 'SELL', 'quantity': 10, 'price': 50}
]
prices = {
    'GGAL_CALL': 120, # Gain of 20 * 10 = 200
    'GGAL_PUT': 40    # Gain of 10 * 10 = 100 (Price dropped, good for short)
}

total, details = calculate_pnl(ops, prices)
print(f"Total P&L: {total}") # Should be 300
```

## 5. P&L Curve at Finish (Expiration)

This calculation generates the P&L profile of the strategy at expiration across a range of possible underlying asset prices.

### Logic
We simulate a range of underlying prices ($S_T$) and calculate the payoff for each contract.

$$ P\&L_{finish} = Quantity \times (Payoff(S_T) - Price_{entry}) $$

- **Call Payoff**: $max(S_T - K, 0)$
- **Put Payoff**: $max(K - S_T, 0)$

### Python Implementation

The output is two `numpy.ndarray` vectors:
1.  `S_T`: Array of underlying prices.
2.  `total_pnl_curve`: Array of total P&L at each price point.

```python
def calculate_pnl_curve_at_finish(operations, current_underlying_price, range_pct=0.2, steps=100):
    """
    Generates the P&L curve at expiration.
    
    Args:
        operations: List of dicts (must include 'strike', 'type', 'quantity', 'price')
        current_underlying_price: Float, center of the simulation range.
        range_pct: Float, percentage range to simulate (e.g., 0.2 for +/- 20%).
        steps: Int, number of price points.
        
    Returns:
        S_T: np.ndarray (The price vector)
        total_pnl_curve: np.ndarray (The returns vector)
    """
    
    # 1. Generate Underlying Price Vector (S_T)
    min_price = current_underlying_price * (1 - range_pct)
    max_price = current_underlying_price * (1 + range_pct)
    S_T = np.linspace(min_price, max_price, steps) # Vector of float64
    
    # Initialize Total P&L vector with zeros
    total_pnl_curve = np.zeros_like(S_T)
    
    for op in operations:
        K = op['strike']
        q = op['quantity'] if op['type'] == 'BUY' else -op['quantity']
        p_entry = op['price']
        
        # 2. Vectorized Payoff Calculation
        if op['type'] == 'Call':
            # Payoff = max(S_T - K, 0)
            payoff = np.maximum(S_T - K, 0)
        elif op['type'] == 'Put':
            # Payoff = max(K - S_T, 0)
            payoff = np.maximum(K - S_T, 0)
        else:
            continue # Should not happen
            
        # 3. P&L for this leg
        # P&L = Quantity * (Final_Value - Initial_Cost)
        leg_pnl = q * (payoff - p_entry)
        
        # Add to total
        total_pnl_curve += leg_pnl
        
    return S_T, total_pnl_curve
```

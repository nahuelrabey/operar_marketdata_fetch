# Algorithms and Functions

This document describes the backend functions and algorithms required to fulfill the use cases defined in `use_cases.md`.

## 1. Use Case: Create a New Strategy

### Function: `create_position(name: str, description: str) -> int`
**Goal**: Create a new strategy container.

**Algorithm**:
1.  **Input Validation**: Ensure `name` is not empty.
2.  **Database Insert**:
    ```sql
    INSERT INTO positions (name, description, status) VALUES (?, ?, 'OPEN');
    ```
3.  **Return**: The `id` of the newly created row.

## 2. Use Case: Add a Trade to a Strategy

### Function: `add_operation_to_position(position_id: int, contract_symbol: str, type: str, quantity: int, price: float) -> int`
**Goal**: Record a trade and link it to the strategy.

**Algorithm**:
1.  **Transaction Start**: Begin a database transaction to ensure atomicity.
2.  **Insert Operation**:
    ```sql
    INSERT INTO operations (contract_symbol, operation_type, quantity, price)
    VALUES (?, ?, ?, ?);
    -- Capture the new operation_id
    ```
3.  **Link Operation**:
    ```sql
    INSERT INTO position_contains_operations (position_id, operation_id)
    VALUES (?, ?);
    ```
4.  **Transaction Commit**: Save changes.
5.  **Return**: The `operation_id`.

## 3. Use Case: View Strategy Performance (Dashboard)

### Function: `get_position_details(position_id: int) -> dict`
**Goal**: Retrieve the composition, current P&L, and P&L curve for a strategy.

**Algorithm**:
1.  **Fetch Operations**:
    ```sql
    SELECT o.contract_symbol, o.operation_type, o.quantity, o.price
    FROM operations o
    JOIN position_contains_operations link ON o.id = link.operation_id
    WHERE link.position_id = ?;
    ```
2.  **Fetch Market Prices**:
    - Extract unique `contract_symbol`s from operations.
    - Execute **Batch Query** (as defined in `profit_loss.md`) to get latest prices.
3.  **Calculate Composition (Net Quantity)**:
    - Iterate through operations.
    - Aggregate `quantity` per `contract_symbol` (Add for BUY, Subtract for SELL).
4.  **Calculate Current P&L**:
    - Call `calculate_pnl(operations, current_prices)` (from `pnl.py`).
5.  **Calculate P&L Curve**:
    - Determine `current_underlying_price` (e.g., from the underlying asset of the contracts).
    - Call `calculate_pnl_curve_at_finish(operations, current_underlying_price)` (from `pnl.py`).
6.  **Return**: A dictionary containing:
    - `composition`: List of `{symbol, net_quantity}`.
    - `current_pnl`: Float.
    - `pnl_curve`: `{x: S_T_vector, y: pnl_vector}`.

## 4. Use Case: Close a Strategy

### Function: `close_position(position_id: int) -> bool`
**Goal**: Mark a strategy as closed.

**Algorithm**:
1.  **Database Update**:
    ```sql
    UPDATE positions SET status = 'CLOSED' WHERE id = ?;
    ```
2.  **Return**: `True` if successful.
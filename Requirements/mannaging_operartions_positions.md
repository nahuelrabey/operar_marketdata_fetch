# Managing Operations and Positions

This document details the user interactions and underlying logic for managing **Positions** (Strategies) and **Operations** (Trades) within the application interface.

## Concepts
- **Position (Strategy)**: A container for a set of related trades. Examples: "Long Call GGAL", "Bear Put Spread", "Covered Call".
- **Operation (Trade)**: A single buy or sell transaction of an option contract.

---

## User Cases

### 1. Create a New Strategy (Position)
**User Story**: As a user, I want to define a new trading strategy so that I can group related trades together.
- **UI Action**: Click "New Strategy" button.
- **Input**:
    - Name (e.g., "Bull Spread GGAL Dec").
    - Description (Optional).
- **System Action**: Creates a new record in the `positions` table with status 'OPEN'.

### 2. Add a Trade (Operation) to a Strategy
**User Story**: As a user, I want to record a buy or sell order and link it to a specific strategy.
- **UI Action**:
    1.  Select an active Strategy from a dropdown/list.
    2.  Select an Option Contract (e.g., from the Market Data view).
    3.  Click "Add Trade".
- **Input**:
    - Operation Type: "BUY" or "SELL".
    - Quantity: Integer (e.g., 10).
    - Price: Decimal (Premium paid/received).
- **System Action**:
    - Creates a record in `operations`.
    - Links the operation to the selected `position` via `position_contains_operations`.

### 3. View Strategy Performance (Dashboard)
**User Story**: As a user, I want to see how my strategies are performing.
- **UI Action**: Navigate to "Strategies" tab.
- **Display**: List of active positions showing:
    - Name.
    - **Composition**: List of contracts with their **Net Quantity** (e.g., "+10 GGAL Call 2600", "-10 GGAL Call 2800").
    - Current P&L (Calculated based on live market data).
- **System Action**: Queries all operations for each position and calculates metrics on-the-fly.

### 4. Close a Strategy
**User Story**: As a user, I want to mark a strategy as finished.
- **UI Action**: Click "Close Strategy" on a specific position.
- **System Action**: Updates `positions.status` to 'CLOSED'.

---

## Algorithms and Strategies (CRUD Logic)

### 1. Creating a Position
**Operation**: `INSERT`
**Logic**:
1.  Receive `name` and `description` from UI.
2.  Execute SQL:
    ```sql
    INSERT INTO positions (name, description, status) VALUES (?, ?, 'OPEN');
    ```
3.  Return the new `id`.

### 2. Adding an Operation
**Operation**: `INSERT` (with Link)
**Logic**:
1.  Receive `position_id`, `contract_symbol`, `type`, `quantity`, `price`.
2.  **Transaction Start**:
    1.  Insert the operation:
        ```sql
        INSERT INTO operations (contract_symbol, operation_type, quantity, price)
        VALUES (?, ?, ?, ?);
        -- Get the new operation_id
        ```
    2.  Link to position:
        ```sql
        INSERT INTO position_contains_operations (position_id, operation_id)
        VALUES (?, ?);
        ```
3.  **Transaction Commit**.

### 3. Calculating Position Metrics (Read Strategy)
Since `positions` is just a container, we must derive its state from its `operations`.

**Algorithm: Calculate Net Quantity per Contract**
**Net Quantity** is the total number of contracts held for a specific symbol, accounting for buys and sells.

1.  **Fetch Operations**:
    ```sql
    SELECT o.contract_symbol, o.operation_type, o.quantity, o.price
    FROM operations o
    JOIN position_contains_operations link ON o.id = link.operation_id
    WHERE link.position_id = ?;
    ```
2.  **Group and Aggregate**:
    - Create a dictionary/map: `portfolio = {}`
    - For each operation:
        - Key = `contract_symbol`
        - If `BUY`:
            - `portfolio[key].quantity += quantity`
            - `portfolio[key].invested += quantity * price`
        - If `SELL`:
            - `portfolio[key].quantity -= quantity`
            - `portfolio[key].invested -= quantity * price`
3.  **Result**:
    - A list of holdings, where each holding has a `Net Quantity` (Sum of Buys - Sum of Sells).
    - If `Net Quantity` is 0, the position for that specific contract is closed.

### 4. Deleting/Correcting an Operation
**Operation**: `DELETE` or `UPDATE`
**Logic**:
- **Delete**:
    1.  Remove link from `position_contains_operations`.
    2.  Delete record from `operations`.
- **Update**:
    1.  Update fields in `operations` directly.
    2.  Recalculate Position Metrics to update the UI.

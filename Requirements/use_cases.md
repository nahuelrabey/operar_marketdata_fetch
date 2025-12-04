This document details the user interactions and underlying logic for managing **Positions** (Strategies) and **Operations** (Trades) within the application interface.

## Concepts
- **Position (Strategy)**: A container for a set of related trades. Examples: "Long Call GGAL", "Bear Put Spread", "Covered Call".
- **Operation (Trade)**: A single buy or sell transaction of an option contract.

---

## User Cases

### 1. List Current Prices by Underlying
**User Story**: As a user, I want to view the latest market prices for all contracts associated with a specific underlying asset.
- **UI Action**:
    1.  Select an Underlying Symbol (e.g., "GGAL").
    2.  Click "Refresh".
- **Display**: A table showing:
    - Contract Symbol.
    - Type (Call/Put).
    - Strike.
    - Last Price.
    - Timestamp (Broker timestamp if available, system timestamp otherwise).
- **System Action**:
    - Queries `market_prices` joined with `options_contracts`.
    - Filters by `underlying_symbol` and selects the most recent `system_timestamp` for each contract.

### 2. Create a New Strategy (Position)
**User Story**: As a user, I want to define a new trading strategy so that I can group related trades together.
- **UI Action**: Click "New Strategy" button.
- **Input**:
    - Name (e.g., "Bull Spread GGAL Dec").
    - Description (Optional).
- **System Action**: Creates a new record in the `positions` table with status 'OPEN'.

### 3. Add a Trade (Operation) to a Strategy
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

### 4. Remove a Trade (Operation) from a Strategy
**User Story**: As a user, I want to remove an incorrect trade from a strategy.
- **UI Action**:
    1.  Select a trade in the Composition list.
    2.  Click "Remove Trade".
- **System Action**:
    - Deletes the link in `position_contains_operations`.
    - Optionally deletes the record in `operations` (or keeps it as orphaned/archived).
    - Recalculates strategy metrics.

### 5. View Strategy Performance (Dashboard)
**User Story**: As a user, I want to see how my strategies are performing.
- **UI Action**: Navigate to "Strategies" tab.
- **Display**: List of active positions showing:
    - Name.
    - **Composition**: List of contracts with their **Net Quantity** (e.g., "+10 GGAL Call 2600", "-10 GGAL Call 2800").
    - **Current P&L**: Calculated based on live market data.
    - **P&L at Finish Graph**: A visual curve showing the projected P&L at expiration across a range of underlying prices (as defined in `profit_loss.md`).
- **System Action**: 
    - Queries all operations for each position.
    - Calculates metrics on-the-fly.
    - Generates the P&L curve vectors (`S_T`, `total_pnl_curve`) for plotting.

### 6. Close a Strategy
**User Story**: As a user, I want to mark a strategy as finished.
- **UI Action**: Click "Close Strategy" on a specific position.
- **System Action**: Updates `positions.status` to 'CLOSED'.

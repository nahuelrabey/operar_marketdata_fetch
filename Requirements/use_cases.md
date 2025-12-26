This document details the user interactions and underlying logic for managing **Positions** (Strategies) and **Operations** (Trades) within the application.

## Concepts
- **Position (Strategy)**: A container for a set of related trades. Examples: "Long Call GGAL", "Bear Put Spread", "Covered Call".
- **Operation (Trade)**: A single buy or sell transaction of an option contract.

---

## User Cases

### 1. List Current Prices by Underlying
**User Story**: As a user, I want to view the latest market prices for all contracts associated with a specific underlying asset.
- **CLI Command**: 
    ```bash
    python main.py prices <symbol>
    ```
    *Example*: `python main.py prices GGAL`
- **CLI Output**: A formatted text table showing:
    - Contract Symbol
    - Type (Call/Put)
    - Strike
    - Last Price
    - Timestamp (Broker or System)
- **System Action**:
    - Queries `market_prices` joined with `options_contracts`.
    - Filters by `underlying_symbol` and selects the most recent `system_timestamp` for each contract.

### 2. Create a New Strategy (Position)
**User Story**: As a user, I want to define a new trading strategy so that I can group related trades together.
- **CLI Command**:
    ```bash
    python main.py strategy new --name "<name>" [--description "<description>"]
    ```
    *Example*: `python main.py strategy new --name "Bull Spread GGAL Dec" --description "Long Call 2600 / Short Call 2800"`
- **CLI Output**: Confirmation message with the new Strategy ID.
- **System Action**: Creates a new record in the `positions` table with status 'OPEN'.

### 3. Add a Trade (Operation) to a Strategy
**User Story**: As a user, I want to record a buy or sell order and link it to a specific strategy.
- **CLI Command**:
    ```bash
    python main.py trade add --strategy <strategy_id> --symbol <contract_symbol> --type <BUY/SELL> --quantity <qty> --price <price>
    ```
    *Example*: `python main.py trade add --strategy 1 --symbol GFGC26009D --type BUY --quantity 10 --price 150`
- **CLI Output**: Confirmation message with the new Operation ID.
- **System Action**:
    - Creates a record in `operations`.
    - Links the operation to the selected `position` via `position_contains_operations`.

### 4. Remove a Trade (Operation) from a Strategy
**User Story**: As a user, I want to remove an incorrect trade from a strategy.
- **CLI Command**:
    ```bash
    python main.py trade remove --operation <operation_id>
    ```
- **CLI Output**: Confirmation message.
- **System Action**:
    - Deletes the link in `position_contains_operations`.
    - Optionally deletes the record in `operations`.
    - Recalculates strategy metrics.

### 5. View Strategy Performance (Dashboard)
**User Story**: As a user, I want to see how my strategies are performing.
- **CLI Command**:
    ```bash
    python main.py strategy view <strategy_id>
    ```
    *Note*: Use `python main.py strategy list` to see all active strategies.
- **CLI Output**: 
    - Text summary of the position (Name, ID, Status).
    - **Composition**: List of contracts with Net Quantity.
    - **Current P&L**: Calculated value.
    - **Path to Plot**: Location of the generated P&L curve image (e.g., `plots/strategy_1_pnl.png`).
- **System Action**: 
    - Queries all operations for each position.
    - Calculates metrics on-the-fly.
    - Generates the P&L curve vectors and saves the plot to a file string.

### 6. Close a Strategy
**User Story**: As a user, I want to mark a strategy as finished.
- **CLI Command**:
    ```bash
    python main.py strategy close <strategy_id>
    ```
- **CLI Output**: Confirmation message.
- **System Action**: Updates `positions.status` to 'CLOSED'.

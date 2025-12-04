# System Modules Design

This document outlines the complete design of the system, consolidating requirements from `database_design.md`, `algorithms.md`, `populating_market_data.md`, and `profit_loss.md`.

## 1. Proposed File Structure

```
MarketData/
├── data/                   # Storage for fetched CSVs and raw logs
├── src/
│   ├── __init__.py
│   ├── main.py             # Application entry point
│   ├── login.py            # Authentication logic
│   ├── fetch_data.py       # API interaction & Data Mapping
│   ├── database.py         # Database interactions & CRUD Algorithms
│   ├── pnl.py              # P&L Calculations (Numpy)
│   └── interface.py        # Graphical User Interface (Tkinter)
├── requirements.txt        # Python dependencies
├── .gitignore
└── README.md
```

---

## 2. Modules Detailed Design

### 2.1. Login Module (`src/login.py`)
**Responsibility**: Handle authentication with the Invertir Online API.

- **`authenticate(username, password) -> token`**:
    - Authenticates against the API.
    - Stores the token in `token.txt`.

### 2.2. FetchData Module (`src/fetch_data.py`)
**Responsibility**: Retrieve market data and map it to the domain model.

- **`fetch_option_chain(symbol, token) -> List[ContractData]`**:
    - Requests option chain from API.
    - Saves raw data to `data/`.
    - **Data Population Strategy** (from `populating_market_data.md`):
        - Maps JSON fields to `ContractData` and `PriceData`.
        - Handles `timestamp` splitting (`broker_timestamp` vs `system_timestamp`).
        - Parses `description` to extract `strike`.

### 2.3. Database Module (`src/database.py`)
**Responsibility**: Manage SQLite database interactions and implement business algorithms.

- **`initialize_db()`**: Creates tables (`options_contracts`, `market_prices`, `positions`, `operations`, `position_contains_operations`).
- **`upsert_contract(contract_data)`**: Inserts/Updates contract details.
- **`insert_market_price(price_data)`**: Logs new price data.

**CRUD Algorithms** (from `algorithms.md`):
- **`create_position(name, description)`**:
    - Inserts new strategy with status 'OPEN'.
- **`add_operation(position_id, operation_data)`**:
    - Transactional insert into `operations` and linking in `position_contains_operations`.
- **`get_position_details(position_id)`**:
    - Aggregates operations to calculate **Net Quantity** per contract.
    - Determines if the position is effectively closed (Net Qty = 0).
- **`close_position(position_id)`**:
    - Updates status to 'CLOSED'.

### 2.4. P&L Module (`src/pnl.py`)
**Responsibility**: Perform financial calculations using efficient vector operations.

**Logic** (from `profit_loss.md`):
- **`calculate_pnl(operations, current_prices_map) -> (total, details)`**:
    - Uses `numpy` to calculate $P\&L = Quantity_{signed} \times (Price_{current} - Price_{entry})$.
- **`calculate_pnl_curve_at_finish(operations, current_underlying, ...)`**:
    - Simulates underlying price range ($S_T$).
    - Calculates vectorized payoff:
        - Call: $max(S_T - K, 0)$
        - Put: $max(K - S_T, 0)$
    - Returns vectors for plotting the P&L curve at expiration.

### 2.5. Interface Module (`src/interface.py`)
**Responsibility**: Provide the GUI.

- **Login Tab**: Invokes `login.py`.
- **Market Data Tab**: Invokes `fetch_data.py` and `database.py` to save data.
- **Strategies Tab**:
    - Displays list of positions using `database.get_position_details`.
    - Shows **Composition** (Net Quantity).
    - Shows **Current P&L** (via `pnl.py`).
    - **Graph**: Plots the "P&L Curve at Finish" (via `pnl.py`).
    - **Actions**: "New Strategy", "Add Trade", "Close Strategy".

---

## 3. Data Structures

```python
from typing import TypedDict, List

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
    broker_timestamp: str | None
    system_timestamp: str
    volume: int

class OperationData(TypedDict):
    contract_symbol: str
    operation_type: str
    quantity: int
    price: float
    operation_date: str
```

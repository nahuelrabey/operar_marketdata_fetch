# System Modules Design

This document outlines the complete design of the system, consolidating requirements from `database_design.md`, `algorithms.md`, `populating_market_data.md`, and `profit_loss.md`.

## 1. Proposed File Structure

```
MarketData/
├── data/                   # Storage for fetched CSVs and raw logs
├── src/
│   ├── __init__.py
│   ├── main.py             # Application entry point (CLI)
│   ├── login.py            # Authentication logic
│   ├── fetch_data.py       # API interaction & Data Mapping
│   ├── database.py         # Database interactions & CRUD Algorithms
│   └── pnl.py              # P&L Calculations (Numpy)
├── requirements.txt        # Python dependencies
├── .gitignore
└── README.md
```

---

## 2. Modules Detailed Design

### 2.1. Login Module (`src/login.py`)
**Responsibility**: Handle authentication with the Invertir Online API.

- **`authenticate(username: str, password: str) -> str`**:
    - **Input**: User credentials.
    - **Output**: The authentication token as a string.
    - **Behavior**: Authenticates against the API and stores the token in `token.txt`.

### 2.2. FetchData Module (`src/fetch_data.py`)
**Responsibility**: Retrieve market data and map it to the domain model.

- **`fetch_option_chain(symbol: str, token: str) -> List[ContractData]`**:
    - **Input**: Underlying symbol (e.g., "GGAL") and auth token.
    - **Output**: List of `ContractData` dictionaries.
    - **Behavior**:
        - Requests option chain from API.
        - Saves raw data to `data/`.
        - **Data Population Strategy**: Maps JSON fields to `ContractData` and `PriceData`, handling timestamp splitting and strike extraction.

### 2.3. Database Module (`src/database.py`)
**Responsibility**: Manage SQLite database interactions and implement business algorithms.

- **`initialize_db() -> None`**:
    - Creates tables if they don't exist.
- **`upsert_contract(contract_data: ContractData) -> None`**:
    - Inserts or updates contract details.
- **`insert_market_price(price_data: PriceData) -> int`**:
    - Logs new price data. Returns the new row ID.

**CRUD Algorithms** (from `algorithms.md`):
- **`create_position(name: str, description: str) -> int`**:
    - Inserts new strategy with status 'OPEN'. Returns the new `position_id`.
- **`add_operation(position_id: int, operation_data: OperationData) -> int`**:
    - Transactional insert into `operations` and linking in `position_contains_operations`. Returns `operation_id`.
- **`remove_operation_from_position(position_id: int, operation_id: int) -> bool`**:
    - Removes the link between position and operation. Returns `True` on success.
- **`get_position_details(position_id: int) -> PositionDetails`**:
    - **Output**: Returns a `PositionDetails` dictionary containing composition and P&L data.
    - **Behavior**: Aggregates operations, calculates Net Quantity, and calls P&L module.
- **`close_position(position_id: int) -> bool`**:
    - Updates status to 'CLOSED'. Returns `True` on success.
- **`get_positions() -> List[PositionData]`**:
    - Returns a list of all positions with their basic metadata.
- **`get_latest_prices_by_underlying(underlying_symbol: str) -> List[Dict]`**:
    - **Output**: List of dicts with keys: `symbol`, `type`, `strike`, `price`, `timestamp`.
    - **Behavior**: Queries `market_prices` joined with `options_contracts` to get the latest price for each contract.

### 2.4. P&L Module (`src/pnl.py`)
**Responsibility**: Perform financial calculations using efficient vector operations.

**Logic** (from `profit_loss.md`):
- **`calculate_pnl(operations: List[Dict], current_prices_map: Dict[str, float]) -> Tuple[float, np.ndarray]`**:
    - **Output**: Total P&L (float) and a vector of P&L per leg.
    - **Behavior**: Uses `numpy` to calculate $P\&L = Quantity_{signed} \times (Price_{current} - Price_{entry})$.
- **`calculate_pnl_curve_at_finish(operations: List[Dict], current_underlying_price: float, range_pct: float = 0.2, steps: int = 100) -> Tuple[np.ndarray, np.ndarray]`**:
    - **Output**: Tuple of `(S_T_vector, total_pnl_curve_vector)`.
    - **Behavior**: Simulates underlying price range and calculates vectorized payoff for Calls and Puts.

### 2.5. Main Module (`src/main.py`)
**Responsibility**: Entry point for the CLI application.

- **`main()`**:
    - **Behavior**:
        - Parses command-line arguments (using `argparse`).
        - Routes commands to appropriate modules (`database`, `fetch_data`, etc.).
        - Prints formatted output to stdout.


---

## 3. Type Definitions

```python
from typing import TypedDict, List, Optional, Dict, Any

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

class PositionComposition(TypedDict):
    symbol: str
    net_quantity: int

class PositionDetails(TypedDict):
    composition: List[PositionComposition]
    current_pnl: float
    pnl_curve: Dict[str, Any] # values are np.ndarray

class PositionData(TypedDict):
    id: int
    name: str
    description: str
    status: str
    created_at: str
```

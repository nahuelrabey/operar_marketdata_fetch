# System Modules Design

This document outlines the design of the system modules based on the requirements defined in `DatabaseDesign.md`, `FetchData.md`, `DesktopInterface.md`, and `Login.md`.

## 1. Login Module (`src/login.py`)
**Responsibility**: Handle authentication with the Invertir Online API.

### Functions
- **`authenticate(username, password)`**:
    - **Input**: `username` (str), `password` (str).
    - **Output**: `token` (str) or raises an Exception.
    - **Behavior**:
        - Authenticates against the API.
        - Stores the received token in `token.txt` (root directory).
        - Returns the token.

## 2. FetchData Module (`src/fetch_data.py`)
**Responsibility**: Retrieve market data from the API.

### Functions
- **`fetch_option_chain(symbol, token)`**:
    - **Input**: `symbol` (str), `token` (str).
    - **Output**: List of dictionaries or DataFrame containing option data.
    - **Behavior**:
        - Uses the provided token to request the option chain for the given symbol.
        - Saves the raw data to `data/<symbol>_option_chain_<date>.csv`.
        - Returns the parsed data for further processing (e.g., database insertion).

## 3. Database Module (`src/database.py`)
**Responsibility**: Manage all interactions with the SQLite database.

### Functions
- **`initialize_db()`**:
    - Creates tables if they do not exist (based on `DatabaseDesign.md`).
- **`upsert_contract(contract_data)`**:
    - Inserts or ignores static contract details into `options_contracts`.
- **`insert_market_price(price_data)`**:
    - Inserts a new record into `market_prices`.
- **`create_position(name, description)`**:
    - Creates a new strategy container in `positions`.
- **`add_operation(position_id, operation_data)`**:
    - Adds a trade to `operations` and links it to the position via `position_contains_operations`.
- **`get_positions()`**:
    - Retrieves all positions with their associated operations and current status.

### Observations
- **Upsert**: This term combines "Update" and "Insert". It means that if a record already exists (e.g., a contract with the same symbol), it will be updated or ignored, and if it doesn't exist, it will be inserted. This prevents duplicate key errors.

### Data Structures
These structures define the dictionaries passed between modules, using Python types:

```python
from typing import TypedDict

class ContractData(TypedDict):
    symbol: str             # e.g., "GFGC26549D"
    underlying_symbol: str  # e.g., "GGAL"
    type: str               # "Call" or "Put"
    expiration_date: str    # ISO 8601 format: "YYYY-MM-DD"
    strike: float           # e.g., 2654.9
    description: str        # Human-readable description

class PriceData(TypedDict):
    contract_symbol: str    # e.g., "GFGC26549D"
    price: float            # Last price/premium, e.g., 150.5
    timestamp: str          # ISO 8601 format: "YYYY-MM-DD HH:MM:SS"
    volume: int             # e.g., 500

class OperationData(TypedDict):
    contract_symbol: str    # e.g., "GFGC26549D"
    operation_type: str     # "BUY" or "SELL"
    quantity: int           # e.g., 10
    price: float            # Premium per contract, e.g., 150.5
    operation_date: str     # ISO 8601 format: "YYYY-MM-DD HH:MM:SS"
```

## 4. Interface Module (`src/interface.py`)
**Responsibility**: Provide the Graphical User Interface (GUI) for the user.

### Components
- **Login Section**:
    - Inputs: Username, Password (handled securely, not stored).
    - Button: "Login".
    - Action: Calls `Login.authenticate`.
    - Feedback: "Login successful" + Token display (with copy button).
- **Market Data Section**:
    - Input: Stock Symbol (e.g., "GGAL").
    - Button: "Fetch Data".
    - Action:
        1.  Calls `FetchData.fetch_option_chain`.
        2.  Calls `Database.upsert_contract` and `Database.insert_market_price` to persist data.
    - Feedback: "Fetching option chain..." -> "Option chain fetched successfully."

## Module Interactions
1.  **User** interacts with **Interface**.
2.  **Interface** calls **Login** to get a token.
3.  **Interface** calls **FetchData** (passing the token) to get market data.
4.  **FetchData** returns data to **Interface** (and saves CSV).
5.  **Interface** (or a controller layer) calls **Database** to save the fetched data into SQLite.

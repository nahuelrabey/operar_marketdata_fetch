# Populating Market Data from Historical Prices

This document outlines the strategy to populate the `market_prices` table using the historical data endpoint from IOL API.

## 1. Goal
Populate `market_prices` with historical Series for options contracts to enable backtesting and P&L analysis over time.

## 2. Source Data
- **Endpoint**: `GET /api/v2/bCBA/Titulos/{symbol}/Cotizacion/seriehistorica/{date_from}/{date_to}/sinAjustar`
- **Parameters**: 
    - `date_from`: Start date (e.g., "2025-01-01").
    - `date_to`: End date (usually today).
    - `symbol`: The option contract symbol (e.g., "GFGC10177D").


### 2.1 Example API Response
```json
[
    {
    "ultimoPrecio": 16.001,
    "variacion": -36.3,
    "apertura": 28,
    "maximo": 28.1,
    "minimo": 17.002,
    "fechaHora": "2025-12-04T16:59:55.873",
    "tendencia": "mantiene",
    "cierreAnterior": 16.001,
    "montoOperado": 17962645.6,
    "volumenNominal": 7475,
    "precioPromedio": 0,
    "moneda": "peso_Argentino",
    "precioAjuste": 0,
    "interesesAbiertos": 0,
    "puntas": null,
    "cantidadOperaciones": 909,
    "descripcionTitulo": null,
    "plazo": null,
    "laminaMinima": 0,
    "lote": 0
  },
]
```

## 3. Data Mapping

The following table explains how each column in the `market_prices` table is populated using the data from the Example API Response (Section 2.1).

| Database Column | API Field (JSON) | Extraction Logic |
| :--- | :--- | :--- |
| `contract_symbol` | *N/A* | **Context/Argument**: This value is not present in the historical JSON object. It is passed as an argument to the function (`symbol`) from the API request URL context. |
| `price` | `ultimoPrecio` | Direct mapping. `Decimal(16.001)`. |
| `broker_timestamp`| `fechaHora` | Direct mapping. `"2025-12-04T16:59:55.873"`. Parsed to ISO format if needed. |
| `volume` | `volumenNominal` | Direct mapping. `7475`. (Note: Do not use `montoOperado` or `cantidadOperaciones`). |
| `system_timestamp`| *N/A* | **Generated**: The current system time (`datetime.now()`) when the record is processed/inserted. |

## 4. Algorithm Strategy

### 4.1. Prerequisites
- **Source of Symbols**: Query the `options_contracts` table. 
  `SELECT symbol FROM options_contracts`
- Valid Authentication Token.

### 4.2. Execution Flow
1.  **Fetch Symbols**: Retrieve all active option symbols from the `options_contracts` table.
2.  **Iterate & Fetch**: For *each* symbol:
    - Call the API endpoint with `date_from` (default "2025-01-01" if not provided) and `date_to` (today).
    - Parse the response.
    - Insert the price series into `market_prices`.

## 5. Required Functions

### 5.1. `src/fetch_data.py`

#### `fetch_historical_prices(symbol: str, date_from: datetime, date_to: datetime, token: str) -> List[PriceData]`
- Constructs the URL with formatted dates (e.g., `DD-MM-YYYY`).
- Makes the GET request.
- Parses the JSON list into `PriceData` objects.

#### `process_historical_data(date_from: str = "2025-01-01", token: str) -> None`
- Orchestrates the flow:
    - Gets all symbols from DB.
    - Loops through them and calls `fetch_historical_prices`.
    - Inserts data into DB.

### 5.2. `src/database.py`

#### `get_all_contract_symbols() -> List[str]`
- Queries `options_contracts` to retrieve all available symbols.
- Returns a list of strings (e.g., `['GFGC10177D', ...]`).

#### `insert_market_prices_batch(prices: List[PriceData]) -> None`
- Accepting a list of `PriceData`.
- Using `client.table("market_prices").insert(prices).execute()`.
- *Note*: Supabase supports batch inserts.

## 6. CLI Command
Add a new subcommand to `main.py`:
```bash
python src/main.py fetch history [<date_from>]
```
- `<date_from>` is optional. Defaults to `2025-01-01`.
- Format: `YYYY-MM-DD`.

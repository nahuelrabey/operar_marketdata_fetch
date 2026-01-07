# Populating Market Data with Fetch Contract

This document explains the process of populating the `options_contracts` table in the database using the `fetch_data.py` module (orchestrated via `main.py`).

## 1. Overview

The system needs to store static reference data for option contracts (like strike price, expiration date, type). This information is fetched from the Invertir Online (IOL) API for a specific list of symbols.

## 2. Input Source

The process starts with a list of unique option symbols.
- **File**: `symbols.tmp.json`
- **Location**: Project root.
- **Format**: JSON Array of strings.
  ```json
  [ "GFGC10154D", "GFGC10177D", ... ]
  ```

## 3. Data Acquisition

The script iterates through each symbol in the input file and calls the IOL API.

- **Endpoint**: `GET /api/v2/bCBA/Titulos/{symbol}`
- **Function**: `src.fetch_data.fetch_contract_data(symbol, token)`

### Example API Response
```json
{
  "operableCompra": false,
  "operableVenta": false,
  "visible": true,
  "ultimoPrecio": 16.001,
  "variacion": -36.3,
  "apertura": 28,
  "maximo": 28.1,
  "minimo": 17.002,
  "fechaHora": "2025-12-04T16:59:55.873",
  "tendencia": "mantiene",
  "cierreAnterior": 16.001,
  "montoOperado": 17962645.6,
  "volumenNominal": 0,
  "precioPromedio": 0,
  "moneda": "peso_Argentino",
  "precioAjuste": 0,
  "interesesAbiertos": 0,
  "puntas": [],
  "cantidadOperaciones": 909,
  "simbolo": "GFGC10177D",
  "pais": "argentina",
  "mercado": "bcba",
  "tipo": "opciones",
  "descripcionTitulo": "Call GGAL 10,177.00 Vencimiento: 19/12/2025",
  "plazo": "t0",
  "laminaMinima": 100,
  "lote": 1,
  "cantidadMinima": 1,
  "puntosVariacion": 0
}
```

## 4. Data Mapping & Processing

The raw API response is parsed and mapped to the `ContractData` structure, which aligns with the `options_contracts` table schema.

| Database Column | API Field | Transformation / Logic |
| :--- | :--- | :--- |
| `symbol` | `simbolo` | Direct mapping. |
| `underlying_symbol` | *Derived* | Extracted from `descripcionTitulo` (2nd word). |
| `type` | *Derived* | Extracted from `descripcionTitulo` (1st word: Call/Put). |
| `expiration_date` | *Derived* | Extracted from `descripcionTitulo` after "Vencimiento:". Converted to ISO. |
| `description` | `descripcionTitulo` | Direct mapping. |
| `strike` | *Derived* | Extracted from `descripcionTitulo` using regex. |

### Parsing Logic (from `descripcionTitulo`)
The fields `type`, `underlying_symbol`, `strike`, and `expiration_date` are NOT provided as direct fields in the single-title API response. They must be parsed from the description string, which follows the format:
`"[Type] [Underlying] [Strike] Vencimiento: [Date]"`
*Example*: `"Call GGAL 10,177.00 Vencimiento: 19/12/2025"`

1.  **Type**: The first word (e.g., "Call").
2.  **Underlying**: The second word (e.g., "GGAL").
3.  **Strike**: The third word (e.g., "10,177.00").
4.  **Expiration Date**: The string following "Vencimiento: " (e.g., "19/12/2025"), which is then parsed to a datetime object.

*Implementation*: `src.fetch_data._parse_description`

### Parsing Examples

**Example 1: Call**
Input: `"Call GGAL 10,177.00 Vencimiento: 19/12/2025"`
Output:
```python
{
    'type': 'Call',
    'underlying': 'GGAL',
    'strike': 10177.00,
    'expiration': '2025-12-19T00:00:00'
}
```

**Example 2: Put**
Input: `"Put GGAL 8,500.00 Vencimiento: 20/02/2026"`
Output:
```python
{
    'type': 'Put',
    'underlying': 'GGAL',
    'strike': 8500.00,
    'expiration': '2026-02-20T00:00:00'
}
```

## 5. Database Update - Update on Conflict (Upsert)

The system uses an **Upsert** (Update or Insert) strategy to ensure data potential consistency and handle re-runs gracefully.

1.  **Primary Key**: The table `options_contracts` has `symbol` defined as the Primary Key.
2.  **Logic**:
    - When `src.database.upsert_contract(contract_data)` is called, it sends the data to Supabase using the `.upsert()` method.
    - **If `symbol` does NOT exist**: A new row is inserted.
    - **If `symbol` ALREADY exists**: The existing row is updated with the new values for `underlying_symbol`, `type`, `expiration_date`, `strike`, and `description`.

This ensures that if we run the script multiple times, or if contract details change (e.g., description correction), the database always reflects the latest fetched information without creating duplicates or throwing errors.

## 6. Execution

The process is triggered via the CLI:

```bash
python src/main.py fetch contracts [symbols_file] [access_token]
```

- If `symbols_file` is omitted, it defaults to `symbols.tmp.json`.
- If `access_token` is omitted, it reads from `token.txt`.

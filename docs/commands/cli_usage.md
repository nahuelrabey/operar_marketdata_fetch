# CLI Usage Guide

The tool exposes a Command Line Interface (CLI) via `src/main.py`.

## Fetch Commands

### `fetch chain`
Fetches the entire option chain for a given underlying symbol.
*   **Usage**: `uv run src/main.py fetch chain <symbol> [--username USER] [--password PASS]`
*   **Arguments**:
    *   `symbol`: The underlying symbol (e.g., GGAL).
    *   `--username`: IOL Username (overrides environment variable).
    *   `--password`: IOL Password (overrides environment variable).

### `fetch contracts`
Fetches data for a specific list of contracts defined in a JSON file.
*   **Usage**: `uv run src/main.py fetch contracts [file] [token]`
*   **Arguments**:
    *   `file`: Path to the JSON file containing contract symbols (default: `symbols.tmp.json`).
    *   `token`: Access token (optional).

### `fetch history`
Fetches historical price data for all known contracts in the system.
*   **Usage**: `uv run src/main.py fetch history [date_from] [--token TOKEN]`
*   **Arguments**:
    *   `date_from`: Start date for the history in YYYY-MM-DD format (default: `2025-01-01`).
    *   `--token`: Access token override.

---

## Strategy Commands

### `strategy new`
Creates a new strategy container.
*   **Usage**: `uv run src/main.py strategy new --name NAME [--description DESC]`
*   **Arguments**:
    *   `--name`: Name of the strategy.
    *   `--description`: Optional description.

### `strategy list`
Lists all existing strategies.
*   **Usage**: `uv run src/main.py strategy list`

### `strategy view`
Views the details, composition, and P&L of a specific strategy. Generates a P&L curve plot.
*   **Usage**: `uv run src/main.py strategy view <id>`
*   **Arguments**:
    *   `id`: The ID of the strategy.

### `strategy close`
Marks a strategy as closed.
*   **Usage**: `uv run src/main.py strategy close <id>`
*   **Arguments**:
    *   `id`: The ID of the strategy.

---

## Trade Commands

### `trade add`
Adds a new trade (operation) to a strategy.
*   **Usage**: `uv run src/main.py trade add --strategy ID --symbol SYMBOL --type TYPE --quantity QTY --price PRICE`
*   **Arguments**:
    *   `--strategy`: The ID of the strategy.
    *   `--symbol`: The contract symbol (e.g., GGALC4600O).
    *   `--type`: Operation type (`BUY` or `SELL`).
    *   `--quantity`: Number of contracts.
    *   `--price`: Price per contract.

### `trade remove`
Removes a specific trade from a strategy.
*   **Usage**: `uv run src/main.py trade remove --operation ID --strategy ID`
*   **Arguments**:
    *   `--operation`: The ID of the operation to remove.
    *   `--strategy`: The ID of the strategy (for verification context).

---

## Token Commands

### `token update`
Updates the authentication token using credentials.
*   **Usage**: `uv run src/main.py token update [--username USER] [--password PASS]`
*   **Arguments**:
    *   `--username`: IOL Username (overrides environment variable).
    *   `--password`: IOL Password (overrides environment variable).

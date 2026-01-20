# Fetch Commands

This section details how the data fetching commands work, including the interaction between the CLI, the Controller, and the Database.

## Overview

The `fetch` command group deals with retrieving option chains, individual contracts, and historical price series from the Invertir Online (IOL) API.

## Fetch History Workflow

The `fetch history` command (`handle_fetch_history`) is the most complex operation, designed to backfill price data for all known contracts.

### Command Flow

1. **CLI Layer**: `main.py` receives the command.
2. **Controller**: `fetch_data.py` orchestrates the process.
3. **Database**: `database.py` provides the list of symbols and saves the results.

### Sequence Diagram

```mermaid
sequenceDiagram
    participant User
    participant CLI as Main (handle_fetch_history)
    participant Controller as Fetch Module (process_historical_data)
    participant DB as Database
    participant API as IOL API

    User->>CLI: fetch history [date_from]
    CLI->>Controller: process_historical_data(date_from, token)
    
    rect rgb(240, 248, 255)
        note right of Controller: Step 1: Get Symbols
        Controller->>DB: get_all_contract_symbols()
        DB-->>Controller: [GGALC4600, YPFDC2000, ...]
    end

    loop For each Symbol
        rect rgb(255, 250, 240)
            note right of Controller: Step 2: Fetch API
            Controller->>API: GET /seriehistorica/{symbol}
            API-->>Controller: JSON History Data
        end
        
        rect rgb(240, 255, 240)
            note right of Controller: Step 3: Save Data
            Controller->>DB: insert_market_prices_batch(prices)
            DB-->>Controller: Success
        end
    end
    
    Controller-->>CLI: Finished
    CLI-->>User: "Done. Total records inserted..."
```

## Functions Involved

- [`src.main.handle_fetch_history`][src.main.handle_fetch_history]
- [`src.fetch_data.process_historical_data`][src.fetch_data.process_historical_data]
- [`src.database.get_all_contract_symbols`][src.database.get_all_contract_symbols]
- [`src.fetch_data.fetch_historical_prices`][src.fetch_data.fetch_historical_prices]
- [`src.database.insert_market_prices_batch`][src.database.insert_market_prices_batch]

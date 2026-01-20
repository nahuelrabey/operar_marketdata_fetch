# Strategy Management

This section explains how strategies are managed, visualized, and analyzed.

## Viewing a Strategy

The `strategy view` command aggregates data from multiple sources to present a comprehensive snapshot of a trading strategy, including its composition, current P&L, and payoff profile at expiration.

### Command Flow

1. **Retrieve Details**: Fetches the strategy's operations and contract details from the database.
2. **Fetch Prices**: Gets the latest known prices for the relevant contracts.
3. **Calculate P&L**: Computes the current profit/loss and simulates the expiration curve.
4. **Visualize**: Generates a matplotlib plot.

### Sequence Diagram

```mermaid
sequenceDiagram
    participant User
    participant CLI as Main (handle_strategy_view)
    participant DB as Database
    participant PnL as PnL Module
    participant Plot as Matplotlib

    User->>CLI: strategy view {id}
    
    rect rgb(240, 248, 255)
        note right of CLI: 1. Get Strategy Data
        CLI->>DB: get_position_details(id)
        DB-->>CLI: { operations: [...], composition: [...] }
    end

    rect rgb(255, 250, 240)
        note right of CLI: 2. Get Market Data
        CLI->>DB: get_latest_prices(symbols)
        DB-->>CLI: { GGALC4600: 150.0, ... }
    end

    rect rgb(240, 255, 240)
        note right of CLI: 3. Calculate Math
        CLI->>PnL: calculate_pnl(ops, prices)
        PnL-->>CLI: Total P&L
        
        CLI->>PnL: calculate_pnl_curve_at_finish(ops, ...)
        PnL-->>CLI: (S_T, PnL_Vector)
    end
    
    rect rgb(255, 240, 245)
        note right of CLI: 4. Draw
        CLI->>Plot: plot(S_T, PnL_Vector)
        Plot-->>CLI: File Saved (.png)
    end
    
    CLI-->>User: Display Table & Plot Path
```

## Functions Involved

- [`src.main.handle_strategy_view`][src.main.handle_strategy_view]
- [`src.database.get_position_details`][src.database.get_position_details]
- [`src.pnl.calculate_pnl`][src.pnl.calculate_pnl]
- [`src.pnl.calculate_pnl_curve_at_finish`][src.pnl.calculate_pnl_curve_at_finish]

# Proposal: Parallel `fetch history`

## Goal
Optimize the `fetch history` command to download historical prices for all known contracts in parallel, significantly reducing the total execution time and improving database write efficiency.

## Current State
Currently, `process_historical_data` in `src/fetch_data.py` iterates through all symbols sequentially:
1. Fetch all symbols from the database.
2. For each symbol, make a synchronous API call to the IOL API.
3. Batch insert the fetched historical prices for that symbol into the database.
4. Repeat for the next symbol.

This sequential nature causes the process to be heavily I/O bound by network latency between the app and the API.

## Proposed Changes

We can mirror the architecture already established for `batch_fetch_latest_prices`, leveraging Python's `concurrent.futures.ThreadPoolExecutor`.

### 1. Update `fetch_historical_prices` (Optional but Recommended)
Ensure that exceptions inside the worker thread do not crash the ThreadPool. If `fetch_historical_prices` already returns an empty list `[]` on failure (which it currently does), this is suitable for parallel execution.

### 2. Refactor `process_historical_data`
Rewrite the function to use a `ThreadPoolExecutor`:

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def process_historical_data(date_from_str: str, token: str, max_workers: int = 10) -> None:
    # Parse dates and get symbols as usual
    date_from = datetime.strptime(date_from_str, "%Y-%m-%d")
    date_to = datetime.now()
    symbols = get_all_contract_symbols()
    
    print(f"Found {len(symbols)} symbols. Starting parallel backfill with {max_workers} workers...")
    
    total_records = 0
    prices_accumulator = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_symbol = {
            executor.submit(fetch_historical_prices, sym, date_from, date_to, token): sym 
            for sym in symbols
        }
        
        for future in as_completed(future_to_symbol):
            symbol = future_to_symbol[future]
            try:
                # Retrieve the historical prices (List[PriceData])
                prices = future.result()
                if prices:
                    prices_accumulator.extend(prices)
                    print(f"  > Received {len(prices)} historical records for {symbol}.")
                else:
                    print(f"  > No data for {symbol}.")
            except Exception as e:
                print(f"Error fetching history for {symbol}: {e}")
            
            # Write to database in chunks to avoid memory bloat and optimize DB trips
            # Because historical data lists can be longer, we batch by total accumulated records
            if len(prices_accumulator) >= 2000:
                insert_market_prices_batch(prices_accumulator)
                total_records += len(prices_accumulator)
                prices_accumulator = []

    # Final flush
    if prices_accumulator:
        insert_market_prices_batch(prices_accumulator)
        total_records += len(prices_accumulator)

    print(f"Done. Total historical records inserted: {total_records}")
```

### 3. Consider Rate Limits (Optional)
If IOL API has strict rate limits, we should document or introduce a short backoff/retry in `fetch_historical_prices`. However, the concurrency level (`max_workers=10`) usually respects typical REST limits without issue.

## Benefits
- **Drastic Speed Improvement**: Multiple network requests execute concurrently instead of one by one.
- **Efficient DB Writes**: By decoupling the API fetch from the DB insert logic (batching in the main thread with a size threshold instead of per-symbol), database connections are utilized more optimally.
- **Consistency**: Bring the history fetching logic in line with `fetch latest`, standardizing the codebase.

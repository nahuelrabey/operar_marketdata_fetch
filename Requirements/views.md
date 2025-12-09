# Table Views

## Read the newest price from `market_prices` table

From each contract in `options_contracts` fetch the newest price from `market_prices` table.

```sql
WITH LatestPrices AS (
    SELECT
        contract_symbol,
        price,
        system_timestamp,
        ROW_NUMBER() OVER(PARTITION BY contract_symbol ORDER BY system_timestamp DESC) as rn
    FROM
        market_prices
)
SELECT
    oc.symbol,
    lp.price,
    lp.system_timestamp
FROM
    options_contracts oc
JOIN
    LatestPrices lp ON oc.symbol = lp.contract_symbol
WHERE
    lp.rn = 1;
```

## Get a list of the `system_timestamps` from `market_prices` table

Dont show repeated timestamps.

```sql
SELECT DISTINCT system_timestamp
FROM market_prices
ORDER BY system_timestamp DESC;
```




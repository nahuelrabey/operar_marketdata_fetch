# Database Proposal

## Recommended Service: Supabase
For your requirement of a **free, online, and simple-to-configure** SQL database, I recommend **[Supabase](https://supabase.com/)**.

### Why Supabase?
- **Free Tier**: Generous free tier (500MB storage) which is sufficient for millions of market data records.
- **PostgreSQL**: Built on standard PostgreSQL, the world's most advanced open-source relational database.
- **Easy Configuration**: Provides a direct connection string compatible with Python libraries like `psycopg2` or `SQLAlchemy`.
- **Web Interface**: Excellent dashboard to view and manage your data table manually if needed.

---

## Proposed Table Structure
To optimize storage and keep data organized, we should normalize the data into two tables: one for the static contract details and one for the time-series price data.

### 1. Table: `options_contracts`
Stores the static information about the option symbol. This data rarely changes.

| Column Name | Type | Description |
| :--- | :--- | :--- |
| **`symbol`** | `VARCHAR` (PK) | The unique option symbol (e.g., `GFGC26549D`). Primary Key. |
| `underlying_symbol` | `VARCHAR` | The stock symbol (e.g., `GGAL`). |
| `type` | `VARCHAR` | `Call` or `Put`. |
| `expiration_date` | `TIMESTAMP` | The expiration date of the option. |
| `strike` | `DECIMAL` | The strike price of the option. |
| `description` | `VARCHAR` | Human-readable description. |

### 2. Table: `market_prices`
Stores the price information fetched at specific times. This table will grow every time you run the script.

| Column Name | Type | Description |
| :--- | :--- | :--- |
| **`id`** | `SERIAL` (PK) | Auto-incrementing unique ID. |
| `contract_symbol` | `VARCHAR` (FK) | Foreign Key referencing `options_contracts.symbol`. |
| `price` | `DECIMAL` | The last price (`ultimoPrecio`) |
| `timestamp` | `TIMESTAMP` | The time of the data point (`fechaHora`). |
| `volume` | `INTEGER` | Optional: Volume traded (`volumenNominal`). |

### 3. Table: `positions` (Strategy Container)
Represents a high-level strategy or "complex position" (e.g., "Mariposa GGAL"). This is the parent entity.

| Column Name | Type | Description |
| :--- | :--- | :--- |
| **`id`** | `SERIAL` (PK) | Unique position ID. |
| `name` | `VARCHAR` | Name of the strategy (e.g., "Long Call GGAL"). |
| `status` | `VARCHAR` | State of the position ('OPEN', 'CLOSED'). |
| `created_at` | `TIMESTAMP` | Creation date. |

### 4. Table: `operations` (Trades)
Stores individual buy/sell transactions. Each operation belongs to a specific `position`.

| Column Name | Type | Description |
| :--- | :--- | :--- |
| **`id`** | `SERIAL` (PK) | Unique operation ID. |
| `position_id` | `INTEGER` (FK) | Reference to the `positions` table. |
| `contract_symbol` | `VARCHAR` (FK) | Reference to `options_contracts.symbol`. |
| `operation_type` | `VARCHAR` | 'BUY' or 'SELL'. |
| `quantity` | `INTEGER` | Number of contracts traded. |
| `price` | `DECIMAL` | Premium per contract at the time of trade. |
| `operation_date` | `TIMESTAMP` | When the trade occurred. |


### Observations

Notice that "price" in the `market_prices` and `operations` tables is the last price (`ultimoPrecio`), this is also called the premium of the option.

### SQL Creation Script
```sql
-- Create Contracts Table
CREATE TABLE options_contracts (
    symbol VARCHAR(50) PRIMARY KEY,
    underlying_symbol VARCHAR(20),
    type VARCHAR(10),
    expiration_date TIMESTAMP,
    strike DECIMAL(10, 3),
    description TEXT
);

-- Create Prices Table
CREATE TABLE market_prices (
    id SERIAL PRIMARY KEY,
    contract_symbol VARCHAR(50) REFERENCES options_contracts(symbol),
    price DECIMAL(10, 3),
    timestamp TIMESTAMP,
    volume INTEGER
);

-- Create Positions Table (The Strategy/Container)
-- Represents a high-level position or strategy (e.g., "Mariposa GGAL")
CREATE TABLE positions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    description TEXT,
    status VARCHAR(20) DEFAULT 'OPEN', -- OPEN, CLOSED
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create Operations Table (Individual Trades linked to a Position)
CREATE TABLE operations (
    id SERIAL PRIMARY KEY,
    position_id INTEGER REFERENCES positions(id),
    contract_symbol VARCHAR(50) REFERENCES options_contracts(symbol),
    operation_type VARCHAR(4) CHECK (operation_type IN ('BUY', 'SELL')),
    quantity INTEGER NOT NULL,
    price DECIMAL(10, 3) NOT NULL, -- Premium per contract
    operation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```
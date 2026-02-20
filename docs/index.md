# Market Data Tool Documentation

Welcome to the **Market Data Tool** documentation. This project helps in downloading, storing, and analyzing options market data from the "Invertir Online" API.

## Quick Start

### Installation
1. Clone the repository.
2. Install dependencies: `uv sync`.
3. Set up `.env` with your `SUPABASE_URL`, `SUPABASE_KEY`, `IOL_USERNAME`, and `IOL_PASSWORD`.

### Basic Usage
Fetch the latest option chain for a symbol:
```bash
uv run src/main.py fetch chain GGAL
```

Explore the **User Guide** for more detailed instructions.

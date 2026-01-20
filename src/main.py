import argparse
import sys
import os
import matplotlib.pyplot as plt
from typing import List
from tabulate import tabulate
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import database, fetch_data, pnl
# We need to import login to get the token, but login.py is simple and interactive? 
# Let's assume for now we might need a token. 
# fetch_data.fetch_option_chain needs a token.
from src import login

def main():
    """
    Entry point for the Market Data CLI.
    Parses arguments and dispatches commands to handlers.
    """
    parser = argparse.ArgumentParser(description="Market Data CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # --- Fetch Command ---
    fetch_parser = subparsers.add_parser("fetch", help="Fetch market data")
    fetch_subparsers = fetch_parser.add_subparsers(dest="fetch_command", help="Fetch actions")

    # Fetch: Chain
    fetch_chain = fetch_subparsers.add_parser("chain", help="Fetch option chain for a symbol")
    fetch_chain.add_argument("symbol", help="Underlying symbol (e.g., GGAL)")
    fetch_chain.add_argument("--username", help="IOL Username (overrides env var)")
    fetch_chain.add_argument("--password", help="IOL Password (overrides env var)")
    
    # Fetch: Contracts
    fetch_contracts = fetch_subparsers.add_parser("contracts", help="Fetch specific contracts from list")
    fetch_contracts.add_argument("file", nargs="?", default="symbols.tmp.json", help="Path to symbols JSON file")
    fetch_contracts.add_argument("token", nargs="?", help="Access Token")

    # Fetch: History (NEW)
    fetch_history = fetch_subparsers.add_parser("history", help="Fetch historical prices for all known contracts")
    fetch_history.add_argument("date_from", nargs='?', help="Start date YYYY-MM-DD (default: 2025-01-01)")
    fetch_history.add_argument("--token", help="Access Token override")

    # --- Prices Command ---
    prices_parser = subparsers.add_parser("prices", help="List latest prices for a symbol")
    prices_parser.add_argument("symbol", help="Underlying symbol (e.g., GGAL)")

    # --- Strategy Commands ---
    strategy_parser = subparsers.add_parser("strategy", help="Manage strategies")
    strategy_subparsers = strategy_parser.add_subparsers(dest="strategy_command", help="Strategy actions")

    # Strategy: New
    strat_new = strategy_subparsers.add_parser("new", help="Create a new strategy")
    strat_new.add_argument("--name", required=True, help="Strategy name")
    strat_new.add_argument("--description", default="", help="Description")

    # Strategy: List
    strategy_subparsers.add_parser("list", help="List all strategies")

    # Strategy: View
    strat_view = strategy_subparsers.add_parser("view", help="View strategy details and P&L")
    strat_view.add_argument("id", type=int, help="Strategy ID")

    # Strategy: Close
    strat_close = strategy_subparsers.add_parser("close", help="Close a strategy")
    strat_close.add_argument("id", type=int, help="Strategy ID")

    # --- Trade Commands ---
    trade_parser = subparsers.add_parser("trade", help="Manage trades")
    trade_subparsers = trade_parser.add_subparsers(dest="trade_command", help="Trade actions")

    # Trade: Add
    trade_add = trade_subparsers.add_parser("add", help="Add a trade to a strategy")
    trade_add.add_argument("--strategy", type=int, required=True, help="Strategy ID")
    trade_add.add_argument("--symbol", required=True, help="Contract Symbol")
    trade_add.add_argument("--type", required=True, choices=['BUY', 'SELL'], help="Operation Type")
    trade_add.add_argument("--quantity", type=int, required=True, help="Quantity")
    trade_add.add_argument("--price", type=float, required=True, help="Price per contract")

    # Trade: Remove
    trade_remove = trade_subparsers.add_parser("remove", help="Remove a trade")
    trade_remove.add_argument("--operation", type=int, required=True, help="Operation ID")
    trade_remove.add_argument("--strategy", type=int, required=True, help="Strategy ID (for context)")

    # --- Token Commands ---
    token_parser = subparsers.add_parser("token", help="Manage access token")
    token_subparsers = token_parser.add_subparsers(dest="token_command", help="Token actions")

    # Token: Update
    token_update = token_subparsers.add_parser("update", help="Update access token")
    token_update.add_argument("--username", help="IOL Username")
    token_update.add_argument("--password", help="IOL Password")

    # Parse arguments
    args = parser.parse_args()

    # Initialize DB (idempotent)
    database.initialize_db()

    if args.command == "fetch":
        if args.fetch_command == "chain":
            handle_fetch_chain(args.symbol, args.username, args.password)
        elif args.fetch_command == "contracts":
            handle_fetch_contracts(args.file, args.token)
        elif args.fetch_command == "history":
            handle_fetch_history(args.date_from, args.token)
        else: 
            # Backwards compatibility or default behavior if user typed just 'fetch GGAL' 
            # (which is broken now that we have subparsers, but let's assume user follows new structure)
            # Actually, `add_subparsers` makes the sub-command required usually unless configured otherwise.
            fetch_parser.print_help()

    elif args.command == "prices":
        handle_prices(args.symbol)
    elif args.command == "strategy":
        if args.strategy_command == "new":
            handle_strategy_new(args.name, args.description)
        elif args.strategy_command == "list":
            handle_strategy_list()
        elif args.strategy_command == "view":
            handle_strategy_view(args.id)
        elif args.strategy_command == "close":
            handle_strategy_close(args.id)
        else:
            strategy_parser.print_help()
    elif args.command == "trade":
        if args.trade_command == "add":
            handle_trade_add(args.strategy, args.symbol, args.type, args.quantity, args.price)
        elif args.trade_command == "remove":
            handle_trade_remove(args.strategy, args.operation)
        else:
            trade_parser.print_help()
    elif args.command == "token":
        if args.token_command == "update":
            handle_token_update(args.username, args.password)
        else:
            token_parser.print_help()
    else:
        parser.print_help()

def handle_fetch_chain(symbol: str, cli_user: str = None, cli_pass: str = None):
    """
    Handles fetching and saving the full option chain for a symbol.
    Authenticates first to get a token.

    Args:
        symbol: The underlying ticker.
        cli_user: Optional username override.
        cli_pass: Optional password override.
    """
    print(f"Authenticating...")

    try:
        # Prioritize CLI args, then Env vars
        username = cli_user or os.environ.get("IOL_USERNAME", "")
        password = cli_pass or os.environ.get("IOL_PASSWORD", "")
        
        if not username or not password:
             print("Error: Username and Password are required.")
             print("Please provide them via --username and --password arguments")
             print("OR set IOL_USERNAME and IOL_PASSWORD environment variables.")
             return

        auth_response = login.authenticate(username, password)
        token = auth_response['access_token']
        print(f"Fetching data for {symbol}...")
        contracts, prices = fetch_data.fetch_option_chain(symbol, token)
        
        print(f"Saving {len(contracts)} contracts and {len(prices)} prices...")
        
        count_new_contracts = 0
        for c in contracts:
            database.upsert_contract(c)
            count_new_contracts += 1
            
        count_new_prices = 0
        for p in prices:
            database.insert_market_price(p)
            count_new_prices += 1
            
        print(f"Done. Processed {count_new_contracts} contracts and {count_new_prices} price points.")
        
    except Exception as e:
        print(f"Error fetching data: {e}")

def handle_fetch_contracts(file_path: str, token: str):
    """
    Handles fetching data for a specific list of contracts.

    Args:
        file_path: Path to the JSON file with symbols.
        token: Access token (or loads from token.txt).
    """
    # Defaults
    file_path = file_path or "symbols.tmp.json"
    token_path = "token.txt"
    
    try:
        # Try to load token from file if not provided
        if not token:
            if os.path.exists(token_path):
                with open(token_path, 'r', encoding='utf-8') as f:
                    token = f.read().strip()
                print(f"Loaded token from {token_path}")
            else:
                print(f"Error: Token not provided and {token_path} not found.")
                return # Exit gracefully
        
        # Check symbols file
        if not os.path.exists(file_path):
             print(f"Error: Symbols file '{file_path}' not found.")
             return

        fetch_data.process_symbols_list(file_path, token)
        print("Done.")
    except Exception as e:
        print(f"Error: {e}")

def handle_fetch_history(date_from: str = None, token_arg: str = None):
    """
    Handles the bulk history fetch command.

    Args:
        date_from: Start date YYYY-MM-DD.
        token_arg: Access token.
    """
    # Load token
    token = token_arg
    if not token and os.path.exists("token.txt"):
        with open("token.txt", "r") as f:
            token = f.read().strip()
            
    if not token:
        print("Error: No access token provided and token.txt not found.")
        return

    # Default date
    d_from = date_from if date_from else "2025-01-01"
    
    print(f"Fetching historical data starting from {d_from}...")
    fetch_data.process_historical_data(d_from, token)

def handle_prices(symbol: str):
    """
    Prints the latest prices for a symbol in a tabular format.

    Args:
        symbol: The underlying ticker.
    """
    prices = database.get_latest_prices_by_underlying(symbol)
    if not prices:
        print(f"No prices found for {symbol}.")
        return
        
    # Prepare table
    table_data = []
    # Keys: symbol, type, strike, price, timestamp
    for p in prices:
        table_data.append([
            p['symbol'], 
            p['type'], 
            f"{p['strike']:.2f}", 
            f"${p['price']:.2f}", 
            p['timestamp']
        ])
        
    print(tabulate(table_data, headers=["Symbol", "Type", "Strike", "Price", "Timestamp"], tablefmt="simple"))

def handle_strategy_new(name: str, description: str):
    """Creates a new strategy."""
    try:
        new_id = database.create_position(name, description)
        print(f"Strategy created successfully. ID: {new_id}")
    except Exception as e:
        print(f"Error creating strategy: {e}")

def handle_strategy_list():
    """Lists all strategies."""
    positions = database.get_positions()
    if not positions:
        print("No strategies found.")
        return
        
    data = [[p['id'], p['name'], p['status'], p['created_at']] for p in positions]
    print(tabulate(data, headers=["ID", "Name", "Status", "Created At"], tablefmt="simple"))

def handle_strategy_view(position_id: int):
    """
    Deep look into a strategy: shows composition, P&L, and generates a plot.

    Args:
        position_id: Strategy ID.
    """
    try:
        details = database.get_position_details(position_id)
        # We need to calculate P&L here using pnl.py
        
        # 1. Get latest prices for the contracts in the strategy
        # details['operations'] has the contracts.
        # We need 'database' to have a function to get latest prices for a list of symbols OR
        # 'get_position_details' might have done it?
        # modules_design.md says: get_position_details -> Returns PositionDetails which has 'current_pnl'.
        # But looking at src/database.py:
        # It calculates 'composition' but 'pnl' is delegated? 
        # Actually in the code of database.py I read earlier:
        # It returns {'operations': ..., 'composition': ...}
        # It DOES NOT calculate P&L.
        
        # So Main needs to orchestrate P&L calculation.
        
        ops = details['operations']
        if not ops:
            print("Strategy has no trades.")
            return

        symbols = list(set(op['contract_symbol'] for op in ops))
        current_prices_map = database.get_latest_prices(symbols) # Need to verify this exists or implement helper
        
        # Checking database.py read content:
        # Yes, `get_latest_prices(symbols)` exists!
        
        # Calculate Current P&L
        total_pnl, _ = pnl.calculate_pnl(ops, current_prices_map)
        
        print(f"\n--- Strategy {position_id} ---")
        print(f"Current P&L: ${total_pnl:.2f}")
        
        print("\nComposition:")
        comp_data = [[c['symbol'], c['net_quantity']] for c in details['composition']]
        print(tabulate(comp_data, headers=["Symbol", "Net Qty"], tablefmt="simple"))
        
        # Calculate Curve
        # We need a current underlying price. This is tricky. 
        # Usually we take the underlying price from the market data or one of the options (less accurate).
        # Or we ask the user. 
        # For now, let's try to infer from the first option's underlying... but we don't have underlying price explicitly in the DB market_prices usually?
        # Actually `market_prices` is for options. 
        # Let's assume we use the Strike of a representative option as a center or simply 
        # logic: Get average strike of positions as center.
        avg_strike = sum(float(op['strike']) for op in ops) / len(ops)
        
        S_T, pnl_curve = pnl.calculate_pnl_curve_at_finish(ops, avg_strike)
        
        # Plot
        plt.figure(figsize=(10, 6))
        plt.plot(S_T, pnl_curve, label='P&L at Expiration')
        plt.axhline(0, color='black', linewidth=0.5)
        plt.axvline(avg_strike, color='gray', linestyle='--')
        plt.title(f"Strategy {position_id} P&L Profile")
        plt.xlabel("Underlying Price")
        plt.ylabel("P&L ($)")
        plt.grid(True)
        plt.legend()
        
        # Save plot
        plot_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'plots')
        os.makedirs(plot_dir, exist_ok=True)
        plot_path = os.path.join(plot_dir, f"strategy_{position_id}_pnl.png")
        plt.savefig(plot_path)
        plt.close()
        
        print(f"\nP&L Curve saved to: {plot_path}")

    except Exception as e:
        print(f"Error viewing strategy: {e}")

def handle_strategy_close(position_id: int):
    """Closes a strategy."""
    if database.close_position(position_id):
        print(f"Strategy {position_id} closed.")
    else:
        print("Failed to close strategy.")

def handle_trade_add(strategy_id: int, symbol: str, op_type: str, qty: int, price: float):
    """Adds a trade to a strategy."""
    # Need operation_date, defaulting to now
    op_data = {
        'contract_symbol': symbol,
        'operation_type': op_type,
        'quantity': qty,
        'price': price,
        'operation_date': datetime.now().isoformat()
    }
    try:
        op_id = database.add_operation(strategy_id, op_data)
        print(f"Trade added. Operation ID: {op_id}")
    except Exception as e:
        print(f"Error adding trade: {e}")

def handle_trade_remove(strategy_id: int, operation_id: int):
    """Removes a trade from a strategy."""
    try:
        if database.remove_operation_from_position(strategy_id, operation_id):
             print("Trade removed from strategy.")
        else:
             print("Failed to remove trade.")
    except Exception as e:
        print(f"Error removing trade: {e}")

def handle_token_update(cli_user: str = None, cli_pass: str = None):
    """Updates the access token using credentials."""
    print("Updating access token...")
    try:
        # Prioritize CLI args, then Env vars
        username = cli_user or os.environ.get("IOL_USERNAME", "")
        password = cli_pass or os.environ.get("IOL_PASSWORD", "")
        
        if not username or not password:
             print("Error: Username and Password are required.")
             print("Please provide them via --username and --password arguments")
             print("OR set IOL_USERNAME and IOL_PASSWORD environment variables.")
             return

        auth_data = login.authenticate(username, password)
        
        expires_in = auth_data.get('expires_in')
        issued = auth_data.get('.issued')
        expires = auth_data.get('.expires')
        
        print("\nToken updated successfully.")
        if expires:
            print(f"Token expires at: {expires}")
        elif expires_in:
            print(f"Token expires in: {expires_in} seconds")
            
    except Exception as e:
        print(f"Error updating token: {e}")

if __name__ == "__main__":
    main()


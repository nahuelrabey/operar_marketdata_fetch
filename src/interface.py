import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
from typing import Dict, Any, List
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np

from src import login, fetch_data, database, pnl
# import login
# import fetch_data
# import database
# import pnl

class MarketDataApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Market Data Manager")
        self.geometry("1024x768")
        
        # Initialize DB
        database.initialize_db()
        
        # Configure Style
        style = ttk.Style()
        default_font = ('Helvetica', 11)
        style.configure('.', font=default_font)
        style.configure('Treeview', font=default_font, rowheight=25)
        style.configure('Treeview.Heading', font=('Helvetica', 11, 'bold'))
        self.option_add("*Font", default_font)
        
        # Main Notebook
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill='both', expand=True)
        
        # Tabs
        self.login_tab = LoginTab(self.notebook)
        self.market_data_tab = MarketDataTab(self.notebook)
        self.prices_tab = PricesTab(self.notebook)
        self.strategies_tab = StrategiesTab(self.notebook)
        
        self.notebook.add(self.login_tab, text="Login")
        self.notebook.add(self.market_data_tab, text="Market Data")
        self.notebook.add(self.prices_tab, text="Prices")
        self.notebook.add(self.strategies_tab, text="Strategies")

class LoginTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Auth Frame
        auth_frame = ttk.LabelFrame(self, text="Authentication")
        auth_frame.pack(fill='x', pady=10)
        
        ttk.Label(auth_frame, text="Username:").grid(row=0, column=0, padx=5, pady=5, sticky='e')
        self.entry_username = ttk.Entry(auth_frame)
        self.entry_username.grid(row=0, column=1, padx=5, pady=5, sticky='ew')
        
        ttk.Label(auth_frame, text="Password:").grid(row=1, column=0, padx=5, pady=5, sticky='e')
        self.entry_password = ttk.Entry(auth_frame, show="*")
        self.entry_password.grid(row=1, column=1, padx=5, pady=5, sticky='ew')
        
        self.btn_login = ttk.Button(auth_frame, text="Login", command=self.perform_login)
        self.btn_login.grid(row=2, column=1, padx=5, pady=10, sticky='e')
        
        auth_frame.columnconfigure(1, weight=1)
        
        # Status Frame
        status_frame = ttk.LabelFrame(self, text="Status")
        status_frame.pack(fill='x', pady=10)
        
        ttk.Label(status_frame, text="Token:").grid(row=0, column=0, padx=5, pady=5, sticky='e')
        self.entry_token = ttk.Entry(status_frame, state='readonly')
        self.entry_token.grid(row=0, column=1, padx=5, pady=5, sticky='ew')
        
        self.lbl_status = ttk.Label(status_frame, text="Not Logged In", foreground="red")
        self.lbl_status.grid(row=1, column=1, padx=5, pady=5, sticky='w')
        
        status_frame.columnconfigure(1, weight=1)

    def perform_login(self):
        username = self.entry_username.get()
        password = self.entry_password.get()
        
        if not username or not password:
            messagebox.showerror("Error", "Please enter username and password")
            return
            
        try:
            token = login.authenticate(username, password)
            self.entry_token.config(state='normal')
            self.entry_token.delete(0, tk.END)
            self.entry_token.insert(0, token)
            self.entry_token.config(state='readonly')
            
            self.lbl_status.config(text="Login Successful", foreground="green")
            messagebox.showinfo("Success", "Login Successful")
        except Exception as e:
            self.lbl_status.config(text="Login Failed", foreground="red")
            messagebox.showerror("Login Error", str(e))

class MarketDataTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Controls
        controls_frame = ttk.LabelFrame(self, text="Fetch Options Data")
        controls_frame.pack(fill='x', pady=10)
        
        ttk.Label(controls_frame, text="Underlying Symbol:").pack(side='left', padx=5)
        self.entry_symbol = ttk.Entry(controls_frame)
        self.entry_symbol.insert(0, "GGAL")
        self.entry_symbol.pack(side='left', padx=5)
        
        self.btn_fetch = ttk.Button(controls_frame, text="Fetch Data", command=self.start_fetch_thread)
        self.btn_fetch.pack(side='left', padx=5)
        
        # Logs
        log_frame = ttk.LabelFrame(self, text="Logs")
        log_frame.pack(fill='both', expand=True, pady=10)
        
        self.txt_log = tk.Text(log_frame, height=10)
        self.txt_log.pack(fill='both', expand=True, padx=5, pady=5)
        
    def log(self, message):
        self.txt_log.insert(tk.END, f"{message}\n")
        self.txt_log.see(tk.END)
        
    def start_fetch_thread(self):
        threading.Thread(target=self.fetch_data, daemon=True).start()
        
    def fetch_data(self):
        symbol = self.entry_symbol.get()
        token_widget = self.master.master.login_tab.entry_token # Access token from LoginTab
        token = token_widget.get()
        
        if not token:
            self.log("Error: No token found. Please login first.")
            return
            
        self.btn_fetch.config(state='disabled')
        self.log(f"Fetching data for {symbol}...")
        
        try:
            contracts, prices = fetch_data.fetch_option_chain(symbol, token)
            self.log(f"Received {len(contracts)} contracts.")
            
            # Save to DB
            count = 0
            for contract in contracts:
                database.upsert_contract(contract)
            
            for price in prices:
                database.insert_market_price(price)
                count += 1
                
            self.log(f"Successfully saved {count} price records to database.")
            
        except Exception as e:
            self.log(f"Error: {str(e)}")
        finally:
            self.btn_fetch.config(state='normal')

class PricesTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Controls
        controls_frame = ttk.Frame(self)
        controls_frame.pack(fill='x', pady=10)
        
        ttk.Label(controls_frame, text="Underlying Symbol:").pack(side='left', padx=5)
        self.entry_symbol = ttk.Entry(controls_frame)
        self.entry_symbol.insert(0, "GGAL")
        self.entry_symbol.pack(side='left', padx=5)
        
        self.btn_search = ttk.Button(controls_frame, text="Search", command=self.search_prices)
        self.btn_search.pack(side='left', padx=5)
        
        # Table
        columns = ('symbol', 'type', 'strike', 'last', 'time')
        self.tree = ttk.Treeview(self, columns=columns, show='headings')
        
        self.tree.heading('symbol', text='Symbol')
        self.tree.heading('type', text='Type')
        self.tree.heading('strike', text='Strike')
        self.tree.heading('last', text='Last Price')
        self.tree.heading('time', text='Time')
        
        self.tree.column('symbol', width=100)
        self.tree.column('type', width=50)
        self.tree.column('strike', width=80)
        self.tree.column('last', width=80)
        self.tree.column('time', width=150)
        
        self.tree.pack(fill='both', expand=True, pady=10)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.place(relx=1, rely=0, relheight=1, anchor='ne')

    def search_prices(self):
        symbol = self.entry_symbol.get()
        if not symbol:
            return
            
        # Clear existing
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        try:
            results = database.get_latest_prices_by_underlying(symbol)
            
            if not results:
                messagebox.showinfo("Info", "No prices found for this symbol.")
                return
                
            for row in results:
                self.tree.insert('', tk.END, values=(
                    row['symbol'],
                    row['type'],
                    f"{row['strike']:,.2f}",
                    f"{row['price']:,.2f}",
                    row['timestamp']
                ))
        except Exception as e:
            messagebox.showerror("Error", str(e))

class StrategiesTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Paned Window (Split View)
        self.paned = ttk.PanedWindow(self, orient='horizontal')
        self.paned.pack(fill='both', expand=True)
        
        # Left Panel: List
        self.left_panel = ttk.Frame(self.paned, width=200)
        self.paned.add(self.left_panel, weight=1)
        
        ttk.Label(self.left_panel, text="Strategies").pack(pady=5)
        self.list_strategies = tk.Listbox(self.left_panel)
        self.list_strategies.pack(fill='both', expand=True, padx=5)
        self.list_strategies.bind('<<ListboxSelect>>', self.on_strategy_select)
        
        ttk.Button(self.left_panel, text="New Strategy", command=self.new_strategy_dialog).pack(pady=5, fill='x', padx=5)
        ttk.Button(self.left_panel, text="Refresh List", command=self.refresh_list).pack(pady=5, fill='x', padx=5)
        
        # Right Panel: Details
        self.right_panel = ttk.Frame(self.paned)
        self.paned.add(self.right_panel, weight=3)
        
        # Header
        self.lbl_strategy_name = ttk.Label(self.right_panel, text="Select a Strategy", font=('Arial', 14, 'bold'))
        self.lbl_strategy_name.pack(pady=10)
        
        self.lbl_pnl = ttk.Label(self.right_panel, text="Current P&L: $ 0.00", font=('Arial', 12))
        self.lbl_pnl.pack(pady=5)
        
        self.btn_close_strategy = ttk.Button(self.right_panel, text="Close Strategy", command=self.close_strategy)
        self.btn_close_strategy.pack(pady=5)
        
        # Composition Table
        columns = ('symbol', 'net_qty')
        self.tree = ttk.Treeview(self.right_panel, columns=columns, show='headings', height=5)
        self.tree.heading('symbol', text='Symbol')
        self.tree.heading('net_qty', text='Net Qty')
        self.tree.pack(fill='x', padx=10, pady=10)
        
        # Graph Canvas
        self.figure, self.ax = plt.subplots(figsize=(5, 3))
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.right_panel)
        self.canvas.get_tk_widget().pack(fill='both', expand=True, padx=10, pady=10)
        
        # Actions
        actions_frame = ttk.Frame(self.right_panel)
        actions_frame.pack(pady=10)
        
        ttk.Button(actions_frame, text="Add Trade", command=self.add_trade_dialog).pack(side='left', padx=5)
        ttk.Button(actions_frame, text="Remove Trade", command=self.remove_trade_dialog).pack(side='left', padx=5)
        
        self.current_position_id = None
        self.refresh_list()

    def refresh_list(self):
        self.list_strategies.delete(0, tk.END)
        self.positions = database.get_positions()
        for pos in self.positions:
            status = pos['status']
            name = f"{pos['name']} ({status})"
            self.list_strategies.insert(tk.END, name)

    def new_strategy_dialog(self):
        name = simpledialog.askstring("New Strategy", "Strategy Name:")
        if name:
            desc = simpledialog.askstring("New Strategy", "Description:") or ""
            database.create_position(name, desc)
            self.refresh_list()

    def on_strategy_select(self, event):
        selection = self.list_strategies.curselection()
        if not selection:
            return
            
        index = selection[0]
        position = self.positions[index]
        self.current_position_id = position['id']
        self.load_strategy_details(position)

    def load_strategy_details(self, position):
        self.lbl_strategy_name.config(text=position['name'])
        
        # Get Details
        details = database.get_position_details(position['id'])
        composition = details['composition']
        operations = details['operations']
        
        # Update Tree
        for item in self.tree.get_children():
            self.tree.delete(item)
        for item in composition:
            self.tree.insert('', tk.END, values=(item['symbol'], item['net_quantity']))
            
        # Calculate P&L
        # 1. Get current prices
        symbols = [op['contract_symbol'] for op in operations]
        prices_map = database.get_latest_prices(list(set(symbols)))
        
        # 2. Calc Current P&L
        total_pnl, _ = pnl.calculate_pnl(operations, prices_map)
        self.lbl_pnl.config(text=f"Current P&L: $ {total_pnl:,.2f}")
        
        # 3. Calc P&L Curve
        # Estimate underlying price (heuristic: take strike of first option or 0)
        current_underlying = 0.0
        if operations:
             # Try to find a strike
             first_op = operations[0]
             current_underlying = float(first_op.get('strike', 0))
             # Or try to get it from contract metadata if we had it easily accessible
        
        if current_underlying > 0:
            S_T, pnl_curve = pnl.calculate_pnl_curve_at_finish(operations, current_underlying)
            
            # Plot
            self.ax.clear()
            self.ax.plot(S_T, pnl_curve, label='P&L at Expiration')
            self.ax.axhline(0, color='black', linewidth=0.5)
            self.ax.set_title("P&L Profile")
            self.ax.set_xlabel("Underlying Price")
            self.ax.set_ylabel("P&L")
            self.ax.grid(True)
            self.canvas.draw()
        else:
            self.ax.clear()
            self.canvas.draw()

    def add_trade_dialog(self):
        if not self.current_position_id:
            return
            
        # Simple dialog for now. In a real app, use a custom Toplevel with Comboboxes.
        symbol = simpledialog.askstring("Add Trade", "Contract Symbol:")
        if not symbol: return
        
        op_type = simpledialog.askstring("Add Trade", "Type (BUY/SELL):")
        if op_type not in ['BUY', 'SELL']: return
        
        qty = simpledialog.askinteger("Add Trade", "Quantity:")
        if not qty: return
        
        price = simpledialog.askfloat("Add Trade", "Price:")
        if price is None: return
        
        op_data = {
            'contract_symbol': symbol,
            'operation_type': op_type,
            'quantity': qty,
            'price': price,
            'operation_date': '' # Database defaults to current
        }
        
        try:
            database.add_operation(self.current_position_id, op_data)
            # Refresh details
            pos = next(p for p in self.positions if p['id'] == self.current_position_id)
            self.load_strategy_details(pos)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def remove_trade_dialog(self):
        if not self.current_position_id:
            return
            
        # Get operations for current position
        try:
            details = database.get_position_details(self.current_position_id)
            operations = details['operations']
            
            if not operations:
                messagebox.showinfo("Info", "No trades to remove.")
                return
                
            # Create a simple selection dialog (in real app, use a custom Toplevel with listbox)
            # For now, we'll just list them and ask for ID (simplified for this iteration)
            # Better approach: Show a list of operations in a new window
            
            win = tk.Toplevel(self)
            win.title("Remove Trade")
            win.geometry("400x300")
            
            lb = tk.Listbox(win)
            lb.pack(fill='both', expand=True, padx=10, pady=10)
            
            for op in operations:
                lb.insert(tk.END, f"ID {op['id']}: {op['operation_type']} {op['quantity']} {op['contract_symbol']} @ {op['price']}")
                
            def on_remove():
                selection = lb.curselection()
                if not selection:
                    return
                
                index = selection[0]
                op_to_remove = operations[index]
                
                if messagebox.askyesno("Confirm", f"Remove trade {op_to_remove['id']}?"):
                    try:
                        database.remove_operation_from_position(self.current_position_id, op_to_remove['id'])
                        # Refresh
                        pos = next(p for p in self.positions if p['id'] == self.current_position_id)
                        self.load_strategy_details(pos)
                        win.destroy()
                    except Exception as e:
                        messagebox.showerror("Error", str(e))
            
            ttk.Button(win, text="Remove Selected", command=on_remove).pack(pady=10)
            
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def close_strategy(self):
        if not self.current_position_id:
            return
        if messagebox.askyesno("Confirm", "Close this strategy?"):
            database.close_position(self.current_position_id)
            self.refresh_list()

if __name__ == "__main__":
    app = MarketDataApp()
    app.mainloop()

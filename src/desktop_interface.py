import tkinter as tk
from tkinter import messagebox
import login
import fetch_data

def main():
    root = tk.Tk()
    root.title("Market Data Interface")
    root.geometry("400x400")

    # --- Login Section ---
    def on_login_click():
        # Call login UI from login module
        # We need login.get_user_credentials to return the token or we read it from file
        # The requirement says "It will have a button to fetch the token from the Login module"
        # and "If the login is successful, it will show a message..."
        
        # Let's assume we modify login.py to return the token if successful, 
        # or we check the file after the login UI closes.
        
        # Trigger login UI
        login.get_user_credentials(root)
        
        # Check for token
        token = fetch_data.get_token_from_file()
        if token:
            show_login_success(token)

    def show_login_success(token):
        # Clear previous success frame if any (optional, for simplicity just pack new one)
        success_frame = tk.Frame(root, relief="groove", borderwidth=2)
        success_frame.pack(fill='x', padx=20, pady=10)
        
        tk.Label(success_frame, text="Login successful.", font=("Arial", 10, "bold"), fg="green").pack(pady=5)
        
        token_text = tk.Text(success_frame, height=3, width=30)
        token_text.insert("1.0", token)
        token_text.config(state="disabled")
        token_text.pack(pady=5, padx=5)
        
        def copy_to_clipboard():
            root.clipboard_clear()
            root.clipboard_append(token)
            messagebox.showinfo("Copied", "Token copied to clipboard!")

        tk.Button(success_frame, text="Copy Token", command=copy_to_clipboard).pack(pady=5)

    btn_login = tk.Button(root, text="Login / Fetch Token", command=on_login_click, height=2)
    btn_login.pack(pady=20, padx=20, fill='x')

    # --- Fetch Data Section ---
    def on_fetch_click():
        # Check token first
        token = fetch_data.get_token_from_file()
        if not token:
            messagebox.showerror("Error", "No token found. Please login first.")
            return

        # Get symbol
        symbol = fetch_data.get_stock_symbol_ui()
        if not symbol:
            return # Cancelled

        # Show fetching status
        lbl_fetch_success.config(text="Fetching option chain...", fg="black")
        root.update() # Force UI update

        # Fetch data
        data = fetch_data.fetch_option_chain(token, symbol)
        
        if data:
            fetch_data.save_to_csv(data, symbol)
            messagebox.showinfo("Success", "Option chain fetched successfully.")
            
            # Show success message on UI as well
            lbl_fetch_success.config(text="Option chain fetched successfully.", fg="blue")
        else:
            lbl_fetch_success.config(text="Failed to fetch option chain.", fg="red")
            messagebox.showerror("Error", "Failed to fetch option chain.")

    btn_fetch = tk.Button(root, text="Fetch Option Chain", command=on_fetch_click, height=2)
    btn_fetch.pack(pady=20, padx=20, fill='x')
    
    lbl_fetch_success = tk.Label(root, text="")
    lbl_fetch_success.pack(pady=10)

    root.mainloop()

if __name__ == "__main__":
    main()

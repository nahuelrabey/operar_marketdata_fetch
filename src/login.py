import requests
import tkinter as tk
from tkinter import messagebox

def get_token(username, password):
    """
    Retrieves the authentication token from Invertir Online API.
    """
    url = "https://api.invertironline.com/token"
    payload = {
        'username': username,
        'password': password,
        'grant_type': 'password'
    }
    
    try:
        response = requests.post(url, data=payload)
        response.raise_for_status()
        token = response.json().get('access_token')
        if token:
            with open('token.txt', 'w') as f:
                f.write(token)
        return token
    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error: {e}")
        if response.content:
            print(f"Response content: {response.content.decode()}")
        return None
    except Exception as e:
        print(f"Error getting token: {e}")
        return None

def get_user_credentials(parent=None):
    """
    Opens a GUI dialog to get username and password from the user.
    Handles login and displays token on success.
    """
    if parent:
        root = tk.Toplevel(parent)
    else:
        root = tk.Tk()
        
    root.title("Invertir Online Login")
    root.geometry("300x250")

    # Frame for login form
    login_frame = tk.Frame(root)
    login_frame.pack(fill='both', expand=True, padx=20, pady=20)

    tk.Label(login_frame, text="Username:").pack(pady=5)
    entry_username = tk.Entry(login_frame)
    entry_username.pack(pady=5, fill='x')

    tk.Label(login_frame, text="Password:").pack(pady=5)
    entry_password = tk.Entry(login_frame, show="*")
    entry_password.pack(pady=5, fill='x')

    def submit():
        username = entry_username.get()
        password = entry_password.get()
        
        if not username or not password:
            messagebox.showwarning("Input Error", "Please enter both username and password.")
            return

        token = get_token(username, password)
        
        if token:
            # Login successful, close window. 
            # The Interface module will handle the success display.
            root.destroy()
        else:
            messagebox.showerror("Login Failed", "Could not retrieve token. Check credentials.")

    btn_submit = tk.Button(login_frame, text="Login", command=submit, height=2)
    btn_submit.pack(pady=20, fill='x')

    # Handle window close button
    def on_closing():
        root.destroy()
    root.protocol("WM_DELETE_WINDOW", on_closing)

    if parent:
        root.wait_window()
    else:
        root.mainloop()
    
    return None, None 

if __name__ == "__main__":
    get_user_credentials()

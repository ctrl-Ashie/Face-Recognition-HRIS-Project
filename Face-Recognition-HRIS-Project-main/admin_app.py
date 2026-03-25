import os
import secrets
import hashlib
import tkinter as tk
from tkinter import messagebox

from dotenv import load_dotenv

from Menu import AdminPanel
from storage import init_db, get_employee, get_connection, _using_supabase, _supabase_request
from modern_ui import apply_modern_style, ModernCard, PrimaryButton, SecondaryButton, ModernLabel, ModernEntry


def verify_password(password: str, hashed: str) -> bool:
    if not password or not hashed:
        return False
    return hashlib.sha256(password.encode()).hexdigest() == hashed


class AdminLauncher:
    """Standalone admin app for managing employees and logs."""

    def __init__(self):
        # Guarantee we load the .env from the exact same directory (fixes path bugs)
        self.env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
        load_dotenv(self.env_path)
        
        init_db()

        self.root = tk.Tk()
        self.root.title("HRIS Admin / Manager Login")
        self.root.minsize(450, 300)
        
        apply_modern_style()

        # Check secret immediately on launch
        self._check_sysadmin_secret()

        self.status_var = tk.StringVar(value="Enter credentials or register a manager.")

        self._build_login_ui()

    def _check_sysadmin_secret(self):
        """Checks if a SysAdmin secret exists. If not, auto-generates one and saves it."""
        env_secret = None
        if os.path.exists(self.env_path):
            with open(self.env_path, "r") as f:
                for line in f:
                    if line.startswith("HRIS_SYSADMIN_SECRET="):
                        env_secret = line.split("=", 1)[1].strip()
                        break
        
        secret = os.getenv("HRIS_SYSADMIN_SECRET") or env_secret
        if not secret:
            self._generate_and_show_secret()
            
    def _generate_and_show_secret(self):
        # Auto-generate a readable but strong secret key
        import random
        import string
        
        chars = string.ascii_uppercase + string.digits
        new_secret = "HRIS-" + "".join(random.choice(chars) for _ in range(8))
        
        try:
            # Save to .env
            with open(self.env_path, "a") as f:
                f.write(f"\n# Auto-generated SysAdmin Secret for registering managers\n")
                f.write(f"HRIS_SYSADMIN_SECRET={new_secret}\n")
            
            os.environ["HRIS_SYSADMIN_SECRET"] = new_secret
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save secret to .env: {e}")
            return
            
        # Hide root temporarily
        self.root.withdraw()
        
        setup_win = tk.Toplevel()
        setup_win.title("SysAdmin Setup")
        setup_win.geometry("480x280")
        setup_win.protocol("WM_DELETE_WINDOW", lambda: self.root.destroy()) # Exit if closed
        
        tk.Label(setup_win, text="Welcome to the Manager Portal!", font=("Arial", 14, "bold"), fg="#caab2f").pack(pady=(15, 10))
        tk.Label(setup_win, text="We have securely auto-generated your initial\nSysAdmin Secret. You need this to promote employees to Managers.", wraplength=450, justify="center").pack(pady=(0, 15))
        
        # Display secret securely but clearly
        secret_var = tk.StringVar(value=new_secret)
        entry = tk.Entry(setup_win, textvariable=secret_var, font=("Courier", 16, "bold"), justify="center", state="readonly")
        entry.pack(pady=5, padx=20, fill="x")
        
        def copy_to_clipboard():
            setup_win.clipboard_clear()
            setup_win.clipboard_append(new_secret)
            setup_win.update() # Keeps the clipboard active
            messagebox.showinfo("Copied", "Secret key copied to clipboard!", parent=setup_win)
            
        tk.Button(setup_win, text="Copy to Clipboard", command=copy_to_clipboard).pack(pady=5)
        
        def continue_app():
            setup_win.destroy()
            self.root.deiconify() # Bring back main window
                
        tk.Button(setup_win, text="I have saved it, Continue", command=continue_app, bg="#caab2f", font=("Arial", 11, "bold")).pack(pady=15)
        
        setup_win.wait_window()

    def _build_login_ui(self):
        for widget in self.root.winfo_children():
            widget.destroy()
            
        container = ModernCard(self.root, padx=18, pady=16)
        container.pack(fill="both", expand=True)
        container_inner = container.inner

        ModernLabel(container_inner, text="Manager Portal Login", font=("Arial", 16, "bold")).pack(anchor="w", pady=(0, 10))

        form = tk.Frame(container_inner, bg=container_inner.cget("bg"))
        form.pack(fill="x")

        ModernLabel(form, text="Manager ID", width=14, anchor="w").grid(row=0, column=0, sticky="w", pady=4)
        ModernLabel(form, text="Password", width=14, anchor="w").grid(row=1, column=0, sticky="w", pady=4)

        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()
        user_entry = ModernEntry(form, textvariable=self.username_var)
        user_entry.grid(row=0, column=1, sticky="ew", pady=4)
        
        pwd_entry = ModernEntry(form, textvariable=self.password_var)
        pwd_entry.entry.config(show="*")
        pwd_entry.grid(row=1, column=1, sticky="ew", pady=4)
        form.columnconfigure(1, weight=1)

        btn_container = tk.Frame(container_inner, bg=container_inner.cget("bg"))
        btn_container.pack(fill="x", pady=(12, 8))
        PrimaryButton(btn_container, text="Login", command=self._login).pack(side="right", padx=5)
        SecondaryButton(btn_container, text="Register Manager", command=self._show_register_ui).pack(side="left", padx=5)
        
        tk.Label(container_inner, textvariable=self.status_var, anchor="w", bg=container_inner.cget("bg"), fg="#333333").pack(fill="x")

    def _show_register_ui(self):
        for widget in self.root.winfo_children():
            widget.destroy()

        container = ModernCard(self.root, padx=18, pady=16)
        container.pack(fill="both", expand=True)
        container_inner = container.inner

        ModernLabel(container_inner, text="Register Manager Account", font=("Arial", 16, "bold")).pack(anchor="w", pady=(0, 10))
        ModernLabel(container_inner, text="Note: Upgrades an existing employee account to Manager.", fg="#555").pack(anchor="w", pady=(0, 10))

        form = tk.Frame(container_inner, bg=container_inner.cget("bg"))
        form.pack(fill="x")

        ModernLabel(form, text="SysAdmin Secret*", width=16, anchor="w").grid(row=0, column=0, sticky="w", pady=4)
        ModernLabel(form, text="Employee ID", width=16, anchor="w").grid(row=1, column=0, sticky="w", pady=4)
        ModernLabel(form, text="New Password", width=16, anchor="w").grid(row=2, column=0, sticky="w", pady=4)

        self.secret_var = tk.StringVar()
        self.reg_id_var = tk.StringVar()
        self.reg_pass_var = tk.StringVar()
        
        secret_entry = ModernEntry(form, textvariable=self.secret_var)
        secret_entry.entry.config(show="*")
        secret_entry.grid(row=0, column=1, sticky="ew", pady=4)
        
        id_entry = ModernEntry(form, textvariable=self.reg_id_var)
        id_entry.grid(row=1, column=1, sticky="ew", pady=4)
        
        reg_pwd_entry = ModernEntry(form, textvariable=self.reg_pass_var)
        reg_pwd_entry.entry.config(show="*")
        reg_pwd_entry.grid(row=2, column=1, sticky="ew", pady=4)
        
        form.columnconfigure(1, weight=1)

        btn_container = tk.Frame(container_inner, bg=container_inner.cget("bg"))
        btn_container.pack(fill="x", pady=(12, 8))
        PrimaryButton(btn_container, text="Register", command=self._register_manager).pack(side="right", padx=5)
        SecondaryButton(btn_container, text="Back to Login", command=self._build_login_ui).pack(side="left", padx=5)

    def _register_manager(self):
        # Reliable read: Check the file directly first in case of dotenv caching issues on Windows.
        expected_secret = os.getenv("HRIS_SYSADMIN_SECRET", "")
        if os.path.exists(self.env_path):
            with open(self.env_path, "r") as f:
                for line in f:
                    if line.startswith("HRIS_SYSADMIN_SECRET="):
                        expected_secret = line.split("=", 1)[1].strip()
        
        expected_secret = expected_secret.strip()
        user_input_secret = self.secret_var.get().strip()

        if not expected_secret or user_input_secret != expected_secret:
            messagebox.showerror("Register", "Invalid SysAdmin secret.")
            return

        emp_id = self.reg_id_var.get().strip()
        pwd = self.reg_pass_var.get().strip()
        if not emp_id or not pwd:
            messagebox.showwarning("Register", "Fill all fields.")
            return

        emp = get_employee(emp_id)
        if not emp:
            messagebox.showerror("Register", "Employee ID not found. Register them in the Main App first.")
            return

        hashed = hashlib.sha256(pwd.encode()).hexdigest()

        try:
            if _using_supabase():
                _supabase_request("PATCH", "employees", params={"employee_id": f"eq.{emp_id}"}, payload={"is_admin": 1, "password_hash": hashed})
            else:
                with get_connection() as conn:
                    conn.execute("UPDATE employees SET is_admin = 1, password_hash = ? WHERE employee_id = ?", (hashed, emp_id))
                    conn.commit()
            
            messagebox.showinfo("Register", f"Employee {emp_id} is now a Manager.")
            self._build_login_ui()
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to promote manager:\n{e}")

    def _login(self):
        username = self.username_var.get().strip()
        password = self.password_var.get().strip()

        if not username or not password:
            messagebox.showwarning("Login", "Enter both ID and password.")
            return

        # Check DB
        emp = get_employee(username)
        if not emp or not emp.get("is_admin"):
            messagebox.showerror("Login", "Invalid Manager ID or not a manager.")
            return

        if not verify_password(password, emp.get("password_hash")):
            messagebox.showerror("Login", "Invalid password.")
            return

        self.root.withdraw()
        panel = AdminPanel(self.root, on_status=self._set_status, on_reenroll=None, current_manager_id=username)
        panel.protocol("WM_DELETE_WINDOW", lambda: self._close_panel(panel))

    def _close_panel(self, panel):
        panel.destroy()
        self.root.deiconify()

    def _set_status(self, message):
        self.status_var.set(message)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    AdminLauncher().run()

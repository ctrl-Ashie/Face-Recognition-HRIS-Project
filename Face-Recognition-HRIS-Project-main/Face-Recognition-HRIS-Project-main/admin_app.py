import os
import secrets
import hashlib
import tkinter as tk
from tkinter import messagebox

from dotenv import load_dotenv

from Menu import AdminPanel
from storage import init_db, get_employee, get_connection, _using_supabase, _supabase_request


def verify_password(password: str, hashed: str) -> bool:
    if not password or not hashed:
        return False
    return hashlib.sha256(password.encode()).hexdigest() == hashed


class AdminLauncher:
    """Standalone admin app for managing employees and logs."""

    def __init__(self):
        load_dotenv()
        init_db()

        self.root = tk.Tk()
        self.root.title("HRIS Admin / Manager Login")
        self.root.minsize(450, 300)

        self._ensure_sysadmin_secret()

        self.status_var = tk.StringVar(value="Enter credentials or register the first manager.")

        self._build_login_ui()

    def _ensure_sysadmin_secret(self):
        """Generates a SysAdmin secret if one doesn't exist, updating the .env file."""
        secret = os.getenv("HRIS_SYSADMIN_SECRET")
        if not secret:
            new_secret = secrets.token_hex(6)
            try:
                with open(".env", "a") as f:
                    f.write(f"\n# Auto-generated SysAdmin Secret for registering managers\n")
                    f.write(f"HRIS_SYSADMIN_SECRET={new_secret}\n")
                
                os.environ["HRIS_SYSADMIN_SECRET"] = new_secret
                
                # Show popup to user so they know where to find it.
                self.root.after(500, lambda: messagebox.showinfo(
                    "First Time Configuration", 
                    f"Welcome!\n\n"
                    f"A secure 'SysAdmin Secret' was just generated and saved to your .env file.\n\n"
                    f"Secret: {new_secret}\n\n"
                    f"Please keep this safe. You will need it whenever you click 'Register Manager' to upgrade an employee into a Manager."
                ))
            except Exception as e:
                print(f"Could not automatically write SysAdmin Secret to .env: {e}")

    def _build_login_ui(self):
        for widget in self.root.winfo_children():
            widget.destroy()
            
        container = tk.Frame(self.root, padx=18, pady=16)
        container.pack(fill="both", expand=True)

        tk.Label(container, text="Manager Portal Login", font=("Arial", 16, "bold")).pack(anchor="w", pady=(0, 10))

        form = tk.Frame(container)
        form.pack(fill="x")

        tk.Label(form, text="Manager ID", width=14, anchor="w").grid(row=0, column=0, sticky="w", pady=4)
        tk.Label(form, text="Password", width=14, anchor="w").grid(row=1, column=0, sticky="w", pady=4)

        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()
        tk.Entry(form, textvariable=self.username_var).grid(row=0, column=1, sticky="ew", pady=4)
        tk.Entry(form, textvariable=self.password_var, show="*").grid(row=1, column=1, sticky="ew", pady=4)
        form.columnconfigure(1, weight=1)

        btn_container = tk.Frame(container)
        btn_container.pack(fill="x", pady=(12, 8))
        tk.Button(btn_container, text="Login", command=self._login, bg="#caab2f").pack(side="right", padx=5)
        tk.Button(btn_container, text="Register Manager", command=self._show_register_ui).pack(side="left", padx=5)
        
        tk.Label(container, textvariable=self.status_var, anchor="w").pack(fill="x")

    def _show_register_ui(self):
        for widget in self.root.winfo_children():
            widget.destroy()

        container = tk.Frame(self.root, padx=18, pady=16)
        container.pack(fill="both", expand=True)

        tk.Label(container, text="Register Manager Account", font=("Arial", 16, "bold")).pack(anchor="w", pady=(0, 10))
        tk.Label(container, text="Note: Upgrades an existing employee account to Manager.", fg="#555").pack(anchor="w", pady=(0, 10))

        form = tk.Frame(container)
        form.pack(fill="x")

        tk.Label(form, text="SysAdmin Secret*", width=16, anchor="w").grid(row=0, column=0, sticky="w", pady=4)
        tk.Label(form, text="Employee ID", width=16, anchor="w").grid(row=1, column=0, sticky="w", pady=4)
        tk.Label(form, text="New Password", width=16, anchor="w").grid(row=2, column=0, sticky="w", pady=4)

        self.secret_var = tk.StringVar()
        self.reg_id_var = tk.StringVar()
        self.reg_pass_var = tk.StringVar()
        tk.Entry(form, textvariable=self.secret_var, show="*").grid(row=0, column=1, sticky="ew", pady=4)
        tk.Entry(form, textvariable=self.reg_id_var).grid(row=1, column=1, sticky="ew", pady=4)
        tk.Entry(form, textvariable=self.reg_pass_var, show="*").grid(row=2, column=1, sticky="ew", pady=4)
        form.columnconfigure(1, weight=1)

        btn_container = tk.Frame(container)
        btn_container.pack(fill="x", pady=(12, 8))
        tk.Button(btn_container, text="Register", command=self._register_manager, bg="#caab2f").pack(side="right", padx=5)
        tk.Button(btn_container, text="Back to Login", command=self._build_login_ui).pack(side="left", padx=5)

    def _register_manager(self):
        expected_secret = os.getenv("HRIS_SYSADMIN_SECRET")
        if not expected_secret or self.secret_var.get() != expected_secret:
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

        if _using_supabase():
            _supabase_request("PATCH", "employees", params={"employee_id": f"eq.{emp_id}"}, payload={"is_admin": 1, "password_hash": hashed})
        else:
            with get_connection() as conn:
                conn.execute("UPDATE employees SET is_admin = 1, password_hash = ? WHERE employee_id = ?", (hashed, emp_id))
                conn.commit()

        messagebox.showinfo("Register", f"Employee {emp_id} is now a Manager.")
        self._build_login_ui()

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

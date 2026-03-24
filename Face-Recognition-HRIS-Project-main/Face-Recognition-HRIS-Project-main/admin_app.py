import os
import secrets
import hashlib
import tkinter as tk
from tkinter import messagebox

from dotenv import load_dotenv

from Menu import AdminPanel
from modern_ui import (
    ModernStyles,
    ModernButton,
    PrimaryButton,
    SecondaryButton,
    ModernCard,
    ModernLabel,
    create_gradient_header,
)
from storage import init_db, get_employee, get_connection, _using_supabase, _supabase_request

BG_COLOR = "#f0f2f5"
HEADER_COLOR = "#010066"
ACCENT_COLOR = "#caab2f"


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
        self.root.minsize(500, 380)
        self.root.config(bg=BG_COLOR)

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
                
                self.root.after(500, lambda: messagebox.showinfo(
                    "First Time Configuration", 
                    f"Welcome!\n\n"
                    f"A secure 'SysAdmin Secret' was just generated and saved to your .env file.\n\n"
                    f"Secret: {new_secret}\n\n"
                    f"Please keep this safe. You will need it whenever you click 'Register Manager' to upgrade an employee into a Manager."
                ))
            except Exception as e:
                print(f"Could not automatically write SysAdmin Secret to .env: {e}")

    def _create_header(self, parent):
        header = tk.Frame(parent, bg=HEADER_COLOR)
        header.pack(fill="x")
        
        header_canvas = tk.Canvas(header, height=70, bg=HEADER_COLOR, highlightthickness=0)
        header_canvas.pack(fill="x")
        header_canvas.update_idletasks()
        
        w = header_canvas.winfo_width()
        if w < 100:
            w = 500
        
        create_gradient_header(header_canvas, w, 70)
        
        header_canvas.create_text(w//2, 35, text="Manager Portal", fill="#ffffff", 
                                  font=("Segoe UI", 22, "bold"), anchor="center")
        header_canvas.create_text(w//2, 55, text="HRIS Admin System", fill="#caab2f", 
                                  font=("Segoe UI", 11), anchor="center")

    def _build_login_ui(self):
        for widget in self.root.winfo_children():
            widget.destroy()
        
        self._create_header(self.root)
            
        container = tk.Frame(self.root, bg=BG_COLOR, padx=30, pady=20)
        container.pack(fill="both", expand=True)

        card = ModernCard(container, padx=25, pady=20)
        card.pack(fill="both", expand=True)

        form = card.inner

        tk.Label(form, text="Manager Login", bg=ModernStyles.CARD_BG, fg=HEADER_COLOR, 
                font=("Segoe UI", 16, "bold")).pack(anchor="w", pady=(0, 20))

        field_frame = tk.Frame(form, bg=ModernStyles.CARD_BG)
        field_frame.pack(fill="x", pady=(0, 20))

        tk.Label(field_frame, text="Manager ID", bg=ModernStyles.CARD_BG, fg=ModernStyles.TEXT_PRIMARY,
                width=14, anchor="w", font=("Segoe UI", 10)).grid(row=0, column=0, sticky="w", pady=12)
        
        self.username_var = tk.StringVar()
        username_entry = tk.Entry(
            field_frame, textvariable=self.username_var,
            font=("Segoe UI", 11), bg="#ffffff", fg=ModernStyles.TEXT_PRIMARY,
            relief="flat", highlightthickness=1,
            highlightcolor=ACCENT_COLOR, highlightbackground=ModernStyles.BORDER_COLOR,
            insertbackground=HEADER_COLOR
        )
        username_entry.grid(row=0, column=1, sticky="ew", pady=12)
        field_frame.columnconfigure(1, weight=1)

        tk.Label(field_frame, text="Password", bg=ModernStyles.CARD_BG, fg=ModernStyles.TEXT_PRIMARY,
                width=14, anchor="w", font=("Segoe UI", 10)).grid(row=1, column=0, sticky="w", pady=12)
        
        self.password_var = tk.StringVar()
        password_entry = tk.Entry(
            field_frame, textvariable=self.password_var, show="*",
            font=("Segoe UI", 11), bg="#ffffff", fg=ModernStyles.TEXT_PRIMARY,
            relief="flat", highlightthickness=1,
            highlightcolor=ACCENT_COLOR, highlightbackground=ModernStyles.BORDER_COLOR,
            insertbackground=HEADER_COLOR
        )
        password_entry.grid(row=1, column=1, sticky="ew", pady=12)

        btn_container = tk.Frame(form, bg=ModernStyles.CARD_BG)
        btn_container.pack(fill="x", pady=(0, 15))
        
        register_btn = SecondaryButton(btn_container, text="Register Manager", 
                                       command=self._show_register_ui, width=140)
        register_btn.pack(side="left")
        
        login_btn = PrimaryButton(btn_container, text="Login", command=self._login, width=100)
        login_btn.pack(side="right")
        
        status_label = tk.Label(form, textvariable=self.status_var, bg=ModernStyles.CARD_BG, 
                                fg=ModernStyles.TEXT_SECONDARY, font=("Segoe UI", 9), anchor="w")
        status_label.pack(fill="x")

    def _show_register_ui(self):
        for widget in self.root.winfo_children():
            widget.destroy()

        self._create_header(self.root)

        container = tk.Frame(self.root, bg=BG_COLOR, padx=30, pady=20)
        container.pack(fill="both", expand=True)

        card = ModernCard(container, padx=25, pady=20)
        card.pack(fill="both", expand=True)

        form = card.inner

        tk.Label(form, text="Register Manager Account", bg=ModernStyles.CARD_BG, fg=HEADER_COLOR, 
                font=("Segoe UI", 16, "bold")).pack(anchor="w", pady=(0, 8))
        
        tk.Label(form, text="Note: Upgrades an existing employee account to Manager.", 
                bg=ModernStyles.CARD_BG, fg=ModernStyles.TEXT_SECONDARY, 
                font=("Segoe UI", 10)).pack(anchor="w", pady=(0, 20))

        field_frame = tk.Frame(form, bg=ModernStyles.CARD_BG)
        field_frame.pack(fill="x", pady=(0, 20))

        tk.Label(field_frame, text="SysAdmin Secret*", bg=ModernStyles.CARD_BG, fg=ModernStyles.TEXT_PRIMARY,
                width=16, anchor="w", font=("Segoe UI", 10)).grid(row=0, column=0, sticky="w", pady=12)
        
        self.secret_var = tk.StringVar()
        secret_entry = tk.Entry(
            field_frame, textvariable=self.secret_var, show="*",
            font=("Segoe UI", 11), bg="#ffffff", fg=ModernStyles.TEXT_PRIMARY,
            relief="flat", highlightthickness=1,
            highlightcolor=ACCENT_COLOR, highlightbackground=ModernStyles.BORDER_COLOR,
            insertbackground=HEADER_COLOR
        )
        secret_entry.grid(row=0, column=1, sticky="ew", pady=12)
        field_frame.columnconfigure(1, weight=1)

        tk.Label(field_frame, text="Employee ID", bg=ModernStyles.CARD_BG, fg=ModernStyles.TEXT_PRIMARY,
                width=16, anchor="w", font=("Segoe UI", 10)).grid(row=1, column=0, sticky="w", pady=12)
        
        self.reg_id_var = tk.StringVar()
        reg_id_entry = tk.Entry(
            field_frame, textvariable=self.reg_id_var,
            font=("Segoe UI", 11), bg="#ffffff", fg=ModernStyles.TEXT_PRIMARY,
            relief="flat", highlightthickness=1,
            highlightcolor=ACCENT_COLOR, highlightbackground=ModernStyles.BORDER_COLOR,
            insertbackground=HEADER_COLOR
        )
        reg_id_entry.grid(row=1, column=1, sticky="ew", pady=12)

        tk.Label(field_frame, text="New Password", bg=ModernStyles.CARD_BG, fg=ModernStyles.TEXT_PRIMARY,
                width=16, anchor="w", font=("Segoe UI", 10)).grid(row=2, column=0, sticky="w", pady=12)
        
        self.reg_pass_var = tk.StringVar()
        reg_pass_entry = tk.Entry(
            field_frame, textvariable=self.reg_pass_var, show="*",
            font=("Segoe UI", 11), bg="#ffffff", fg=ModernStyles.TEXT_PRIMARY,
            relief="flat", highlightthickness=1,
            highlightcolor=ACCENT_COLOR, highlightbackground=ModernStyles.BORDER_COLOR,
            insertbackground=HEADER_COLOR
        )
        reg_pass_entry.grid(row=2, column=1, sticky="ew", pady=12)

        btn_container = tk.Frame(form, bg=ModernStyles.CARD_BG)
        btn_container.pack(fill="x", pady=(0, 15))
        
        back_btn = SecondaryButton(btn_container, text="Back to Login", 
                                   command=self._build_login_ui, width=130)
        back_btn.pack(side="left")
        
        register_btn = PrimaryButton(btn_container, text="Register", 
                                     command=self._register_manager, width=100)
        register_btn.pack(side="right")

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

        emp = get_employee(username)
        if not emp or not emp.get("is_admin"):
            messagebox.showerror("Login", "Invalid Manager ID or not a manager.")
            return

        if not verify_password(password, emp.get("password_hash", "")):
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

import tkinter as tk
from UI import UI
from tkinter import messagebox
from Main import Main

class Login(UI):

    def __init__(self):
        super().__init__()
        self.main.title("Login Application")
        self.login_vars = {
            "employee_id": tk.StringVar(),
        }
        self.signup_vars = {
            "employee_id":    tk.StringVar(),
            "full_name":      tk.StringVar(),
            "department":     tk.StringVar(),
            "role_position":  tk.StringVar(),
            "contact_number": tk.StringVar(),
            "email":          tk.StringVar(),
        }

        self._create_login()
        self._create_account()
        self._terms_and_conditions()

    def _create_login(self):
        card = UI.card(self.main)
        card.pack(pady=2, padx=30, fill="x")

        login_header = UI.login_header(card)
        login_header.pack(fill="x")
        tk.Label(login_header, text="Employee Login", bg=self.HEADER_COLOR, fg="#ffffff",
                 font=("Segoe UI", 10, "bold")).pack(pady=10)
        row_frame = tk.Frame(card, bg=self.FORM_BG)
        row_frame.pack(fill="x", padx=20, pady=5)
        tk.Label(row_frame, text="Employee ID", bg=self.FORM_BG).pack(side="left", padx=(0, 10))
        UI.Entry(row_frame, textvariable=self.login_vars["employee_id"]).pack(side="left", fill="x", expand=True )

        spacer = tk.Frame(card, bg=self.FORM_BG, height=0)
        spacer.pack(fill="x") 
        UI.RoundedButton(card, text="Login", command=self.on_login).pack(side="bottom", pady=10)

    def on_login(self):
        employee_id = self.login_vars["employee_id"].get()

        if not employee_id:
            tk.messagebox.showwarning("Warning", "Please enter your Employee ID.")
            return
        self.main.destroy()
        app = Main()
        app.main.mainloop()

    def _create_account(self):
        card = UI.card(self.main)
        card.pack(pady=2, padx=30, fill="x")

        login_header = UI.login_header(card)
        login_header.pack(fill="x")
        tk.Label(login_header, text="Create New Account", bg=self.HEADER_COLOR, fg="#ffffff",
             font=("Segoe UI", 10, "bold")).pack(pady=10)

        columns = tk.Frame(card, bg=self.FORM_BG)
        columns.pack(fill="x", padx=10, pady=5)

        left = tk.Frame(columns, bg=self.FORM_BG)
        left.pack(side="left", fill="both", expand=True, padx=(0, 5))

        tk.Label(left, text="Employee ID", bg=self.FORM_BG).pack(anchor="w", padx=10, pady=(10, 0))
        UI.Entry(left, textvariable=self.signup_vars["employee_id"]).pack(fill="x", padx=10, pady=3)

        tk.Label(left, text="Full Name", bg=self.FORM_BG).pack(anchor="w", padx=10, pady=(10, 0))
        UI.Entry(left, textvariable=self.signup_vars["full_name"]).pack(fill="x", padx=10, pady=3)

        tk.Label(left, text="Department", bg=self.FORM_BG).pack(anchor="w", padx=10, pady=(10, 0))
        UI.Entry(left, textvariable=self.signup_vars["department"]).pack(fill="x", padx=10, pady=3)

        right = tk.Frame(columns, bg=self.FORM_BG)
        right.pack(side="right", fill="both", expand=True, padx=(5, 0))

        tk.Label(right, text="Role / Position", bg=self.FORM_BG).pack(anchor="w", padx=10, pady=(10, 0))
        UI.Entry(right, textvariable=self.signup_vars["role_position"]).pack(fill="x", padx=10, pady=3)

        tk.Label(right, text="Contact Number", bg=self.FORM_BG).pack(anchor="w", padx=10, pady=(10, 0))
        UI.Entry(right, textvariable=self.signup_vars["contact_number"]).pack(fill="x", padx=10, pady=3)

        tk.Label(right, text="Email", bg=self.FORM_BG).pack(anchor="w", padx=10, pady=(10, 0))
        UI.Entry(right, textvariable=self.signup_vars["email"]).pack(fill="x", padx=10, pady=3)

        spacer = tk.Frame(card, bg=self.FORM_BG, height=0)
        spacer.pack(fill="x")

        UI.RoundedButton(card, text="Create Account",
                     command=self.on_create_account).pack(side="bottom", pady=10)

    def on_create_account(self):
        data = {k: v.get() for k, v in self.signup_vars.items()}
        if not all(data.values()):
            tk.messagebox.showwarning("Warning", "Please fill in all fields to create an account.")
            return
        self.main.destroy()
        app = Main()
        app.main.mainloop()

    def _terms_and_conditions(self):
        terms_frame = tk.Frame(self.main, bg=self.BG_COLOR)
        terms_frame.pack(fill="x", pady=5, padx=40)

        tk.Button(terms_frame, text="By logging in, you agree to our Terms and Conditions.",
                  bd=0, bg=self.BG_COLOR, fg="#555555").pack(pady=5)
        tk.Button(terms_frame, text="View Terms and Conditions", command=self._show_terms,
                  bd=0, bg=self.BG_COLOR, fg="#115374", font=("Segoe UI", 9, "underline")).pack(pady=5)
    def _show_terms(self):
        tk.messagebox.showinfo("Terms and Conditions", "Terms and conditions content goes here.")
        return

if __name__ == "__main__":
    app = Login()
    app.main.mainloop()
